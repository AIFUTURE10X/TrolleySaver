"""Fix all Woolworths product images with correct URL pattern."""
import sys
import re
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models import Store, Special


def fix_woolworths_images():
    """Update all Woolworths products with correct image URLs."""
    db = SessionLocal()

    store = db.query(Store).filter(Store.slug == 'woolworths').first()
    if not store:
        print('ERROR: Woolworths store not found')
        return

    # Get all Woolworths products
    products = db.query(Special).filter(Special.store_id == store.id).all()
    print(f'Found {len(products)} Woolworths products')

    updated = 0
    failed = 0

    for p in products:
        if not p.product_url:
            failed += 1
            continue

        # Extract product ID from URL
        # URL format: https://www.woolworths.com.au/shop/productdetails/89121/product-name
        match = re.search(r'/productdetails/(\d+)/', p.product_url)
        if match:
            product_id = match.group(1)
            # Use the correct Woolworths image URL pattern
            new_image_url = f'https://assets.woolworths.com.au/images/1005/{product_id}.jpg?impolicy=wowsmkqiema&w=600&h=600'
            p.image_url = new_image_url
            updated += 1
        else:
            print(f'Could not extract product ID from: {p.product_url}')
            failed += 1

    db.commit()
    db.close()

    print(f'Updated {updated} Woolworths products with correct image URLs')
    print(f'Failed to update {failed} products')


if __name__ == '__main__':
    fix_woolworths_images()
