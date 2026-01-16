"""
Open Food Facts Import Service

Imports Australian product data from Open Food Facts API.
This gives us ~68,000 products with names, brands, barcodes, and categories.
Prices will need to be crowdsourced separately.
"""
import httpx
import logging
import time
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import SessionLocal
from app.models import Product, Category

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE = "https://world.openfoodfacts.org/api/v2/search"
PAGE_SIZE = 100  # Max allowed by API


def get_or_create_category(db: Session, category_name: str) -> Optional[int]:
    """Get or create a category by name."""
    if not category_name:
        return None

    # Clean up category name
    category_name = category_name.strip()
    if not category_name:
        return None

    # Try to find existing category
    slug = category_name.lower().replace(" ", "-").replace(",", "")[:100]
    category = db.query(Category).filter(Category.slug == slug).first()

    if not category:
        category = Category(name=category_name[:100], slug=slug)
        db.add(category)
        db.flush()

    return category.id


def parse_categories(categories_str: str) -> str:
    """Extract primary category from Open Food Facts categories string."""
    if not categories_str:
        return None

    # Categories are comma-separated, often in format "en:category-name"
    parts = categories_str.split(",")
    for part in parts:
        part = part.strip()
        # Skip language-prefixed entries, get clean names
        if ":" in part:
            part = part.split(":")[-1]
        part = part.replace("-", " ").title()
        if part and len(part) > 2:
            return part
    return None


def import_products_from_openfoodfacts(
    db: Session,
    max_pages: int = None,
    start_page: int = 1
) -> dict:
    """
    Import Australian products from Open Food Facts API.

    Args:
        db: Database session
        max_pages: Maximum number of pages to fetch (None for all)
        start_page: Page to start from (for resuming)

    Returns:
        Dict with import statistics
    """
    imported = 0
    skipped = 0
    errors = 0
    page = start_page

    # First, get total count
    params = {
        "countries_tags": "en:australia",
        "page_size": 1,
        "page": 1,
        "fields": "count"
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(API_BASE, params=params)
            data = response.json()
            total_products = data.get("count", 0)
            total_pages = (total_products // PAGE_SIZE) + 1
            logger.info(f"Total Australian products: {total_products} ({total_pages} pages)")
    except Exception as e:
        logger.error(f"Failed to get product count: {e}")
        return {"error": str(e)}

    if max_pages:
        total_pages = min(total_pages, start_page + max_pages - 1)

    logger.info(f"Starting import from page {start_page} to {total_pages}")

    with httpx.Client(timeout=30.0) as client:
        while page <= total_pages:
            try:
                params = {
                    "countries_tags": "en:australia",
                    "page_size": PAGE_SIZE,
                    "page": page,
                    "fields": "code,product_name,brands,categories,quantity,image_url"
                }

                response = client.get(API_BASE, params=params)

                if response.status_code != 200:
                    logger.error(f"API error on page {page}: {response.status_code}")
                    errors += 1
                    page += 1
                    continue

                data = response.json()
                products = data.get("products", [])

                if not products:
                    logger.info(f"No more products at page {page}")
                    break

                for product in products:
                    try:
                        barcode = product.get("code", "").strip()
                        name = product.get("product_name", "").strip()
                        brand = product.get("brands", "").strip()
                        quantity = product.get("quantity", "").strip()
                        categories = product.get("categories", "")
                        image_url = product.get("image_url", "")

                        # Skip products without names
                        if not name or len(name) < 2:
                            skipped += 1
                            continue

                        # Check if product already exists (by barcode or name+brand)
                        existing = None
                        if barcode:
                            existing = db.query(Product).filter(
                                Product.barcode == barcode
                            ).first()

                        if not existing and brand:
                            # Try name + brand match
                            full_name = f"{brand} {name}"
                            existing = db.query(Product).filter(
                                func.lower(Product.name) == full_name.lower()
                            ).first()

                        if existing:
                            skipped += 1
                            continue

                        # Parse category
                        primary_category = parse_categories(categories)
                        category_id = get_or_create_category(db, primary_category) if primary_category else None

                        # Create product name with brand
                        if brand and brand.lower() not in name.lower():
                            full_name = f"{brand} {name}"
                        else:
                            full_name = name

                        # Add quantity to name if not already there
                        if quantity and quantity not in full_name:
                            full_name = f"{full_name} {quantity}"

                        # Truncate if too long
                        full_name = full_name[:255]

                        # Create new product
                        new_product = Product(
                            name=full_name,
                            brand=brand[:100] if brand else None,
                            barcode=barcode[:50] if barcode else None,
                            category_id=category_id,
                            size=quantity[:50] if quantity else None,
                            image_url=image_url[:500] if image_url else None,
                            is_key_product=False
                        )
                        db.add(new_product)
                        imported += 1

                    except Exception as e:
                        logger.error(f"Error importing product: {e}")
                        errors += 1

                # Commit every page
                db.commit()

                logger.info(f"Page {page}/{total_pages}: imported {imported}, skipped {skipped}, errors {errors}")

                page += 1

                # Rate limiting - be nice to the API
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Error on page {page}: {e}")
                errors += 1
                page += 1
                time.sleep(1)

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "pages_processed": page - start_page,
        "total_available": total_products
    }


def get_import_status(db: Session) -> dict:
    """Get current import status."""
    total_products = db.query(Product).count()
    with_barcode = db.query(Product).filter(Product.barcode != None).count()
    with_brand = db.query(Product).filter(Product.brand != None).count()

    return {
        "total_products": total_products,
        "with_barcode": with_barcode,
        "with_brand": with_brand,
        "from_openfoodfacts": with_barcode  # Approximation
    }


if __name__ == "__main__":
    # Run import directly
    import sys

    max_pages = int(sys.argv[1]) if len(sys.argv) > 1 else 10

    db = SessionLocal()
    try:
        result = import_products_from_openfoodfacts(db, max_pages=max_pages)
        print(f"Import complete: {result}")
    finally:
        db.close()
