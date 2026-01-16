"""Save Woolworths specials to database."""
import sys
sys.path.insert(0, '.')

from decimal import Decimal
from datetime import date, timedelta
from app.database import SessionLocal
from app.models import Store, Category, Special

# Snacks & Confectionery products extracted from Woolworths
SNACKS_PRODUCTS = [
    {'name': 'Cadbury Dairy Milk Biscoff Chocolate Block 170g', 'price': '8.00', 'wasPrice': None, 'url': '/shop/productdetails/6054458/cadbury-dairy-milk-biscoff-chocolate-block'},
    {'name': 'Ritz Original Crackers 227g', 'price': '3.50', 'wasPrice': None, 'url': '/shop/productdetails/261282/ritz-original-crackers'},
    {'name': 'Oreo Mini Cookies Original Bags 10 pack 204g', 'price': '4.00', 'wasPrice': '5.00', 'url': '/shop/productdetails/317455/oreo-mini-cookies-original-bags-10-pack'},
    {'name': 'Oreo Original Cookies 128g', 'price': '3.00', 'wasPrice': None, 'url': '/shop/productdetails/318506/oreo-original-cookies'},
    {'name': 'Doritos Corn Chips Cheese Supreme Share Pack 170g', 'price': '5.00', 'wasPrice': None, 'url': '/shop/productdetails/826731/doritos-corn-chips-cheese-supreme-share-pack'},
    {"name": "Arnott's Cream Favourites Assorted Biscuits 500g", 'price': '5.50', 'wasPrice': '6.50', 'url': '/shop/productdetails/36022/arnott-s-cream-favourites-assorted-biscuits'},
    {'name': 'Cobs Popcorn Sea Salt Multipack Lunchbox Snacks 5 pack', 'price': '4.00', 'wasPrice': None, 'url': '/shop/productdetails/820459/cobs-popcorn-sea-salt-multipack-lunchbox-snacks'},
    {"name": "Arnott's Salada Original Crispbreads 250g", 'price': '4.00', 'wasPrice': None, 'url': '/shop/productdetails/36019/arnott-s-salada-original-crispbreads'},
    {'name': 'Pringles Sour Cream & Onion Potato Chips 134g', 'price': '5.50', 'wasPrice': None, 'url': '/shop/productdetails/479502/pringles-sour-cream-onion-potato-chips'},
    {"name": "Arnott's Shapes Chicken Crimpy Cracker Biscuits 175g", 'price': '4.00', 'wasPrice': None, 'url': '/shop/productdetails/384245/arnott-s-shapes-chicken-crimpy-cracker-biscuits'},
    {'name': 'Cadbury Dairy Milk Chocolate Block 180g', 'price': '8.00', 'wasPrice': None, 'url': '/shop/productdetails/814479/cadbury-dairy-milk-chocolate-block'},
    {'name': 'Mars Milk Chocolate Bar Party Share Bag 12 Pieces 192g', 'price': '7.00', 'wasPrice': None, 'url': '/shop/productdetails/160841/mars-milk-chocolate-bar-party-share-bag-12-pieces'},
    {"name": "M&M's Milk Chocolate Party Share Bag 11 Pieces 148g", 'price': '7.00', 'wasPrice': None, 'url': '/shop/productdetails/160839/m-m-s-milk-chocolate-party-share-bag-11-pieces'},
    {'name': 'Oreo Milk Chocolate Wafer Stick Cookies 10 pack 128g', 'price': '2.80', 'wasPrice': '3.50', 'url': '/shop/productdetails/729836/oreo-milk-chocolate-wafer-stick-cookies-10-pack'},
    {"name": "Arnott's Shapes Barbecue Cracker Biscuits 175g", 'price': '4.00', 'wasPrice': None, 'url': '/shop/productdetails/485436/arnott-s-shapes-barbecue-cracker-biscuits'},
    {"name": "Arnott's Cruskits Original Crispbreads 125g", 'price': '4.00', 'wasPrice': None, 'url': '/shop/productdetails/36059/arnott-s-cruskits-original-crispbreads'},
    {'name': 'Pringles Original Salted Potato Chips 134g', 'price': '5.50', 'wasPrice': None, 'url': '/shop/productdetails/479501/pringles-original-salted-potato-chips'},
    {'name': 'Red Rock Deli Potato Chips Honey Soy Chicken 165g', 'price': '6.00', 'wasPrice': None, 'url': '/shop/productdetails/781394/red-rock-deli-potato-chips-honey-soy-chicken'},
    {'name': 'Peckish Rice Crackers Original 90g', 'price': '1.85', 'wasPrice': '2.50', 'url': '/shop/productdetails/299533/peckish-rice-crackers-original'},
    {"name": "Arnott's Shapes Pizza Cracker Biscuits 190g", 'price': '4.00', 'wasPrice': None, 'url': '/shop/productdetails/515173/arnott-s-shapes-pizza-cracker-biscuits'},
    {'name': 'Red Rock Deli Potato Chips Sweet Chilli & Sour Cream 165g', 'price': '6.00', 'wasPrice': None, 'url': '/shop/productdetails/781370/red-rock-deli-potato-chips-sweet-chilli-sour-cream'},
    {'name': 'Red Rock Deli Potato Chips Sea Salt Natural 165g', 'price': '6.00', 'wasPrice': None, 'url': '/shop/productdetails/781396/red-rock-deli-potato-chips-sea-salt-natural'},
    {"name": "Arnott's Vita Weat 9 Grain Crispbreads 250g", 'price': '4.00', 'wasPrice': None, 'url': '/shop/productdetails/97482/arnott-s-vita-weat-9-grain-crispbreads'},
    {'name': 'Doritos Corn Chips Cheese Supreme Party Size 380g', 'price': '4.25', 'wasPrice': '8.50', 'url': '/shop/productdetails/54631/doritos-corn-chips-cheese-supreme-party-size'},
    {'name': 'Doritos Corn Chips Original Share Pack 170g', 'price': '5.00', 'wasPrice': None, 'url': '/shop/productdetails/826732/doritos-corn-chips-original-share-pack'},
    {'name': 'Cobs Popcorn Sweet & Salty Multipack Lunchbox Snacks 5 pack', 'price': '4.00', 'wasPrice': None, 'url': '/shop/productdetails/820458/cobs-popcorn-sweet-salty-multipack-lunchbox-snacks'},
    {"name": "Arnott's Shapes Cheese & Bacon Cracker Biscuits 180g", 'price': '4.00', 'wasPrice': None, 'url': '/shop/productdetails/384247/arnott-s-shapes-cheese-bacon-cracker-biscuits'},
    {'name': 'Red Rock Deli Potato Chips Sea Salt & Balsamic Vinegar 165g', 'price': '6.00', 'wasPrice': None, 'url': '/shop/productdetails/781402/red-rock-deli-potato-chips-sea-salt-balsamic-vinegar'},
    {"name": "Arnott's Cruskits 98% Fat Free Crispbreads 125g", 'price': '4.00', 'wasPrice': None, 'url': '/shop/productdetails/197462/arnott-s-cruskits-98-fat-free-crispbreads'},
    {"name": "Arnott's Milk Arrowroot Plain Biscuits Biscuits 250g", 'price': '2.20', 'wasPrice': '2.50', 'url': '/shop/productdetails/36009/arnott-s-milk-arrowroot-plain-biscuits-biscuits'},
    {'name': 'Sakata Rice Cracker Biscuits Plain 90g', 'price': '1.85', 'wasPrice': '2.50', 'url': '/shop/productdetails/956027/sakata-rice-cracker-biscuits-plain'},
    {'name': 'The Natural Confectionery Co. Snakes Lollies 230g', 'price': '2.50', 'wasPrice': '5.00', 'url': '/shop/productdetails/211973/the-natural-confectionery-co-snakes-lollies'},
    {'name': 'Sakata Rice Cracker Biscuits Seaweed 80g', 'price': '1.85', 'wasPrice': '2.50', 'url': '/shop/productdetails/955845/sakata-rice-cracker-biscuits-seaweed'},
    {'name': 'Red Rock Deli Potato Chips Lunchbox Snacks Assorted Multipack 10 pack', 'price': '8.90', 'wasPrice': None, 'url': '/shop/productdetails/299946/red-rock-deli-potato-chips-lunchbox-snacks-assorted-multipack'},
    {'name': 'Doritos Corn Chips Nacho Cheese Share Pack 170g', 'price': '5.00', 'wasPrice': None, 'url': '/shop/productdetails/826700/doritos-corn-chips-nacho-cheese-share-pack'},
    {"name": "Smith's Crinkle Cut Potato Chips Party Bag Original 380g", 'price': '4.25', 'wasPrice': '8.50', 'url': '/shop/productdetails/54665/smith-s-crinkle-cut-potato-chips-party-bag-original'},
    {'name': 'Peckish Flavoured Rice Crackers Cheddar Cheese 90g', 'price': '1.85', 'wasPrice': '2.50', 'url': '/shop/productdetails/299513/peckish-flavoured-rice-crackers-cheddar-cheese'},
    {'name': 'The Natural Confectionery Co. Party Mix Lollies 220g', 'price': '2.50', 'wasPrice': '5.00', 'url': '/shop/productdetails/211982/the-natural-confectionery-co-party-mix-lollies'},
    {'name': 'Pringles BBQ Stacked Potato Chips 134g', 'price': '5.50', 'wasPrice': None, 'url': '/shop/productdetails/479504/pringles-bbq-stacked-potato-chips'},
    {'name': 'Cheezels Cheese Box 125g', 'price': '2.80', 'wasPrice': '3.50', 'url': '/shop/productdetails/660337/cheezels-cheese-box'},
    {"name": "Arnott's Savoy Original Crackers 225g", 'price': '4.00', 'wasPrice': None, 'url': '/shop/productdetails/384252/arnott-s-savoy-original-crackers'},
    {'name': 'Cobs Popcorn Best Ever Butter Multipack Lunchbox Snacks 5 pack', 'price': '4.00', 'wasPrice': None, 'url': '/shop/productdetails/180279/cobs-popcorn-best-ever-butter-multipack-lunchbox-snacks'},
]


