"""
Migration script: Convert existing specials to normalized schema.

This script:
1. Creates the new master_products and product_prices tables
2. Migrates existing specials data
3. Downloads and caches product images
4. Sets up proper relationships

Run with: python -m scripts.migrate_to_v2
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base, engine
from app.models import Store, Special, MasterProduct, ProductPrice
from app.services.image_cache import image_cache


def create_tables():
    """Create new tables if they don't exist."""
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully")


def price_to_cents(price) -> int:
    """Convert price to cents for numeric storage."""
    if price is None:
        return 0
    if isinstance(price, (int, float)):
        return int(float(price) * 100)
    if isinstance(price, Decimal):
        return int(price * 100)
    if isinstance(price, str):
        try:
            return int(float(price.replace("$", "").replace(",", "")) * 100)
        except ValueError:
            return 0
    return 0


def format_price(cents: int) -> str:
    """Format cents as price string."""
    dollars = cents / 100
    return f"${dollars:.2f}"


def migrate_specials(db_session):
    """Migrate existing specials to new schema."""
    print("\nMigrating specials to new schema...")

    # Get all current specials
    specials = db_session.query(Special).all()
    print(f"Found {len(specials)} specials to migrate")

    migrated = 0
    skipped = 0
    errors = 0

    for special in specials:
        try:
            # Check if product already exists
            existing = db_session.query(MasterProduct).filter(
                MasterProduct.store_id == special.store_id,
                MasterProduct.stockcode == special.store_product_id
            ).first()

            if existing:
                product = existing
                # Update last_seen_at
                product.last_seen_at = datetime.now()
            else:
                # Create new master product
                product = MasterProduct(
                    store_id=special.store_id,
                    stockcode=special.store_product_id or f"unknown_{special.id}",
                    name=special.name,
                    brand=special.brand,
                    size=special.size,
                    category=special.category,
                    product_url=special.product_url,
                    original_image_url=special.image_url,
                    image_cached=False,
                    created_at=special.created_at or datetime.now(),
                    last_seen_at=datetime.now()
                )
                db_session.add(product)
                db_session.flush()  # Get product ID

            # Create price record
            price_cents = price_to_cents(special.price)
            was_price_cents = price_to_cents(special.was_price)

            # Check if this price already exists
            existing_price = db_session.query(ProductPrice).filter(
                ProductPrice.product_id == product.id,
                ProductPrice.valid_from == special.valid_from
            ).first()

            if not existing_price:
                price_record = ProductPrice(
                    product_id=product.id,
                    price=format_price(price_cents),
                    price_numeric=price_cents,
                    was_price=format_price(was_price_cents) if was_price_cents else None,
                    was_price_numeric=was_price_cents if was_price_cents else None,
                    discount_percent=special.discount_percent or 0,
                    unit_price=special.unit_price,
                    valid_from=special.valid_from or datetime.now(),
                    valid_to=special.valid_to or (datetime.now() + timedelta(days=7)),
                    is_current=True,  # Will be updated later
                    scraped_at=special.scraped_at or datetime.now()
                )
                db_session.add(price_record)

            migrated += 1

            if migrated % 100 == 0:
                print(f"  Migrated {migrated} specials...")
                db_session.commit()

        except Exception as e:
            errors += 1
            print(f"  Error migrating special {special.id}: {e}")
            continue

    db_session.commit()
    print(f"\nMigration complete: {migrated} migrated, {skipped} skipped, {errors} errors")


def update_current_prices(db_session):
    """Mark only the most recent prices as current."""
    print("\nUpdating current price flags...")

    # First, set all to not current
    db_session.execute(
        text("UPDATE product_prices SET is_current = 0")
    )

    # SQLite-compatible: mark the most recent price for each product as current
    # Using a subquery without table aliases in UPDATE
    db_session.execute(text("""
        UPDATE product_prices
        SET is_current = 1
        WHERE id IN (
            SELECT pp2.id
            FROM product_prices pp2
            INNER JOIN (
                SELECT product_id, MAX(valid_from) as max_valid
                FROM product_prices
                GROUP BY product_id
            ) latest ON pp2.product_id = latest.product_id
                    AND pp2.valid_from = latest.max_valid
        )
    """))

    db_session.commit()
    print("Current prices updated")


async def cache_images(db_session):
    """Download and cache all product images."""
    print("\nCaching product images...")

    # Get all products without cached images
    products = db_session.query(MasterProduct).filter(
        MasterProduct.image_cached == False,
        MasterProduct.original_image_url.isnot(None)
    ).all()

    print(f"Found {len(products)} products needing image cache")

    if not products:
        return

    # Prepare image list
    images = []
    store_slugs = {}

    # Get store slugs
    stores = db_session.query(Store).all()
    for store in stores:
        store_slugs[store.id] = store.slug

    for product in products:
        store_slug = store_slugs.get(product.store_id, "unknown")
        images.append({
            "url": product.original_image_url,
            "store_slug": store_slug,
            "stockcode": product.stockcode,
            "product_id": product.id
        })

    # Download in batches
    batch_size = 50
    for i in range(0, len(images), batch_size):
        batch = images[i:i + batch_size]
        print(f"  Processing batch {i // batch_size + 1} ({len(batch)} images)...")

        results = await image_cache.cache_batch(batch)

        # Update database with cached paths
        for img_info in batch:
            if image_cache.image_exists(img_info["store_slug"], img_info["stockcode"]):
                product = db_session.query(MasterProduct).get(img_info["product_id"])
                if product:
                    product.local_image_path = image_cache.get_local_path(
                        img_info["store_slug"],
                        img_info["stockcode"]
                    )
                    product.image_cached = True

        db_session.commit()
        print(f"    Batch complete: {results}")


def print_stats(db_session):
    """Print migration statistics."""
    print("\n" + "=" * 50)
    print("MIGRATION STATISTICS")
    print("=" * 50)

    product_count = db_session.query(MasterProduct).count()
    price_count = db_session.query(ProductPrice).count()
    current_count = db_session.query(ProductPrice).filter(ProductPrice.is_current == True).count()
    cached_images = db_session.query(MasterProduct).filter(MasterProduct.image_cached == True).count()

    print(f"Master Products: {product_count}")
    print(f"Total Price Records: {price_count}")
    print(f"Current Prices: {current_count}")
    print(f"Cached Images: {cached_images}")

    # By store
    print("\nBy Store:")
    stores = db_session.query(Store).all()
    for store in stores:
        count = db_session.query(MasterProduct).filter(MasterProduct.store_id == store.id).count()
        print(f"  {store.name}: {count} products")

    print("=" * 50)


async def main():
    """Run the migration."""
    print("=" * 50)
    print("SPECIALS V2 MIGRATION")
    print("=" * 50)

    Session = sessionmaker(bind=engine)
    db_session = Session()

    try:
        # Step 1: Create tables
        create_tables()

        # Step 2: Migrate specials data
        migrate_specials(db_session)

        # Step 3: Update current price flags
        update_current_prices(db_session)

        # Step 4: Cache images (optional, can be slow)
        print("\nDo you want to cache product images? This may take a while.")
        print("(Images will be downloaded in the background if you skip)")
        response = input("Cache images now? (y/N): ").strip().lower()

        if response == 'y':
            await cache_images(db_session)

        # Print stats
        print_stats(db_session)

        print("\nMigration completed successfully!")
        print("You can now use the /v2/specials API endpoints")

    except Exception as e:
        print(f"\nMigration failed: {e}")
        db_session.rollback()
        raise
    finally:
        db_session.close()


if __name__ == "__main__":
    asyncio.run(main())
