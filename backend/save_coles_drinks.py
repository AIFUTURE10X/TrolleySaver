"""Save Coles specials to database."""
import sys
sys.path.insert(0, '.')

from decimal import Decimal
from datetime import date, timedelta
from app.database import SessionLocal
from app.models import Store, Category, Special
import re

# ALDI Special Buys - Saturday 17th Jan 2026
ALDI_PRODUCTS = [
    # Page 1
    {'name': 'CRANE Soft Ball Set', 'price': '12.99', 'wasPrice': None},
    {'name': 'KIRKTON HOUSE Bath Pillow', 'price': '19.99', 'wasPrice': None},
    {'name': 'CRANE Water Slide', 'price': '29.99', 'wasPrice': None},
    {'name': 'KIRKTON HOUSE Spa Wrap Towel and Headband Set', 'price': '19.99', 'wasPrice': None},
    {'name': 'FINDON Sprinkler Toy', 'price': '9.99', 'wasPrice': None},
    {'name': 'KIRKTON HOUSE Hair Wrap', 'price': '4.99', 'wasPrice': None},
    {'name': 'SANDY CAPE Childrens Zip Up Hooded Towel', 'price': '24.99', 'wasPrice': None},
    {'name': 'EASY HOME Tissue Box Holder or Accessory Tray', 'price': '19.99', 'wasPrice': None},
    {'name': 'HOME CREATION Folding Step Stool', 'price': '5.99', 'wasPrice': None},
    {'name': 'COCONUT GROVE Wooden Lawn Games', 'price': '19.99', 'wasPrice': None},
    {'name': 'KIRKTON HOUSE Memory Foam Bath Mat', 'price': '11.99', 'wasPrice': None},
    {'name': 'KIRKTON HOUSE Towel Set', 'price': '29.99', 'wasPrice': None},
    {'name': "HAVAIANAS Women's Thongs", 'price': '11.99', 'wasPrice': None},
    {'name': "HAVAIANAS Men's Thongs", 'price': '11.99', 'wasPrice': None},
    {'name': 'EASY HOME Apothecary Glass Jar Set', 'price': '11.99', 'wasPrice': None},
    {'name': "SERRA Women's Denim Shorts", 'price': '14.99', 'wasPrice': None},
    {'name': "SERRA Women's Relaxed Pants", 'price': '19.99', 'wasPrice': None},
    {'name': "SERRA Women's Summer Dress", 'price': '19.99', 'wasPrice': None},
    {'name': "SERRA Women's Leather Double Strap Sandals", 'price': '14.99', 'wasPrice': None},
    {'name': "SERRA Women's Leather Sandals", 'price': '14.99', 'wasPrice': None},
    {'name': 'CRANE Snorkel and Diving Set', 'price': '9.99', 'wasPrice': None},
    {'name': 'EASY HOME Magnetic Storage Assortment', 'price': '5.99', 'wasPrice': None},
    {'name': 'COCONUT GROVE Giant Inflatable Sprinkler', 'price': '24.99', 'wasPrice': None},
    {'name': 'SERRA Shelf Bra Tank 2 Pack', 'price': '19.99', 'wasPrice': None},
    {'name': 'BESTWAY Lounger and Tube Assortment', 'price': '9.99', 'wasPrice': None},
    {'name': 'EASY HOME Make Up Storage', 'price': '19.99', 'wasPrice': None},
    {'name': 'EASY HOME Stackable Storage Box with Handle', 'price': '9.99', 'wasPrice': None},
    {'name': 'LS LIVE IN STYLE Pull Along Picnic Cooler', 'price': '29.99', 'wasPrice': None},
    # Page 2
    {'name': 'EASY HOME Folding Boxes', 'price': '3.99', 'wasPrice': None},
    {'name': "SERRA Women's Robe", 'price': '19.99', 'wasPrice': None},
    {'name': 'EASY HOME Collapsible Wardrobe Organisers', 'price': '8.99', 'wasPrice': None},
    {'name': 'EASY HOME Dry Stone Bath Mat', 'price': '13.99', 'wasPrice': None},
    {'name': "SERRA Women's Leather Handbags", 'price': '34.99', 'wasPrice': None},
    {'name': 'CRANE Towable Board', 'price': '19.99', 'wasPrice': None},
    {'name': 'EASY HOME Drawer Organisers 6 Pack', 'price': '9.99', 'wasPrice': None},
    {'name': 'ADVENTURIDGE Compact Picnic Mat', 'price': '9.99', 'wasPrice': None},
    {'name': 'EASY HOME Ribbed Bathroom Accessories', 'price': '5.99', 'wasPrice': None},
    {'name': 'EASY HOME 3 Tier Ribbed Tower Stand', 'price': '19.99', 'wasPrice': None},
    {'name': 'EASY HOME Ribbed Toilet Roll Holder, Bin or Brush', 'price': '14.99', 'wasPrice': None},
]


