"""
Manual Data Import Service

Allows bulk import of price data via CSV or JSON.
Use this to manually enter prices until automated scraping works.
"""
import csv
import json
import logging
from io import StringIO
from decimal import Decimal
from datetime import date
from typing import Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Store, Product, StoreProduct, Price, Category

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def import_prices_from_csv(csv_content: str, db: Session) -> dict:
    """
    Import prices from CSV content.

    Expected CSV format:
    product_name,store_slug,price,was_price,is_special,special_type

    Example:
    Full Cream Milk 2L,woolworths,4.50,5.00,true,half_price
    Eggs Dozen Free Range,coles,6.00,,false,
    """
    reader = csv.DictReader(StringIO(csv_content))

    imported = 0
    errors = []

    for row_num, row in enumerate(reader, start=2):
        try:
            result = _import_single_price(
                db=db,
                product_name=row.get('product_name', '').strip(),
                store_slug=row.get('store_slug', '').strip().lower(),
                price=row.get('price', '').strip(),
                was_price=row.get('was_price', '').strip() or None,
                is_special=row.get('is_special', '').strip().lower() in ('true', '1', 'yes'),
                special_type=row.get('special_type', '').strip() or None
            )
            if result['success']:
                imported += 1
            else:
                errors.append(f"Row {row_num}: {result['error']}")
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")

    db.commit()

    return {
        "imported": imported,
        "errors": errors,
        "total_rows": row_num - 1
    }


def import_prices_from_json(json_content: str, db: Session) -> dict:
    """
    Import prices from JSON content.

    Expected JSON format:
    [
        {
            "product_name": "Full Cream Milk 2L",
            "store_slug": "woolworths",
            "price": 4.50,
            "was_price": 5.00,
            "is_special": true,
            "special_type": "half_price"
        }
    ]
    """
    try:
        data = json.loads(json_content)
    except json.JSONDecodeError as e:
        return {"imported": 0, "errors": [f"Invalid JSON: {str(e)}"], "total_rows": 0}

    if not isinstance(data, list):
        data = [data]

    imported = 0
    errors = []

    for idx, item in enumerate(data):
        try:
            result = _import_single_price(
                db=db,
                product_name=item.get('product_name', ''),
                store_slug=item.get('store_slug', '').lower(),
                price=str(item.get('price', '')),
                was_price=str(item.get('was_price')) if item.get('was_price') else None,
                is_special=item.get('is_special', False),
                special_type=item.get('special_type')
            )
            if result['success']:
                imported += 1
            else:
                errors.append(f"Item {idx}: {result['error']}")
        except Exception as e:
            errors.append(f"Item {idx}: {str(e)}")

    db.commit()

    return {
        "imported": imported,
        "errors": errors,
        "total_rows": len(data)
    }


def _import_single_price(
    db: Session,
    product_name: str,
    store_slug: str,
    price: str,
    was_price: Optional[str] = None,
    is_special: bool = False,
    special_type: Optional[str] = None
) -> dict:
    """Import a single price entry."""

    # Validate inputs
    if not product_name:
        return {"success": False, "error": "Missing product_name"}
    if not store_slug:
        return {"success": False, "error": "Missing store_slug"}
    if not price:
        return {"success": False, "error": "Missing price"}

    # Find store
    store = db.query(Store).filter(Store.slug == store_slug).first()
    if not store:
        return {"success": False, "error": f"Unknown store: {store_slug}"}

    # Find or create product
    product = db.query(Product).filter(
        Product.name.ilike(product_name)
    ).first()

    if not product:
        # Try fuzzy match with key products
        key_products = db.query(Product).filter(Product.is_key_product == True).all()
        product_lower = product_name.lower()

        for kp in key_products:
            if kp.name.lower() in product_lower or product_lower in kp.name.lower():
                product = kp
                break

    if not product:
        # Create new product
        product = Product(name=product_name, is_key_product=False)
        db.add(product)
        db.flush()

    # Get or create store product
    store_product = db.query(StoreProduct).filter(
        StoreProduct.product_id == product.id,
        StoreProduct.store_id == store.id
    ).first()

    if not store_product:
        store_product = StoreProduct(
            product_id=product.id,
            store_id=store.id,
            store_product_name=product_name
        )
        db.add(store_product)
        db.flush()

    # Create price entry
    try:
        price_decimal = Decimal(price)
        was_decimal = Decimal(was_price) if was_price else None
    except:
        return {"success": False, "error": f"Invalid price format: {price}"}

    new_price = Price(
        store_product_id=store_product.id,
        price=price_decimal,
        was_price=was_decimal,
        is_special=is_special,
        special_type=special_type,
        source="manual"
    )
    db.add(new_price)

    return {"success": True, "product_id": product.id}


def get_csv_template() -> str:
    """Get a CSV template with example data."""
    return """product_name,store_slug,price,was_price,is_special,special_type
Full Cream Milk 2L,woolworths,4.50,5.00,true,half_price
Full Cream Milk 2L,coles,4.40,,false,
Full Cream Milk 2L,aldi,3.99,,false,
Eggs Dozen Free Range,woolworths,6.50,8.00,true,special
Eggs Dozen Free Range,coles,6.00,,false,
Bananas per kg,woolworths,3.50,,false,
Bananas per kg,coles,3.20,4.00,true,price_drop
"""


def get_json_template() -> list:
    """Get a JSON template with example data."""
    return [
        {
            "product_name": "Full Cream Milk 2L",
            "store_slug": "woolworths",
            "price": 4.50,
            "was_price": 5.00,
            "is_special": True,
            "special_type": "half_price"
        },
        {
            "product_name": "Full Cream Milk 2L",
            "store_slug": "coles",
            "price": 4.40,
            "was_price": None,
            "is_special": False,
            "special_type": None
        },
        {
            "product_name": "Full Cream Milk 2L",
            "store_slug": "aldi",
            "price": 3.99,
            "was_price": None,
            "is_special": False,
            "special_type": None
        }
    ]