def save_products(products, category_slug):
    """Save products to database."""
    db = SessionLocal()

    store = db.query(Store).filter(Store.slug == 'woolworths').first()
    if not store:
        print('ERROR: Woolworths store not found')
        return

    category = db.query(Category).filter(Category.slug == category_slug).first()
    category_id = category.id if category else None

    valid_from = date.today()
    valid_to = valid_from + timedelta(days=7)

    saved = 0
    updated = 0

    for p in products:
        try:
            existing = db.query(Special).filter(
                Special.store_id == store.id,
                Special.name == p['name']
            ).first()

            price = Decimal(p['price'])
            was_price = Decimal(p['wasPrice']) if p.get('wasPrice') else None

            discount_percent = None
            if was_price and was_price > price:
                discount_percent = int(((was_price - price) / was_price) * 100)

            if existing:
                existing.price = price
                existing.was_price = was_price
                existing.discount_percent = discount_percent
                existing.product_url = 'https://www.woolworths.com.au' + p['url']
                existing.valid_from = valid_from
                existing.valid_to = valid_to
                updated += 1
            else:
                special = Special(
                    store_id=store.id,
                    category_id=category_id,
                    name=p['name'],
                    price=price,
                    was_price=was_price,
                    discount_percent=discount_percent,
                    product_url='https://www.woolworths.com.au' + p['url'],
                    valid_from=valid_from,
                    valid_to=valid_to
                )
                db.add(special)
                saved += 1
        except Exception as e:
            print(f'Error saving {p["name"]}: {e}')

    db.commit()
    db.close()

    print(f'Woolworths {category_slug}: Saved {saved}, Updated {updated}')
    return {'saved': saved, 'updated': updated}


if __name__ == '__main__':
    print('Saving Woolworths Snacks & Confectionery specials...')
    save_products(SNACKS_PRODUCTS, 'snacks-confectionery')
