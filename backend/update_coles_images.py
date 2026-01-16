"""Update Coles products with image URLs."""
import sys
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models import Store, Special

# Coles product images extracted from website
COLES_IMAGES = [
    {"name": "Coca-Cola Classic Soft Drink Bottle | 1.25L", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/123011.jpg"},
    {"name": "Mount Franklin Lightly Sparkling Water Lime | 10 Pack", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3738420.jpg"},
    {"name": "Coca-Cola No Sugar Soft Drink Bottle | 1.25L", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/1107616.jpg"},
    {"name": "Sprite Lemonade Soft Drink Bottle | 1.25L", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/123027.jpg"},
    {"name": "Fanta Orange Soft Drink Bottle | 1.25L", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/123012.jpg"},
    {"name": "Coca-Cola Classic Soft Drink Multipack Cans | 10 x 375mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5879688.jpg"},
    {"name": "Coca-Cola No Sugar Soft Drink Multipack Cans | 10 x 375mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5879704.jpg"},
    {"name": "Mount Franklin Still Water | 20 x 500mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/2/2428410.jpg"},
    {"name": "Sprite Lemonade Soft Drink Multipack Cans | 10 x 375mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5879696.jpg"},
    {"name": "Fanta Orange Soft Drink Multipack Cans | 10 x 375mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5879720.jpg"},
    {"name": "Pepsi Max No Sugar Cola Soft Drink | 1.25L", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/4/4808890.jpg"},
    {"name": "Pepsi Max No Sugar Cola Soft Drink | 30 x 375mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5628893.jpg"},
    {"name": "Solo Original Lemon Soft Drink | 1.25L", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/123057.jpg"},
    {"name": "Schweppes Lemonade Soft Drink | 1.1L", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/6/6154652.jpg"},
    {"name": "Kirks Lemonade Soft Drink | 10 x 375mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3738511.jpg"},
    {"name": "Bundaberg Ginger Beer | 4 x 375mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5067159.jpg"},
    {"name": "Red Bull Energy Drink | 4 x 250mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/6/6048227.jpg"},
    {"name": "V Energy Drink Original | 4 x 250mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/4/4850010.jpg"},
    {"name": "Monster Energy Drink | 4 x 500mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5879696.jpg"},
    {"name": "Lipton Ice Tea Peach | 6 x 327mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/4/4808882.jpg"},
    {"name": "Cascade Ginger Beer | 4 x 250mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/2/2597584.jpg"},
    {"name": "Coca-Cola Classic Soft Drink Multipack Cans | 30 x 375mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/1137887.jpg"},
    {"name": "Coca-Cola No Sugar Soft Drink Multipack Cans | 30 x 375mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/1107625.jpg"},
    {"name": "Schweppes Dry Ginger Ale | 4 x 300mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/4/4549740.jpg"},
    {"name": "Pepsi Cola Soft Drink | 1.25L", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/4/4808889.jpg"},
    {"name": "7UP Lemonade Soft Drink | 1.25L", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/123068.jpg"},
    {"name": "Kirks Pasito Soft Drink | 10 x 375mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3738502.jpg"},
    {"name": "V Energy Drink Sugar Free | 4 x 250mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/4/4850011.jpg"},
    {"name": "Red Bull Sugar Free Energy Drink | 4 x 250mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/6/6048228.jpg"},
    {"name": "Schweppes Tonic Water | 4 x 300mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/4/4549744.jpg"},
    {"name": "Coca-Cola Classic Soft Drink Bottle | 2L", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/123010.jpg"},
    {"name": "Coca-Cola No Sugar Soft Drink Bottle | 2L", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/1107615.jpg"},
    {"name": "Mountain Dew Citrus Soft Drink | 1.25L", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/123056.jpg"},
    {"name": "Kirks Creaming Soda Soft Drink | 10 x 375mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3738505.jpg"},
    {"name": "Bundaberg Blood Orange | 4 x 375mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5067162.jpg"},
    {"name": "Schweppes Soda Water | 4 x 300mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/4/4549743.jpg"},
    {"name": "Lipton Ice Tea Lemon | 6 x 327mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/4/4808881.jpg"},
    {"name": "Fuze Tea Peach Black Iced Tea | 6 x 327mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5628891.jpg"},
    {"name": "Deep Spring Lemon Mineral Water | 6 x 1.25L", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/123079.jpg"},
    {"name": "Sprite Lemonade Soft Drink Bottle | 2L", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/123026.jpg"},
    {"name": "Fanta Orange Soft Drink Bottle | 2L", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/123014.jpg"},
    {"name": "Solo Original Lemon Soft Drink | 10 x 375mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5879712.jpg"},
    {"name": "Pepsi Max No Sugar Cola Soft Drink | 10 x 375mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5628889.jpg"},
    {"name": "Mountain Dew Citrus Soft Drink | 10 x 375mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5879728.jpg"},
    {"name": "Schweppes Lime & Soda Water | 4 x 300mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/4/4549742.jpg"},
    {"name": "Cascade Tonic Water | 4 x 250mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/2/2597582.jpg"},
    {"name": "Bundaberg Lemon Lime & Bitters | 4 x 375mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5067160.jpg"},
    {"name": "Nexba Naturally Sugar Free Soft Drink Cola | 4 x 250mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/6/6154640.jpg"},
    {"name": "Nudie Nothing But Oranges Juice | 2L", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5628892.jpg"},
    {"name": "Berri Orange Juice | 2L", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/123095.jpg"},
    {"name": "Daily Juice Orange Juice | 2L", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/123097.jpg"},
    {"name": "Golden Circle Pineapple Juice | 2L", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/123093.jpg"},
    {"name": "Golden Circle Apple Juice | 2L", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/123092.jpg"},
    {"name": "Berri Apple Juice | 2L", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/123094.jpg"},
    {"name": "Daily Juice Apple Juice | 2L", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/123098.jpg"},
    {"name": "Coles Orange Juice | 3L", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/6/6154645.jpg"},
    {"name": "Coles Apple Juice | 3L", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/6/6154644.jpg"},
    {"name": "Coles Sparkling Water Lime | 12 x 375mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/6/6154646.jpg"},
    {"name": "Coles Sparkling Water Natural | 12 x 375mL", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/6/6154647.jpg"},
]


def normalize_name(name):
    """Normalize product name for matching."""
    # Remove common suffixes and clean up for matching
    name = name.lower().strip()
    # Remove size info for matching
    name = name.replace(' | ', ' ')
    return name


def update_coles_images():
    """Update Coles products with image URLs."""
    db = SessionLocal()

    store = db.query(Store).filter(Store.slug == 'coles').first()
    if not store:
        print('ERROR: Coles store not found')
        return

    # Get all Coles products
    coles_products = db.query(Special).filter(Special.store_id == store.id).all()
    print(f'Found {len(coles_products)} Coles products in database')

    updated = 0

    # Create lookup dict for faster matching
    image_lookup = {}
    for item in COLES_IMAGES:
        key = normalize_name(item['name'])
        image_lookup[key] = item['imageUrl']

    for product in coles_products:
        # Skip if already has image
        if product.image_url:
            continue

        product_key = normalize_name(product.name)

        # Try exact match first
        if product_key in image_lookup:
            product.image_url = image_lookup[product_key]
            updated += 1
            continue

        # Try partial match (product name contains or is contained by)
        for name_key, image_url in image_lookup.items():
            if name_key in product_key or product_key in name_key:
                product.image_url = image_url
                updated += 1
                break

    db.commit()
    db.close()

    print(f'Updated {updated} Coles products with images')


if __name__ == '__main__':
    update_coles_images()
