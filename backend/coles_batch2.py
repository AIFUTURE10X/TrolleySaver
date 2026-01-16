"""Save Coles dairy specials to database."""
import sys
sys.path.insert(0, '.')

from decimal import Decimal
from datetime import date, timedelta
from app.database import SessionLocal
from app.models import Store, Special

COLES_PRODUCTS = [
    {"name": "Chobani Fit Flip Yogurt Caramel Choc Peanut | 142g", "price": "2.25", "wasPrice": "4.50", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/1154611.jpg", "url": "https://www.coles.com.au/product/chobani-fit-flip-yogurt-caramel-choc-peanut-142g-1154611"},
    {"name": "Nuffin Chive & Onion Dip | 200g", "price": "4.00", "wasPrice": "5.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/7/7757609.jpg", "url": "https://www.coles.com.au/product/nuffin-chive-and-onion-dip-200g-7757609"},
    {"name": "Latina Fresh Beef Ravioli Pasta | 375g", "price": "6.40", "wasPrice": "8.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5051858.jpg", "url": "https://www.coles.com.au/product/latina-fresh-beef-ravioli-pasta-375g-5051858"},
    {"name": "Nuffin Fetta & Cracked Pepper Dip | 200g", "price": "4.00", "wasPrice": "5.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/7/7757697.jpg", "url": "https://www.coles.com.au/product/nuffin-fetta-and-cracked-pepper-dip-200g-7757697"},
    {"name": "Latina Creamy Carbonara Pasta Sauce | 250g", "price": "4.40", "wasPrice": "5.50", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/9/9954622.jpg", "url": "https://www.coles.com.au/product/latina-creamy-carbonara-pasta-sauce-250g-9954622"},
    {"name": "Nuffin Fetta And Basil Dip | 200g", "price": "4.00", "wasPrice": "5.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/1051663.jpg", "url": "https://www.coles.com.au/product/nuffin-fetta-and-basil-dip-200g-1051663"},
    {"name": "Latina Fresh Spinach & Ricotta Agnolotti Pasta | 375g", "price": "6.40", "wasPrice": "8.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5280232.jpg", "url": "https://www.coles.com.au/product/latina-fresh-spinach-and-ricotta-agnolotti-pasta-375g-5280232"},
    {"name": "Perfect Italiano Grated Cheese Perfect Pizza | 250g", "price": "5.20", "wasPrice": "6.50", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3273994.jpg", "url": "https://www.coles.com.au/product/perfect-italiano-grated-cheese-perfect-pizza-250g-3273994"},
    {"name": "Nuffin Creamy Garlic Dip With Fresh Parsley | 200g", "price": "4.00", "wasPrice": "5.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/8/8711261.jpg", "url": "https://www.coles.com.au/product/nuffin-creamy-garlic-dip-with-fresh-parsley-200g-8711261"},
    {"name": "Latina Creamy Sun Dried Tomato Sauce | 250g", "price": "4.40", "wasPrice": "5.50", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/9/9954644.jpg", "url": "https://www.coles.com.au/product/latina-creamy-sun-dried-tomato-sauce-250g-9954644"},
    {"name": "Perfect Italiano Shredded Mozzarella | 250g", "price": "5.20", "wasPrice": "6.50", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3562164.jpg", "url": "https://www.coles.com.au/product/perfect-italiano-shredded-mozzarella-250g-3562164"},
    {"name": "Chobani Fit Flip Yogurt Vanilla Choc Almond | 140g", "price": "2.25", "wasPrice": "4.50", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/1154622.jpg", "url": "https://www.coles.com.au/product/chobani-fit-flip-yogurt-vanilla-choc-almond-140g-1154622"},
    {"name": "Chobani Fit Flip Yogurt Banana Choc Peanut | 140g", "price": "2.25", "wasPrice": "4.50", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/1154666.jpg", "url": "https://www.coles.com.au/product/chobani-fit-flip-yogurt-banana-choc-peanut-140g-1154666"},
    {"name": "Chang's Super Lo-Cal Thin Noodles | 390g", "price": "1.50", "wasPrice": "3.00", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/8/8864976.jpg", "url": "https://www.coles.com.au/product/chang's-super-lo-cal-thin-noodles-390g-8864976"},
    {"name": "Babybel Mini Cheese Original 10 Pack | 200g", "price": "9.00", "wasPrice": "11.20", "imageUrl": "https://cdn.productimages.coles.com.au/productimages/6/6165047.jpg", "url": "https://www.coles.com.au/product/babybel-mini-cheese-original-10-pack-200g-6165047"},
    {"name": "Farmers Union Greek Yoghurt Pouch Strawberry | 130g", "price": "2.50", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3251415.jpg", "url": "https://www.coles.com.au/product/farmers-union-greek-yoghurt-pouch-strawberry-130g-3251415"},
    {"name": "Farmers Union Greek Yoghurt Pouch Mango | 130g", "price": "2.50", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3305810.jpg", "url": "https://www.coles.com.au/product/farmers-union-greek-yoghurt-pouch-mango-130g-3305810"},
    {"name": "Primo Champagne Leg Ham | 100g", "price": "3.95", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3055086.jpg", "url": "https://www.coles.com.au/product/primo-champagne-leg-ham-100g-3055086"},
    {"name": "Primo English Ham | 100g", "price": "3.95", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/8/8145856.jpg", "url": "https://www.coles.com.au/product/primo-english-ham-100g-8145856"},
    {"name": "Primo Chicken Breast Thinly Sliced | 80g", "price": "3.95", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/2/2814057.jpg", "url": "https://www.coles.com.au/product/primo-chicken-breast-thinly-sliced-80g-2814057"},
    {"name": "Yoplait Petit Miam Kids Yoghurt Pouch Strawberry | 70g", "price": "1.20", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/6/6569239.jpg", "url": "https://www.coles.com.au/product/yoplait-petit-miam-kids-yoghurt-pouch-strawberry-70g-6569239"},
    {"name": "Yoplait Petite Miam Kids Yoghurt Pouch Blueberry | 70g", "price": "1.20", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/8/8126057.jpg", "url": "https://www.coles.com.au/product/yoplait-petite-miam-kids-yoghurt-pouch-blueberry-70g-8126057"},
    {"name": "Primo Mild Hungarian Salami | 80g", "price": "3.95", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/2/2814013.jpg", "url": "https://www.coles.com.au/product/primo-mild-hungarian-salami-80g-2814013"},
    {"name": "Farmers Union Greek Yoghurt Pouch Vanilla | 130g", "price": "2.50", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3087060.jpg", "url": "https://www.coles.com.au/product/farmers-union-greek-yoghurt-pouch-vanilla-130g-3087060"},
    {"name": "Black Swan Tzatziki Dip | 200g", "price": "4.50", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/9/9580657.jpg", "url": "https://www.coles.com.au/product/black-swan-tzatziki-dip-200g-9580657"},
    {"name": "Primo Double Smoked Ham | 100g", "price": "3.95", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/2/2819436.jpg", "url": "https://www.coles.com.au/product/primo-double-smoked-ham-100g-2819436"},
    {"name": "Coles Kitchen Butter Chicken With Rice | 350g", "price": "8.00", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/7/7325091.jpg", "url": "https://www.coles.com.au/product/coles-kitchen-butter-chicken-with-rice-350g-7325091"},
    {"name": "Big M Chocolate Flavoured Milk | 600mL", "price": "3.80", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3034246.jpg", "url": "https://www.coles.com.au/product/big-m-chocolate-flavoured-milk-600ml-3034246"},
    {"name": "Yoplait Petit Miam Mango Yoghurt Pouch | 70g", "price": "1.20", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3536368.jpg", "url": "https://www.coles.com.au/product/yoplait-petit-miam-mango-yoghurt-pouch-70g-3536368"},
    {"name": "Farmers Union Greek Yoghurt Pouch Passionfruit | 130g", "price": "2.50", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3306765.jpg", "url": "https://www.coles.com.au/product/farmers-union-greek-yoghurt-pouch-passionfruit-130g-3306765"},
    {"name": "Primo Short Cut Bacon | 200g", "price": "6.80", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/4/4260568.jpg", "url": "https://www.coles.com.au/product/primo-short-cut-bacon-200g-4260568"},
    {"name": "Black Swan Spicy Capsicum Dip | 200g", "price": "4.50", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/7/7604867.jpg", "url": "https://www.coles.com.au/product/black-swan-spicy-capsicum-dip-200g-7604867"},
    {"name": "Activia Probiotics Yoghurt No Added Sugar Vanilla 4x125g | 500g", "price": "6.00", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/8/8169355.jpg", "url": "https://www.coles.com.au/product/activia-probiotics-yoghurt-no-added-sugar-vanilla-4x125g-500g-8169355"},
    {"name": "Black Swan Hommus Dip | 200g", "price": "4.50", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/9/9580680.jpg", "url": "https://www.coles.com.au/product/black-swan-hommus-dip-200g-9580680"},
    {"name": "Ultimate Yoghurt Tropical Mango 4x115g | 4 Pack", "price": "6.00", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3310194.jpg", "url": "https://www.coles.com.au/product/ultimate-yoghurt-tropical-mango-4x115g-4-pack-3310194"},
    {"name": "Primo Sliced Turkey Breast | 80g", "price": "3.95", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/2/2814024.jpg", "url": "https://www.coles.com.au/product/primo-sliced-turkey-breast-80g-2814024"},
    {"name": "Ultimate Yoghurt Black Cherry 4x115g | 4 Pack", "price": "6.00", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3310183.jpg", "url": "https://www.coles.com.au/product/ultimate-yoghurt-black-cherry-4x115g-4-pack-3310183"},
    {"name": "Chobani No Sugar Added Yogurt Pouch Strawberry | 100g", "price": "2.00", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/7/7650219.jpg", "url": "https://www.coles.com.au/product/chobani-no-sugar-added-yogurt-pouch-strawberry-100g-7650219"},
    {"name": "Farmers Union No Added Sugar Protein Yoghurt Pouch Strawberry | 150g", "price": "2.90", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/1155545.jpg", "url": "https://www.coles.com.au/product/farmers-union-no-added-sugar-protein-yoghurt-pouch-strawberry-150g-1155545"},
    {"name": "Activia Probiotic Yoghurt No Added Sugar Mango 4x125g | 500g", "price": "6.00", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/8/8872089.jpg", "url": "https://www.coles.com.au/product/activia-probiotic-yoghurt-no-added-sugar-mango-4x125g-500g-8872089"},
    {"name": "Coles Perform Build Chipotle Chicken Burrito Bowl | 400g", "price": "10.00", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5070830.jpg", "url": "https://www.coles.com.au/product/coles-perform-build-chipotle-chicken-burrito-bowl-400g-5070830"},
    {"name": "Black Swan Dip Reduced Fat Roasted Capsicum | 200g", "price": "4.50", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/8/8750208.jpg", "url": "https://www.coles.com.au/product/black-swan-dip-reduced-fat-roasted-capsicum-200g-8750208"},
    {"name": "Farmers Union No Added Sugar Protein Yoghurt Pouch Mango | 150g", "price": "2.90", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/1/1155534.jpg", "url": "https://www.coles.com.au/product/farmers-union-no-added-sugar-protein-yoghurt-pouch-mango-150g-1155534"},
    {"name": "Primo Hot Hungarian Salami | 80g", "price": "3.95", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3576271.jpg", "url": "https://www.coles.com.au/product/primo-hot-hungarian-salami-80g-3576271"},
    {"name": "Primo Roast Beef Thinly Sliced | 80g", "price": "3.95", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/2/2822259.jpg", "url": "https://www.coles.com.au/product/primo-roast-beef-thinly-sliced-80g-2822259"},
    {"name": "Primo Manuka Honey Leg Ham | 100g", "price": "3.95", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/9/9065548.jpg", "url": "https://www.coles.com.au/product/primo-manuka-honey-leg-ham-100g-9065548"},
    {"name": "Provedore Prosciutto | 100g", "price": "7.50", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3269170.jpg", "url": "https://www.coles.com.au/product/provedore-prosciutto-100g-3269170"},
    {"name": "Chobani No Added Sugar Greek Yogurt Blueberry Pouch | 100g", "price": "2.00", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/9/9961366.jpg", "url": "https://www.coles.com.au/product/chobani-no-added-sugar-greek-yogurt-blueberry-pouch-100g-9961366"},
    {"name": "Farmers Union No Added Sugar Kids Yogurt Pouch Strawberry | 130g", "price": "2.50", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/6/6600689.jpg", "url": "https://www.coles.com.au/product/farmers-union-no-added-sugar-kids-yogurt-pouch-strawberry-130g-6600689"},
    {"name": "Big M Banana Flavoured Milk | 600mL", "price": "3.80", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3034279.jpg", "url": "https://www.coles.com.au/product/big-m-banana-flavoured-milk-600ml-3034279"},
    {"name": "Farmers Union Yoghurt Peach | 130g", "price": "2.50", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3830911.jpg", "url": "https://www.coles.com.au/product/farmers-union-yoghurt-peach-130g-3830911"},
    {"name": "Coles Perform Build Chicken Pesto Gnocchi | 430g", "price": "10.00", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5070921.jpg", "url": "https://www.coles.com.au/product/coles-perform-build-chicken-pesto-gnocchi-430g-5070921"},
    {"name": "Yoplait Petit Miam Vanilla Yoghurt Pouch | 70g", "price": "1.20", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/2/2744734.jpg", "url": "https://www.coles.com.au/product/yoplait-petit-miam-vanilla-yoghurt-pouch-70g-2744734"},
    {"name": "Yoplait Petit Miam Squeezie Banana Yoghurt Pouch | 70g", "price": "1.20", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/6/6569240.jpg", "url": "https://www.coles.com.au/product/yoplait-petit-miam-squeezie-banana-yoghurt-pouch-70g-6569240"},
    {"name": "Vaalia Kids Yoghurt Pouch Strawberry | 140g", "price": "2.50", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/7/7246880.jpg", "url": "https://www.coles.com.au/product/vaalia-kids-yoghurt-pouch-strawberry-140g-7246880"},
    {"name": "Activia Probiotics Yoghurt No Added Sugar Berries 4x125g | 500g", "price": "6.00", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/8/8169435.jpg", "url": "https://www.coles.com.au/product/activia-probiotics-yoghurt-no-added-sugar-berries-4x125g-500g-8169435"},
    {"name": "Black Swan Avocado Dip | 200g", "price": "4.50", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/5/5371939.jpg", "url": "https://www.coles.com.au/product/black-swan-avocado-dip-200g-5371939"},
    {"name": "Coles Kitchen Spaghetti Bolognese | 350g", "price": "8.00", "wasPrice": None, "imageUrl": "https://cdn.productimages.coles.com.au/productimages/3/3771266.jpg", "url": "https://www.coles.com.au/product/coles-kitchen-spaghetti-bolognese-350g-3771266"},
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

    print(f'Coles batch 2 (dairy): Saved {saved}, Updated {updated}')


if __name__ == '__main__':
    save_products()
