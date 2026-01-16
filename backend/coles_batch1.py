"""Save Coles specials batch 1 to database."""
import sys
sys.path.insert(0, '.')

from decimal import Decimal
from datetime import date, timedelta
from app.database import SessionLocal
from app.models import Store, Special

COLES_PRODUCTS = [
    {"name": "Coles Strawberries | 250g", "price": "3.50", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5191256.jpg", "url": "https://www.coles.com.au/product/coles-strawberries-250g-5191256"},
    {"name": "Maggi 2 Minute Instant Noodles Chicken Flavour 5 Pack | 360g", "price": "3.50", "wasPrice": "5.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5366972.jpg", "url": "https://www.coles.com.au/product/maggi-2-minute-instant-noodles-chicken-flavour-5-pack-360g-5366972"},
    {"name": "Norsca Forest Fresh 48Hr Anti Perspirant Deodorant | 212mL", "price": "4.25", "wasPrice": "8.50", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/6/6405617.jpg", "url": "https://www.coles.com.au/product/norsca-forest-fresh-48hr-anti-perspirant-deodorant-212ml-6405617"},
    {"name": "Norsca Instant Adrenaline 48hr Anti Perspirant Deodorant | 212mL", "price": "4.25", "wasPrice": "8.50", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/6/6405606.jpg", "url": "https://www.coles.com.au/product/norsca-instant-adrenaline-48hr-anti-perspirant-deodorant-212ml-6405606"},
    {"name": "Milo Chocolate Malt Powder Hot Or Cold Drink | 460g", "price": "7.50", "wasPrice": "10.70", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3516338.jpg", "url": "https://www.coles.com.au/product/milo-chocolate-malt-powder-hot-or-cold-drink-460g-3516338"},
    {"name": "Health Lab Cookie Dough Custard Filled Ball | 40GRAM", "price": "2.50", "wasPrice": "3.50", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/8/8883380.jpg", "url": "https://www.coles.com.au/product/health-lab-cookie-dough-custard-filled-ball-40gram-8883380"},
    {"name": "Robert Timms Coffee Bags Gold Columbia | 24 Pack", "price": "9.00", "wasPrice": "13.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/1049413.jpg", "url": "https://www.coles.com.au/product/robert-timms-coffee-bags-gold-columbia-24-pack-1049413"},
    {"name": "1800 Coconut Tequila Liqueur 700ml | 1 Each", "price": "72.00", "wasPrice": "84.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/2/2710131.jpg", "url": "https://www.coles.com.au/product/1800-coconut-tequila-liqueur-700ml-1-each-2710131"},
    {"name": "Huon Salmon Steak Skinless Chef's Cut | 200g", "price": "11.00", "wasPrice": "13.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/1058629.jpg", "url": "https://www.coles.com.au/product/huon-salmon-steak-skinless-chef's-cut-200g-1058629"},
    {"name": "Snacktacular Fruit Crisps Disney Frozen Raspberry- Banana & Apple | 5 pack", "price": "3.00", "wasPrice": "5.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/8/8935473.jpg", "url": "https://www.coles.com.au/product/snacktacular-fruit-crisps-disney-frozen-raspberry-banana-and-apple-5-pack-8935473"},
    {"name": "Robert Timms Coffee Bags Italian Espresso | 24 Pack", "price": "9.00", "wasPrice": "13.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/1049402.jpg", "url": "https://www.coles.com.au/product/robert-timms-coffee-bags-italian-espresso-24-pack-1049402"},
    {"name": "Coca-Cola Classic Soft Drink Bottle | 1.25L", "price": "2.00", "wasPrice": "4.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/123011.jpg", "url": "https://www.coles.com.au/product/coca-cola-classic-soft-drink-bottle-1.25l-123011"},
    {"name": "Coca-Cola Zero Sugar Soft Drink Bottle | 1.25L", "price": "2.00", "wasPrice": "4.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/2/2993706.jpg", "url": "https://www.coles.com.au/product/coca-cola-zero-sugar-soft-drink-bottle-1.25l-2993706"},
    {"name": "Snickers Milk Chocolate Bar Peanuts Caramel | 44g", "price": "1.25", "wasPrice": "2.50", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/2/245868.jpg", "url": "https://www.coles.com.au/product/snickers-milk-chocolate-bar-peanuts-caramel-44g-245868"},
    {"name": "Nongshim Shin Toomba Stir Fry 137g | 4 Pack", "price": "4.50", "wasPrice": "9.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/9/9955137.jpg", "url": "https://www.coles.com.au/product/nongshim-shin-toomba-stir-fry-137g-4-pack-9955137"},
    {"name": "Nestle Kit Kat Chocolate Milk 4 Finger Bar | 42g", "price": "1.50", "wasPrice": "3.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/9/9229441.jpg", "url": "https://www.coles.com.au/product/nestle-kit-kat-chocolate-milk-4-finger-bar-42g-9229441"},
    {"name": "Arnott's Shapes Original Bbq | 175g", "price": "2.00", "wasPrice": "4.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/2/2734446.jpg", "url": "https://www.coles.com.au/product/arnott's-shapes-original-bbq-175g-2734446"},
    {"name": "Golden Crumpet Rounds Original | 300g", "price": "2.40", "wasPrice": "4.80", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/332383.jpg", "url": "https://www.coles.com.au/product/golden-crumpet-rounds-original-300g-332383"},
    {"name": "Sprite Lemonade Soft Drink Bottle | 1.25L", "price": "2.00", "wasPrice": "4.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/4/401657.jpg", "url": "https://www.coles.com.au/product/sprite-lemonade-soft-drink-bottle-1.25l-401657"},
    {"name": "Mars Milk Chocolate Bar Caramel Nougat | 47g", "price": "1.25", "wasPrice": "2.50", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/138201.jpg", "url": "https://www.coles.com.au/product/mars-milk-chocolate-bar-caramel-nougat-47g-138201"},
    {"name": "Cobs Lightly Salted Slightly Sweet Popcorn | 120g", "price": "1.75", "wasPrice": "3.50", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/6/6772389.jpg", "url": "https://www.coles.com.au/product/cobs-lightly-salted-slightly-sweet-popcorn-120g-6772389"},
    {"name": "Arnott's Shapes Original Pizza | 190g", "price": "2.00", "wasPrice": "4.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/2/2734457.jpg", "url": "https://www.coles.com.au/product/arnott's-shapes-original-pizza-190g-2734457"},
    {"name": "Sprite Zero Sugar Lemonade Soft Drink Bottle | 1.25L", "price": "2.00", "wasPrice": "4.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3585567.jpg", "url": "https://www.coles.com.au/product/sprite-zero-sugar-lemonade-soft-drink-bottle-1.25l-3585567"},
    {"name": "Sorbent 3 Ply Hypo Allergenic Toilet Paper | 12 Pack", "price": "5.50", "wasPrice": "11.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5865350.jpg", "url": "https://www.coles.com.au/product/sorbent-3-ply-hypo-allergenic-toilet-paper-12-pack-5865350"},
    {"name": "Coca-Cola Zero Sugar Caffeine Free Soft Drink Bottle | 1.25L", "price": "2.00", "wasPrice": "4.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3989555.jpg", "url": "https://www.coles.com.au/product/coca-cola-zero-sugar-caffeine-free-soft-drink-bottle-1.25l-3989555"},
    {"name": "Schweppes Soda Water Bottle Classic Mixers | 1.1L", "price": "1.50", "wasPrice": "3.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3014770.jpg", "url": "https://www.coles.com.au/product/schweppes-soda-water-bottle-classic-mixers-1.1l-3014770"},
    {"name": "Arnott's Shapes Crimpy Chicken | 175g", "price": "2.00", "wasPrice": "4.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/8/8638285.jpg", "url": "https://www.coles.com.au/product/arnott's-shapes-crimpy-chicken-175g-8638285"},
    {"name": "Coca-Cola Vanilla Soft Drink | 1.25L", "price": "2.00", "wasPrice": "4.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/9/9391600.jpg", "url": "https://www.coles.com.au/product/coca-cola-vanilla-soft-drink-1.25l-9391600"},
    {"name": "Peters Drumstick Minis Classic Vanilla 6 Pack | 490mL", "price": "4.75", "wasPrice": "9.50", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5863445.jpg", "url": "https://www.coles.com.au/product/peters-drumstick-minis-classic-vanilla-6-pack-490ml-5863445"},
    {"name": "Fanta Orange Soft Drink | 1.25L", "price": "2.00", "wasPrice": "4.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/123022.jpg", "url": "https://www.coles.com.au/product/fanta-orange-soft-drink-1.25l-123022"},
    {"name": "Cobs Gluten Free Popcorn Sea Salt | 80g", "price": "1.75", "wasPrice": "3.50", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/6/6772593.jpg", "url": "https://www.coles.com.au/product/cobs-gluten-free-popcorn-sea-salt-80g-6772593"},
    {"name": "Peters Drumstick Classic Vanilla 4 Pack | 475mL", "price": "4.75", "wasPrice": "9.50", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/193844.jpg", "url": "https://www.coles.com.au/product/peters-drumstick-classic-vanilla-4-pack-475ml-193844"},
    {"name": "Schweppes Agrum Blood Orange Soft Drink Bottle | 1.1L", "price": "1.50", "wasPrice": "3.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3014850.jpg", "url": "https://www.coles.com.au/product/schweppes-agrum-blood-orange-soft-drink-bottle-1.1l-3014850"},
    {"name": "Schweppes Lemon Lime Bitters Soft Drink Classic Mixers Bottle | 1.1L", "price": "1.50", "wasPrice": "3.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3014839.jpg", "url": "https://www.coles.com.au/product/schweppes-lemon-lime-bitters-soft-drink-classic-mixers-bottle-1.1l-3014839"},
    {"name": "Twisties Minis Cheese Flavoured Snacks | 115g", "price": "5.50", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/1143353.jpg", "url": "https://www.coles.com.au/product/twisties-minis-cheese-flavoured-snacks-115g-1143353"},
    {"name": "Fanta Orange Zero Sugar Soft Drink Bottle | 1.25L", "price": "2.00", "wasPrice": "4.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3585556.jpg", "url": "https://www.coles.com.au/product/fanta-orange-zero-sugar-soft-drink-bottle-1.25l-3585556"},
    {"name": "Coca-Cola Diet Coke Soft Drink Bottle | 1.25L", "price": "2.00", "wasPrice": "4.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/4/419211.jpg", "url": "https://www.coles.com.au/product/coca-cola-diet-coke-soft-drink-bottle-1.25l-419211"},
    {"name": "Nestle Kit Kat Chunky Chocolate Bar | 48g", "price": "1.50", "wasPrice": "3.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/9/9231862.jpg", "url": "https://www.coles.com.au/product/nestle-kit-kat-chunky-chocolate-bar-48g-9231862"},
    {"name": "Handee Ultra Paper Towels Crisp White | 2 pack", "price": "2.15", "wasPrice": "4.30", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5294180.jpg", "url": "https://www.coles.com.au/product/handee-ultra-paper-towels-crisp-white-2-pack-5294180"},
    {"name": "Coca-Cola Zero Sugar Vanilla Soft Drink Bottle | 1.25L", "price": "2.00", "wasPrice": "4.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3271060.jpg", "url": "https://www.coles.com.au/product/coca-cola-zero-sugar-vanilla-soft-drink-bottle-1.25l-3271060"},
    {"name": "Oral B Pro 300 Precision Clean Electric Toothbrush Black | 1 Pack", "price": "45.00", "wasPrice": "90.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5930156.jpg", "url": "https://www.coles.com.au/product/oral-b-pro-300-precision-clean-electric-toothbrush-black-1-pack-5930156"},
    {"name": "Oral B Pro 300 Precision Clean Electric Toothbrush Mint | 1 Pack", "price": "45.00", "wasPrice": "90.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5939536.jpg", "url": "https://www.coles.com.au/product/oral-b-pro-300-precision-clean-electric-toothbrush-mint-1-pack-5939536"},
    {"name": "Oral B Pro 300 Kids Electric Toothbrush Frozen Or Spiderman | 1 pack", "price": "45.00", "wasPrice": "90.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/7/7536574.jpg", "url": "https://www.coles.com.au/product/oral-b-pro-300-kids-electric-toothbrush-frozen-or-spiderman-1-pack-7536574"},
    {"name": "Peters Drumstick Super Choc 4 Pack | 475mL", "price": "4.75", "wasPrice": "9.50", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5197274.jpg", "url": "https://www.coles.com.au/product/peters-drumstick-super-choc-4-pack-475ml-5197274"},
    {"name": "Thins Original Potato Chips | 175g", "price": "2.50", "wasPrice": "5.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/6/6833891.jpg", "url": "https://www.coles.com.au/product/thins-original-potato-chips-175g-6833891"},
    {"name": "Haagen-Dazs Strawberries And Cream Ice Cream | 457mL", "price": "6.75", "wasPrice": "13.50", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/2/2983837.jpg", "url": "https://www.coles.com.au/product/haagen-dazs-strawberries-and-cream-ice-cream-457ml-2983837"},
    {"name": "Fanta Grape Zero Soft Drink Bottle | 1.25L", "price": "2.00", "wasPrice": "4.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/8/8475920.jpg", "url": "https://www.coles.com.au/product/fanta-grape-zero-soft-drink-bottle-1.25l-8475920"},
    {"name": "Aero Peppermint Milk Chocolate Bar | 40g", "price": "1.50", "wasPrice": "3.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5823950.jpg", "url": "https://www.coles.com.au/product/aero-peppermint-milk-chocolate-bar-40g-5823950"},
    {"name": "Cobs Gluten Free Popcorn Butter | 90g", "price": "1.75", "wasPrice": "3.50", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3434856.jpg", "url": "https://www.coles.com.au/product/cobs-gluten-free-popcorn-butter-90g-3434856"},
    {"name": "Arnott's Shapes Cheese Bacon | 180g", "price": "2.00", "wasPrice": "4.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/8/8638241.jpg", "url": "https://www.coles.com.au/product/arnott's-shapes-cheese-bacon-180g-8638241"},
    {"name": "Schweppes Zero Sugar Mixers Lemon Lime & Bitters Soft Drink | 1.1L", "price": "1.50", "wasPrice": "3.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3752738.jpg", "url": "https://www.coles.com.au/product/schweppes-zero-sugar-mixers-lemon-lime-and-bitters-soft-drink-1.1l-3752738"},
    {"name": "Arnott's Shapes Cheddar | 175g", "price": "2.00", "wasPrice": "4.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/8/8638263.jpg", "url": "https://www.coles.com.au/product/arnott's-shapes-cheddar-175g-8638263"},
    {"name": "Cheetos Puffs Flaming Hot | 80g", "price": "1.35", "wasPrice": "2.70", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3706810.jpg", "url": "https://www.coles.com.au/product/cheetos-puffs-flaming-hot-80g-3706810"},
    {"name": "Fairy 5 Power Action Lemon Dishwashing Tablets | 70 Pack", "price": "38.00", "wasPrice": "76.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/1420602.jpg", "url": "https://www.coles.com.au/product/fairy-5-power-action-lemon-dishwashing-tablets-70-pack-1420602"},
    {"name": "Thins Light & Tangy Potato Chips | 175g", "price": "2.50", "wasPrice": "5.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/6/6833927.jpg", "url": "https://www.coles.com.au/product/thins-light-and-tangy-potato-chips-175g-6833927"},
    {"name": "Schweppes Mixers Tonic Water | 1.1L", "price": "1.50", "wasPrice": "3.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3014806.jpg", "url": "https://www.coles.com.au/product/schweppes-mixers-tonic-water-1.1l-3014806"},
    {"name": "Nescafe Strong Cappuccino Coffee Sachets | 10 pack", "price": "4.00", "wasPrice": "8.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5694097.jpg", "url": "https://www.coles.com.au/product/nescafe-strong-cappuccino-coffee-sachets-10-pack-5694097"},
    {"name": "Cheetos Puffs | 80g", "price": "1.35", "wasPrice": "2.70", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3706774.jpg", "url": "https://www.coles.com.au/product/cheetos-puffs-80g-3706774"},
    {"name": "Twisties Cheese | 90g", "price": "1.35", "wasPrice": "2.70", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3706832.jpg", "url": "https://www.coles.com.au/product/twisties-cheese-90g-3706832"},
]


def save_products():
    """Save Coles products to database."""
    db = SessionLocal()

    store = db.query(Store).filter(Store.slug == 'coles').first()
    if not store:
        print('ERROR: Coles store not found')
        return

    valid_from = date.today()
    valid_to = valid_from + timedelta(days=7)

    saved = 0
    updated = 0

    for p in COLES_PRODUCTS:
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
                existing.image_url = p['imageUrl']
                existing.product_url = p['url']
                existing.valid_from = valid_from
                existing.valid_to = valid_to
                updated += 1
            else:
                special = Special(
                    store_id=store.id,
                    name=p['name'],
                    price=price,
                    was_price=was_price,
                    discount_percent=discount_percent,
                    image_url=p['imageUrl'],
                    product_url=p['url'],
                    valid_from=valid_from,
                    valid_to=valid_to
                )
                db.add(special)
                saved += 1
        except Exception as e:
            print(f'Error saving {p["name"]}: {e}')

    db.commit()
    db.close()

    print(f'Coles batch 1: Saved {saved}, Updated {updated}')


if __name__ == '__main__':
    save_products()