def clean_product_name(name):
    """Clean up product name."""
    # Remove special prefixes
    name = re.sub(r'^(1/2 PRICE|SPECIAL|Sponsored)\s*', '', name, flags=re.IGNORECASE)
    # Remove duplicated parts (name appears twice)
    parts = name.split('|')
    if len(parts) >= 2:
        # Take the first part with size info
        name = parts[0].strip() + ' | ' + parts[1].strip().split('$')[0].strip()
    # Remove trailing price info
    name = re.sub(r'\$[\d.]+.*$', '', name)
    # Remove trailing non-product text
    name = re.sub(r'(Save|Was|out of|stars|reviews|options|Add).*$', '', name, flags=re.IGNORECASE)
    return name.strip()


def save_products(products, category_slug):
    """Save products to database."""
    db = SessionLocal()

    store = db.query(Store).filter(Store.slug == 'coles').first()
    if not store:
        print('ERROR: Coles store not found')
        return

    category = db.query(Category).filter(Category.slug == category_slug).first()
    category_id = category.id if category else None

    valid_from = date.today()
    valid_to = valid_from + timedelta(days=7)

    saved = 0
    updated = 0

    for p in products:
        try:
            name = clean_product_name(p['name'])
            if len(name) < 5:
                continue

            existing = db.query(Special).filter(
                Special.store_id == store.id,
                Special.name == name
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
                existing.valid_from = valid_from
                existing.valid_to = valid_to
                updated += 1
            else:
                special = Special(
                    store_id=store.id,
                    category_id=category_id,
                    name=name,
                    price=price,
                    was_price=was_price,
                    discount_percent=discount_percent,
                    valid_from=valid_from,
                    valid_to=valid_to
                )
                db.add(special)
                saved += 1
        except Exception as e:
            print(f'Error saving {p["name"]}: {e}')

    db.commit()
    db.close()

    print(f'Coles {category_slug}: Saved {saved}, Updated {updated}')
    return {'saved': saved, 'updated': updated}


def save_aldi_products(products):
    """Save ALDI products to database."""
    db = SessionLocal()

    store = db.query(Store).filter(Store.slug == 'aldi').first()
    if not store:
        print('ERROR: ALDI store not found')
        return

    valid_from = date.today()
    valid_to = valid_from + timedelta(days=7)

    saved = 0
    updated = 0

    for p in products:
        try:
            name = p['name']
            if len(name) < 5:
                continue

            existing = db.query(Special).filter(
                Special.store_id == store.id,
                Special.name == name
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
                existing.valid_from = valid_from
                existing.valid_to = valid_to
                updated += 1
            else:
                special = Special(
                    store_id=store.id,
                    name=name,
                    price=price,
                    was_price=was_price,
                    discount_percent=discount_percent,
                    valid_from=valid_from,
                    valid_to=valid_to
                )
                db.add(special)
                saved += 1
        except Exception as e:
            print(f'Error saving {p["name"]}: {e}')

    db.commit()
    db.close()

    print(f'ALDI Special Buys: Saved {saved}, Updated {updated}')
    return {'saved': saved, 'updated': updated}


# IGA Weekly Specials - Valid Wed 14 Jan – Tue 20 Jan 2026
IGA_PRODUCTS = [
    # Page 1
    {'name': 'Coca-Cola 10x375mL Selected Varieties', 'price': '10.00', 'wasPrice': '22.00'},
    {'name': 'V Energy Drink 4x500mL Selected Varieties', 'price': '8.35', 'wasPrice': '18.45'},
    {'name': 'Rexona Advanced Protection Antiperspirant Spray 220mL Selected Varieties', 'price': '4.25', 'wasPrice': '11.55'},
    {'name': 'Sanitarium Weet-Bix 575g', 'price': '2.50', 'wasPrice': '5.00'},
    {'name': 'Morning Fresh Dishwashing Liquid 900mL Selected Varieties', 'price': '5.50', 'wasPrice': '11.00'},
    {'name': 'Connoisseur Gourmet Ice Cream 1 Litre Selected Varieties', 'price': '6.60', 'wasPrice': '13.20'},
    {'name': "French Fries Original or Smith's Thinly Cut Chips 175g Selected Varieties", 'price': '2.50', 'wasPrice': '5.50'},
    {'name': 'Bega Cheese Block, Grated or Slices 500g Selected Varieties', 'price': '9.50', 'wasPrice': '11.55'},
    {'name': 'Whiskas Wet Cat Food 400g Selected Varieties', 'price': '1.85', 'wasPrice': '2.95'},
    {'name': 'Continental Flavoured Rice 115-125g Selected Varieties', 'price': '1.75', 'wasPrice': '3.50'},
    {'name': 'Schweppes Mixers, Soft Drinks or Natural Mineral Water 1.1 Litre Selected Varieties', 'price': '1.65', 'wasPrice': '3.30'},
    {'name': 'Mars Fun Size Share Pack 132-192g Selected Varieties', 'price': '5.35', 'wasPrice': None},
    {'name': 'Sanitarium Weet-Bix Bites 500-510g Selected Varieties', 'price': '3.55', 'wasPrice': None},
    {'name': "Four'N Twenty Meat Pies 4 Pack Selected Varieties", 'price': '8.20', 'wasPrice': None},
    {'name': 'McCain Pub Style Wedges 750g', 'price': '4.60', 'wasPrice': '6.60'},
    {'name': 'Sorbent Silky White Facial Tissues 250 Pack', 'price': '2.40', 'wasPrice': '3.40'},
    # Page 2
    {'name': 'Pedigree Dry Dog Food 2.5-3kg Selected Varieties', 'price': '12.00', 'wasPrice': None},
    {'name': 'Optimum Dry Dog Food 2.5-3kg Selected Varieties', 'price': '18.40', 'wasPrice': '25.30'},
    {'name': "Smith's Crackers 160g Selected Varieties", 'price': '2.75', 'wasPrice': '4.40'},
    {'name': 'Australian Mangoes', 'price': '2.90', 'wasPrice': None},
    {'name': 'Australian White or Yellow Peaches', 'price': '3.90', 'wasPrice': None},
    {'name': 'Australian Green Oak Lettuce', 'price': '2.50', 'wasPrice': None},
    {'name': 'Community Co Baby Spinach & Rocket 100g', 'price': '2.40', 'wasPrice': '2.95'},
    {'name': 'Lemnos Fetta Cheese 180-200g Selected Varieties', 'price': '5.75', 'wasPrice': '7.50'},
    {'name': 'Lurpak Spreadable 250g Selected Varieties', 'price': '6.35', 'wasPrice': None},
    {'name': 'Golden Crumpet Rounds 6 Pack Selected Varieties', 'price': '2.40', 'wasPrice': None},
    {'name': 'Bakers Oven Lamingtons 350g Selected Varieties', 'price': '4.20', 'wasPrice': None},
    {'name': 'Wonder White or Wholemeal Bread 680-700g Selected Varieties', 'price': '4.70', 'wasPrice': None},
    {'name': "Abbott's Bakery Bread 680-800g Selected Varieties", 'price': '5.50', 'wasPrice': None},
    {'name': 'Nestle Medium Bars 35-50g or Darrell Lea Choc Logs 3 Pack Selected Varieties', 'price': '1.65', 'wasPrice': '3.30'},
    {'name': "Mars Medium Bars 42-56g or M&M's 35-49g Selected Varieties", 'price': '1.35', 'wasPrice': '2.75'},
    {'name': "Arnott's Cream Biscuits 200-250g, Salada Crackers 250g or Smith's Crinkle Cut Chips 150-170g Selected Varieties", 'price': '3.30', 'wasPrice': '4.40'},
    # Page 3
    {'name': 'Cadbury Chocolate Blocks 150-190g Selected Varieties', 'price': '6.05', 'wasPrice': None},
    {'name': 'Coca-Cola, Sprite or Fanta 1.25 Litre Selected Varieties', 'price': '2.20', 'wasPrice': None},
    {'name': "Arnott's Chocolate Biscuits 160-250g Selected Varieties", 'price': '3.60', 'wasPrice': None},
    {'name': "Allen's Medium Bag 140-200g Selected Varieties", 'price': '3.85', 'wasPrice': '5.50'},
    {'name': 'Red Bull Energy Drink 4x250mL Selected Varieties', 'price': '9.60', 'wasPrice': None},
    {'name': 'Kettle Potato Chips 135-165g Selected Varieties', 'price': '4.95', 'wasPrice': None},
    {'name': 'Pepsi 24x375mL Selected Varieties', 'price': '24.75', 'wasPrice': '41.25'},
    {'name': 'Powerade 600mL Selected Varieties', 'price': '2.85', 'wasPrice': '4.85'},
    {'name': 'Mount Franklin Lightly Sparkling Water 1.25 Litre Selected Varieties', 'price': '2.15', 'wasPrice': '3.60'},
    {'name': "Smith's Crinkle Cut Chips 45g Selected Varieties", 'price': '1.65', 'wasPrice': '2.15'},
    {'name': 'Pascall Chocolate Share Bag 160-185g Selected Varieties', 'price': '5.35', 'wasPrice': '7.70'},
    # Page 4
    {'name': 'Golden Circle Fruit Drink 1 Litre Selected Varieties', 'price': '1.65', 'wasPrice': '3.30'},
    {'name': 'Uncle Tobys Muesli Bars 5-6 Pack or Le Snak 6 Pack Selected Varieties', 'price': '3.00', 'wasPrice': None},
    {'name': 'V8 Fruit & Vegetable Juice 1.25 Litre Selected Varieties', 'price': '3.60', 'wasPrice': '6.05'},
    {'name': "Kellogg's Corn Flakes 380g or Rice Bubbles 250g", 'price': '4.40', 'wasPrice': None},
    {'name': 'Mission Naan Bread 4-6 Pack Selected Varieties', 'price': '3.50', 'wasPrice': '4.50'},
    {'name': 'San Remo Pasta 375-500g Selected Varieties', 'price': '2.50', 'wasPrice': None},
    {'name': 'SunRice Microwave Rice Cup 2 Pack Selected Varieties', 'price': '2.30', 'wasPrice': '3.85'},
    {'name': 'Pepsi or Sunkist 1.25 Litre Selected Varieties', 'price': '1.75', 'wasPrice': '3.85'},
    {'name': 'Peters Maxibon 4 Pack Selected Varieties', 'price': '5.75', 'wasPrice': '12.65'},
    {'name': 'John West Tuna 95g Selected Varieties', 'price': '1.45', 'wasPrice': '2.90'},
    {'name': 'SPC Crushed or Diced Tomatoes 400-410g Selected Varieties', 'price': '1.00', 'wasPrice': '1.85'},
    {'name': 'McCain Family Pizza 490-500g Selected Varieties', 'price': '6.00', 'wasPrice': None},
    {'name': 'Australian Blueberries 125g Punnet', 'price': '3.00', 'wasPrice': None},
    {'name': 'Jon Jon Ginger Kisses 200g', 'price': '4.50', 'wasPrice': None},
    # Page 5
    {'name': 'MasterFoods Mustard 170-175g Selected Varieties', 'price': '3.00', 'wasPrice': None},
    {'name': 'MasterFoods Tomato or Barbecue Sauce 475-500mL Selected Varieties', 'price': '2.75', 'wasPrice': None},
    {'name': 'Doritos Corn Chips 150-170g Selected Varieties', 'price': '4.10', 'wasPrice': None},
    {'name': 'MasterFoods Marinade 375g Selected Varieties', 'price': '3.30', 'wasPrice': None},
    {'name': 'Streets Paddle Pop 8 Pack Selected Varieties', 'price': '5.90', 'wasPrice': '9.90'},
    {'name': "Nanna's Fruit Crumble 550g Selected Varieties", 'price': '4.25', 'wasPrice': None},
    {'name': 'Peters Icy Pole 8 Pack Selected Varieties', 'price': '4.40', 'wasPrice': '5.50'},
    {'name': 'Pauls Vanilla Custard 600g Selected Varieties', 'price': '3.50', 'wasPrice': '4.60'},
    {'name': 'Birds Eye Snap Frozen Mixed Vegetables 500g Selected Varieties', 'price': '3.05', 'wasPrice': '4.40'},
    {'name': 'Birds Eye Frozen Chopped Onions 500g', 'price': '2.60', 'wasPrice': '4.00'},
    {'name': 'Two Boys Brew Energy Tea 330mL Selected Varieties', 'price': '4.10', 'wasPrice': None},
    {'name': 'Bega Cheese Stringers 8 Pack Selected Varieties', 'price': '6.15', 'wasPrice': '7.70'},
    {'name': 'Fluffy Concentrated Fabric Conditioner 900mL-1 Litre Selected Varieties', 'price': '4.75', 'wasPrice': '10.45'},
    {'name': 'Vaseline Intensive Care Body Lotion 225mL Selected Varieties', 'price': '3.85', 'wasPrice': '7.70'},
    {'name': 'Nurofen Zavance Mini Ibuprofen 200mg Liquid Capsules 8 Pack', 'price': '5.15', 'wasPrice': '5.80'},
    {'name': 'OC Naturals Shampoo or Conditioner 400mL Selected Varieties', 'price': '3.15', 'wasPrice': None},
    {'name': 'Murine Relief Eye Drops 15mL', 'price': '8.35', 'wasPrice': None},
    {'name': 'Jiffy Firelighters 24 Pack', 'price': '4.35', 'wasPrice': '6.60'},
    {'name': 'Dine Wet Cat Food 85g Selected Varieties', 'price': '1.40', 'wasPrice': '1.75'},
    {'name': 'Kleenex Facial Tissues 140 Pack Selected Varieties', 'price': '3.95', 'wasPrice': '4.95'},
    {'name': 'Glad Snap Lock Storage 10-15 Pack or Sandwich 30 Pack Resealable Bags Selected Varieties', 'price': '2.75', 'wasPrice': '3.80'},
    {'name': 'Earth Choice Ultra Concentrate Dishwashing Liquid 500mL Selected Varieties', 'price': '2.75', 'wasPrice': '3.85'},
    # Liquor Page
    {'name': 'Tooheys Extra Dry 24 Pack', 'price': '49.00', 'wasPrice': None},
    {'name': 'Great Northern Super Crisp 24 Pack', 'price': '53.00', 'wasPrice': None},
    {'name': 'Tooheys New 24 Pack', 'price': '54.00', 'wasPrice': None},
    {'name': 'Hahn SuperDry 3.5 30 Can Block', 'price': '60.00', 'wasPrice': None},
    {'name': 'Carlton Dry 3.5% 30 Can Block', 'price': '62.00', 'wasPrice': None},
    {'name': 'Woodstock & Cola 4.8% 6 Pack', 'price': '26.00', 'wasPrice': None},
    {'name': 'Hard Rated Lemon 6% 10 Pack', 'price': '45.00', 'wasPrice': None},
    {'name': 'Smirnoff ICE Double Black 6.5% 10 Pack', 'price': '54.00', 'wasPrice': None},
    {'name': "Jack Daniel's & Cola 4.8% Cube 24 Pack", 'price': '95.00', 'wasPrice': None},
    {'name': 'Ampersand Vodka & 500mL', 'price': '36.00', 'wasPrice': None},
    {'name': 'Skrewball Peanut Butter Whiskey 750mL', 'price': '53.00', 'wasPrice': None},
    {'name': 'Canadian Club Whisky or Jim Beam White Label Bourbon 1 Litre', 'price': '70.00', 'wasPrice': None},
    {'name': 'Grant Burge GB Series 750mL Varieties', 'price': '10.00', 'wasPrice': None},
    {'name': 'Ta_Ku 750mL Varieties', 'price': '15.00', 'wasPrice': None},
    {'name': 'Pepperjack 750mL Varieties', 'price': '20.00', 'wasPrice': None},
    {'name': 'Ninth Island Cuvee 750mL', 'price': '22.00', 'wasPrice': None},
]


def save_iga_products(products):
    """Save IGA products to database."""
    db = SessionLocal()

    store = db.query(Store).filter(Store.slug == 'iga').first()
    if not store:
        print('ERROR: IGA store not found')
        return

    valid_from = date.today()
    valid_to = valid_from + timedelta(days=7)

    saved = 0
    updated = 0

    for p in products:
        try:
            name = p['name']
            if len(name) < 5:
                continue

            existing = db.query(Special).filter(
                Special.store_id == store.id,
                Special.name == name
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
                existing.valid_from = valid_from
                existing.valid_to = valid_to
                updated += 1
            else:
                special = Special(
                    store_id=store.id,
                    name=name,
                    price=price,
                    was_price=was_price,
                    discount_percent=discount_percent,
                    valid_from=valid_from,
                    valid_to=valid_to
                )
                db.add(special)
                saved += 1
        except Exception as e:
            print(f'Error saving {p["name"]}: {e}')

    db.commit()
    db.close()

    print(f'IGA Weekly Specials: Saved {saved}, Updated {updated}')
    return {'saved': saved, 'updated': updated}


if __name__ == '__main__':
    print('Saving IGA Weekly Specials...')
    save_iga_products(IGA_PRODUCTS)
