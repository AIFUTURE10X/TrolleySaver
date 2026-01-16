"""Database seeding script - Run after database is initialized."""
import json
from pathlib import Path
from sqlalchemy.orm import Session
from app.database import SessionLocal, init_db
from app.models import Store, Category, Product


DATA_DIR = Path("/data/seed")


def seed_stores(db: Session):
    """Seed stores table."""
    stores_file = DATA_DIR / "stores.json"
    if not stores_file.exists():
        print(f"Stores file not found: {stores_file}")
        return

    with open(stores_file) as f:
        stores_data = json.load(f)

    for store_data in stores_data:
        existing = db.query(Store).filter(Store.slug == store_data["slug"]).first()
        if not existing:
            store = Store(**store_data)
            db.add(store)
            print(f"Added store: {store_data['name']}")

    db.commit()


def seed_categories(db: Session):
    """Seed categories table."""
    categories_file = DATA_DIR / "categories.json"
    if not categories_file.exists():
        print(f"Categories file not found: {categories_file}")
        return

    with open(categories_file) as f:
        categories_data = json.load(f)

    for cat_data in categories_data:
        existing = db.query(Category).filter(Category.slug == cat_data["slug"]).first()
        if not existing:
            category = Category(name=cat_data["name"], slug=cat_data["slug"])
            db.add(category)
            print(f"Added category: {cat_data['name']}")

    db.commit()


def seed_products(db: Session):
    """Seed key products table."""
    products_file = DATA_DIR / "key_products.json"
    if not products_file.exists():
        print(f"Products file not found: {products_file}")
        return

    with open(products_file) as f:
        products_data = json.load(f)

    # Get category mapping
    categories = {c.slug: c.id for c in db.query(Category).all()}

    for prod_data in products_data:
        existing = db.query(Product).filter(
            Product.name == prod_data["name"],
            Product.size == prod_data.get("size")
        ).first()

        if not existing:
            category_slug = prod_data.pop("category", None)
            category_id = categories.get(category_slug) if category_slug else None

            product = Product(
                name=prod_data["name"],
                unit=prod_data.get("unit"),
                size=prod_data.get("size"),
                is_key_product=prod_data.get("is_key_product", True),
                category_id=category_id
            )
            db.add(product)
            print(f"Added product: {prod_data['name']}")

    db.commit()


def seed_all():
    """Run all seed functions."""
    print("Initializing database...")
    init_db()

    db = SessionLocal()
    try:
        print("\nSeeding stores...")
        seed_stores(db)

        print("\nSeeding categories...")
        seed_categories(db)

        print("\nSeeding products...")
        seed_products(db)

        print("\nSeeding complete!")

        # Print stats
        print(f"\nDatabase stats:")
        print(f"  Stores: {db.query(Store).count()}")
        print(f"  Categories: {db.query(Category).count()}")
        print(f"  Products: {db.query(Product).count()}")

    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
