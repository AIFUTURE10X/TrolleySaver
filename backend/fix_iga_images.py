"""Fix IGA product images using product IDs from JSON."""
import sys
import json
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models import Store, Special


def normalize_name(name):
    """Normalize product name for matching."""
    return name.lower().strip()


def fix_iga_images():
    """Update IGA products with image URLs from JSON data."""
    # Load IGA JSON data
    with open('iga_specials.json', 'r', encoding='utf-8') as f:
        iga_json = json.load(f)

    # Create lookup dict by normalized name
    image_lookup = {}
    url_lookup = {}
    for item in iga_json:
        key = normalize_name(item['name'])
        product_id = item.get('product_id')
        if product_id:
            # Use the discovered IGA image URL pattern
            image_lookup[key] = f'https://cdn.metcash.media/image/upload/f_auto,c_limit,w_750,q_auto/igashop/images/{product_id}'
        if item.get('url'):
            url_lookup[key] = item['url']

    print(f'Loaded {len(iga_json)} products from JSON')
    print(f'Products with IDs for images: {len(image_lookup)}')

    db = SessionLocal()

    store = db.query(Store).filter(Store.slug == 'iga').first()
    if not store:
        print('ERROR: IGA store not found')
        return

    # Get all IGA products
    products = db.query(Special).filter(Special.store_id == store.id).all()
    print(f'Found {len(products)} IGA products in database')

    updated_images = 0
    updated_urls = 0
    not_found = []

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
        found = False
        for name_key, image_url in image_lookup.items():
            # Check if names are similar enough
            if name_key in product_key or product_key in name_key:
                if not p.image_url:
                    p.image_url = image_url
                    updated_images += 1
                if not p.product_url and name_key in url_lookup:
                    p.product_url = url_lookup[name_key]
                    updated_urls += 1
                found = True
                break

        if not found and not p.image_url:
            not_found.append(p.name)

    db.commit()
    db.close()

    print(f'Updated {updated_images} IGA products with images')
    print(f'Updated {updated_urls} IGA products with URLs')
    if not_found:
        print(f'Could not find images for {len(not_found)} products:')
        for name in not_found[:10]:
            print(f'  - {name}')
        if len(not_found) > 10:
            print(f'  ... and {len(not_found) - 10} more')


if __name__ == '__main__':
    fix_iga_images()
