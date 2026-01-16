"""Fix ALDI Special Buys product images."""
import sys
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models import Store, Special

# Scraped from ALDI Special Buys website
ALDI_SPECIAL_BUYS = [
    {"fullName": "CRANE Soft Ball Set", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/57ce8a38-1880-470d-a800-6d7a2db45db4/Soft%20Ball%20Set"},
    {"fullName": "KIRKTON HOUSE Bath Pillow", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/5bd832f7-f7eb-4054-ab20-d39b503995ea/Bath%20Pillow"},
    {"fullName": "CRANE Water Slide", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/b80632e8-08f5-429a-ade9-f85a3b14e4bd/Water%20Slide"},
    {"fullName": "KIRKTON HOUSE Spa Wrap Towel and Headband Set", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/ab340a6a-708c-4adc-8360-5eb9075304d4/Spa%20Wrap%20Towel%20and%20Headband%20Set"},
    {"fullName": "FINDON Sprinkler Toy", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/f0fe9576-904c-4e9c-be1c-692087e03b3e/Sprinkler%20Toy"},
    {"fullName": "KIRKTON HOUSE Hair Wrap", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/92213261-c920-4be8-bc5f-3ec0ef4ab07a/Hair%20Wrap"},
    {"fullName": "SANDY CAPE Childrens Zip Up Hooded Towel", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/a09fe016-5365-408a-a1ce-d2289c4e053f/Childrens%20Zip%20Up%20Hooded%20Towel"},
    {"fullName": "EASY HOME Tissue Box Holder or Accessory Tray", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/a52085cc-f337-4c9f-9afb-e1a948719262/Tissue%20Box%20Holder%20or%20Accessory%20Tray"},
    {"fullName": "HOME CREATION Folding Step Stool", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/3823da77-607e-46f0-a4b5-82c45e1a4bef/Folding%20Step%20Stool"},
    {"fullName": "COCONUT GROVE Wooden Lawn Games", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/5bccf608-0332-4c16-940a-30132856961d/Wooden%20Lawn%20Games"},
    {"fullName": "KIRKTON HOUSE Memory Foam Bath Mat", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/9eb14e64-6b87-48a4-91e3-16edfcc222fc/Memory%20Foam%20Bath%20Mat"},
    {"fullName": "KIRKTON HOUSE Towel Set", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/f6f16971-4cbb-4395-9b38-15c8836173b2/Towel%20Set"},
    {"fullName": "HAVAIANAS Women's Thongs", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/b7711cc0-8e1f-4838-8a53-2403d25bebb5/Womens%20Thongs"},
    {"fullName": "HAVAIANAS Men's Thongs", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/8d5ef9b3-3723-4b3a-bad4-357135e29361/Mens%20Thongs"},
    {"fullName": "EASY HOME Apothecary Glass Jar Set", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/8f38c950-a69b-4e29-ae73-3bfb01b26c3c/Apothecary%20Glass%20Jar%20Set"},
    {"fullName": "SERRA Women's Denim Shorts", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/7a8a6a3c-51bc-4846-a374-eee8769d72a2/Womens%20Denim%20Shorts"},
    {"fullName": "SERRA Women's Relaxed Pants", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/002b2aff-96d5-4a1f-ae98-126f4d839e55/Womens%20Relaxed%20Pants"},
    {"fullName": "SERRA Women's Summer Dress", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/f3fed0d7-e995-4c94-bff5-acc5a3a7ff4d/Womens%20Summer%20Dress"},
    {"fullName": "SERRA Women's Leather Double Strap Sandals", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/112d437f-2b26-49f8-bf43-cf8ff8a083b1/Womens%20Leather%20Double%20Strap%20Sandals"},
    {"fullName": "SERRA Women's Leather Sandals", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/c214b16a-06b2-49b1-a590-ebb83ce86c24/Womens%20Leather%20Sandals"},
    {"fullName": "CRANE Snorkel and Diving Set", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/da09c881-ecaf-4da5-98fb-0fdd830e0d91/Snorkel%20and%20Diving%20Set"},
    {"fullName": "EASY HOME Magnetic Storage Assortment", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/722e044a-4bde-4fcb-a742-02a58a99bb70/Magnetic%20Storage%20Assortment"},
    {"fullName": "COCONUT GROVE Giant Inflatable Sprinkler", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/ac1bb579-f60a-48d0-a774-dc4e73657e45/Giant%20Inflatable%20Sprinkler"},
    {"fullName": "SERRA Shelf Bra Tank 2 Pack", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/76e1df68-5496-4ef2-ae38-55c226f57141/Shelf%20Bra%20Tank%202%20Pack"},
    {"fullName": "BESTWAY Lounger and Tube Assortment", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/b08b2481-f0aa-473e-be30-9de41bd49dd3/Lounger%20and%20Tube%20Assortment"},
    {"fullName": "EASY HOME Make Up Storage", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/effe8496-7031-48c9-80eb-4e4fd08a071d/Make%20Up%20Storage"},
    {"fullName": "EASY HOME Stackable Storage Box with Handle", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/c1b99e99-b888-45b2-9119-e59620162d1e/Stackable%20Storage%20Box%20with%20Handle"},
    {"fullName": "LS LIVE IN STYLE Pull Along Picnic Cooler", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/243870bf-cf4d-479b-a4e9-3cf3d553c0f7/Pull%20Along%20Picnic%20Cooler"},
    {"fullName": "EASY HOME Folding Boxes", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/e6926b02-1033-45b7-b410-ba4841a2178c/Folding%20Boxes"},
    {"fullName": "SERRA Women's Robe", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/7b7fc80a-81e9-4957-b202-35e40f272a78/Womens%20Robe"},
    {"fullName": "EASY HOME Collapsible Wardrobe Organisers", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/4991084d-a884-4940-9a57-4db0ba96c9b8/Collapsible%20Wardrobe%20Organisers"},
    {"fullName": "EASY HOME Dry Stone Bath Mat", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/000b1efc-00d7-4bab-904b-b5aa14bfdb4d/Dry%20Stone%20Bath%20Mat"},
    {"fullName": "SERRA Women's Leather Handbags", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/8f2a4abe-5e21-44c8-be3e-d37cda7b0ddc/Womens%20Leather%20Handbags"},
    {"fullName": "CRANE Towable Board", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/711ad507-545c-429e-9013-149087f147c3/Towable%20Board"},
    {"fullName": "EASY HOME Drawer Organisers 6 Pack", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/7f592877-c6ba-455d-a4c7-d719e40cef71/Drawer%20Organisers%206%20Pack"},
    {"fullName": "ADVENTURIDGE Compact Picnic Mat", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/868f337c-0cb6-4b07-bd60-f3001ea6d19b/Compact%20Picnic%20Mat"},
    {"fullName": "EASY HOME Ribbed Bathroom Accessories", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/c3e7a91e-9a94-42dc-a822-8084c7079b2b/Ribbed%20Bathroom%20Accessories"},
    {"fullName": "EASY HOME 3 Tier Ribbed Tower Stand", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/e6924541-e454-4017-ad00-1f4a14254188/3%20Tier%20Ribbed%20Tower%20Stand"},
    {"fullName": "EASY HOME Ribbed Toilet Roll Holder, Bin or Brush", "imageUrl": "https://dm.apac.cms.aldi.cx/is/image/aldiprodapac/product/jpg/scaleWidth/232/218aea35-730b-42a1-880f-b1a90f9dab75/Ribbed%20Toilet%20Roll%20Holder%20Bin%20or%20Brush"},
]


def normalize_name(name):
    """Normalize product name for matching."""
    return name.lower().strip()


def fix_aldi_special_buys():
    """Update ALDI Special Buys products with image URLs."""
    db = SessionLocal()

    store = db.query(Store).filter(Store.slug == 'aldi').first()
    if not store:
        print('ERROR: ALDI store not found')
        return

    # Create lookup dict by normalized name
    image_lookup = {}
    for item in ALDI_SPECIAL_BUYS:
        key = normalize_name(item['fullName'])
        image_lookup[key] = item['imageUrl']

    print(f'Loaded {len(ALDI_SPECIAL_BUYS)} products from Special Buys scrape')

    # Get ALDI products without images
    products = db.query(Special).filter(
        Special.store_id == store.id,
        (Special.image_url == None) | (Special.image_url == '')
    ).all()
    print(f'Found {len(products)} ALDI products without images')

    updated = 0
    not_found = []

    for p in products:
        product_key = normalize_name(p.name)

        # Try exact match first
        if product_key in image_lookup:
            p.image_url = image_lookup[product_key]
            updated += 1
            continue

        # Try partial match
        found = False
        for name_key, image_url in image_lookup.items():
            if name_key in product_key or product_key in name_key:
                p.image_url = image_url
                updated += 1
                found = True
                break

        if not found:
            not_found.append(p.name)

    db.commit()
    db.close()

    print(f'Updated {updated} ALDI products with images')
    if not_found:
        print(f'Could not find images for {len(not_found)} products:')
        for name in not_found:
            print(f'  - {name}')


if __name__ == '__main__':
    fix_aldi_special_buys()
