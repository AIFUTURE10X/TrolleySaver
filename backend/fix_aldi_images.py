"""Fix ALDI product images from JSON data."""
import sys
import json
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models import Store, Special


def normalize_name(name):
    """Normalize product name for matching."""
    return name.lower().strip()


def fix_aldi_images():
    """Update ALDI products with image URLs from JSON."""
    # Load ALDI JSON data
    with open('aldi_specials.json', 'r', encoding='utf-8') as f:
        aldi_json = json.load(f)

    # Create lookup dict by normalized name
    image_lookup = {}
    url_lookup = {}
    for item in aldi_json:
        key = normalize_name(item['name'])
        if item.get('image_url'):
            image_lookup[key] = item['image_url']
        if item.get('url'):
            url_lookup[key] = item['url']

    print(f'Loaded {len(aldi_json)} products from JSON')
    print(f'Products with images: {len(image_lookup)}')

    db = SessionLocal()

    store = db.query(Store).filter(Store.slug == 'aldi').first()
    if not store:
        print('ERROR: ALDI store not found')
        return

    # Get all ALDI products
    products = db.query(Special).filter(Special.store_id == store.id).all()
    print(f'Found {len(products)} ALDI products in database')

    updated_images = 0
    updated_urls = 0

    for p in products:
        product_key = normalize_name(p.name)

        # Try exact match first
        if product_key in image_lookup:
            if not p.image_url:
                p.image_url = image_lookup[product_key]
                updated_images += 1
            if not p.product_url and product_key in url_lookup:
                p.product_url = url_lookup[product_key]
                updated_urls += 1
            continue

        # Try partial match
        for name_key, image_url in image_lookup.items():
            if name_key in product_key or product_key in name_key:
                if not p.image_url:
                    p.image_url = image_url
                    updated_images += 1
                if not p.product_url and name_key in url_lookup:
                    p.product_url = url_lookup[name_key]
                    updated_urls += 1
                break

    db.commit()
    db.close()

    print(f'Updated {updated_images} ALDI products with images')
    print(f'Updated {updated_urls} ALDI products with URLs')


if __name__ == '__main__':
    fix_aldi_images()
