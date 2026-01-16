"""
Seed Categories Script

Creates the unified category hierarchy based on Woolworths structure.
Run with: python -m scripts.seed_categories
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import sessionmaker
from app.database import engine
from app.models import Category

# Category definitions based on Woolworths structure
# Each store's products will be mapped to these unified categories
CATEGORIES = [
    {"name": "Fruit & Veg", "slug": "fruit-veg", "order": 1, "icon": "apple"},
    {"name": "Poultry, Meat & Seafood", "slug": "meat-seafood", "order": 2, "icon": "drumstick"},
    {"name": "Deli", "slug": "deli", "order": 3, "icon": "bacon"},
    {"name": "Dairy, Eggs & Fridge", "slug": "dairy-eggs-fridge", "order": 4, "icon": "milk"},
    {"name": "Bakery", "slug": "bakery", "order": 5, "icon": "bread-slice"},
    {"name": "Pantry", "slug": "pantry", "order": 6, "icon": "jar"},
    {"name": "Drinks", "slug": "drinks", "order": 7, "icon": "glass-water"},
    {"name": "Freezer", "slug": "freezer", "order": 8, "icon": "snowflake"},
    {"name": "Snacks & Confectionery", "slug": "snacks-confectionery", "order": 9, "icon": "cookie"},
    {"name": "International Foods", "slug": "international", "order": 10, "icon": "globe"},
    {"name": "Beer, Wine & Spirits", "slug": "liquor", "order": 11, "icon": "wine-glass"},
    {"name": "Beauty", "slug": "beauty", "order": 12, "icon": "sparkles"},
    {"name": "Personal Care", "slug": "personal-care", "order": 13, "icon": "hand-sparkles"},
    {"name": "Health & Wellness", "slug": "health", "order": 14, "icon": "heart-pulse"},
    {"name": "Cleaning & Household", "slug": "cleaning-household", "order": 15, "icon": "spray-can"},
    {"name": "Baby", "slug": "baby", "order": 16, "icon": "baby"},
    {"name": "Pet", "slug": "pet", "order": 17, "icon": "paw"},
]

# Subcategories based on Woolworths structure
# Each main category now has comprehensive subcategories
SUBCATEGORIES = {
    "fruit-veg": [
        {"name": "Fresh Fruit", "slug": "fresh-fruit"},
        {"name": "Fresh Vegetables", "slug": "fresh-vegetables"},
        {"name": "Salad", "slug": "salad"},
        {"name": "Prepared Vegetables", "slug": "prepared-vegetables"},
        {"name": "Organic", "slug": "organic-produce"},
        {"name": "Fresh Herbs, Garlic & Chillies", "slug": "herbs-garlic-chillies"},
    ],
    "meat-seafood": [
        {"name": "Beef & Veal", "slug": "beef-veal"},
        {"name": "Chicken", "slug": "chicken"},
        {"name": "Pork", "slug": "pork"},
        {"name": "Lamb", "slug": "lamb"},
        {"name": "Seafood", "slug": "seafood"},
        {"name": "Mince & Burgers", "slug": "mince-burgers"},
        {"name": "Sausages & BBQ", "slug": "sausages-bbq"},
        {"name": "Turkey & Duck", "slug": "turkey-duck"},
    ],
    "deli": [
        {"name": "Cold Cuts & Salami", "slug": "cold-cuts-salami"},
        {"name": "Deli Cheese", "slug": "deli-cheese"},
        {"name": "Olives & Antipasto", "slug": "olives-antipasto"},
        {"name": "Dips & Spreads", "slug": "dips-spreads"},
        {"name": "Cooked Meats", "slug": "cooked-meats"},
    ],
    "dairy-eggs-fridge": [
        {"name": "Milk", "slug": "milk"},
        {"name": "Cheese", "slug": "cheese"},
        {"name": "Yoghurt", "slug": "yoghurt"},
        {"name": "Eggs", "slug": "eggs"},
        {"name": "Butter & Cream", "slug": "butter-cream"},
        {"name": "Cream & Custard", "slug": "cream-custard"},
        {"name": "Chilled Desserts", "slug": "chilled-desserts"},
    ],
    "bakery": [
        {"name": "Bread", "slug": "bread"},
        {"name": "Bread Rolls & Wraps", "slug": "bread-rolls-wraps"},
        {"name": "Cakes & Tarts", "slug": "cakes-tarts"},
        {"name": "Pastries & Croissants", "slug": "pastries-croissants"},
        {"name": "Muffins & Donuts", "slug": "muffins-donuts"},
        {"name": "Gluten Free Bakery", "slug": "gluten-free-bakery"},
    ],
    "pantry": [
        {"name": "Pasta & Noodles", "slug": "pasta-noodles"},
        {"name": "Rice & Grains", "slug": "rice-grains"},
        {"name": "Canned Food", "slug": "canned-food"},
        {"name": "Sauces & Condiments", "slug": "sauces-condiments"},
        {"name": "Cooking Oils", "slug": "cooking-oils"},
        {"name": "Spreads & Honey", "slug": "spreads-honey"},
        {"name": "Breakfast Cereals", "slug": "breakfast-cereals"},
        {"name": "Baking Supplies", "slug": "baking-supplies"},
        {"name": "Herbs & Spices", "slug": "herbs-spices"},
    ],
    "drinks": [
        {"name": "Soft Drinks", "slug": "soft-drinks"},
        {"name": "Water", "slug": "water"},
        {"name": "Juice", "slug": "juice"},
        {"name": "Coffee & Tea", "slug": "coffee-tea"},
        {"name": "Energy Drinks", "slug": "energy-drinks"},
        {"name": "Cordial & Mixers", "slug": "cordial-mixers"},
        {"name": "Sports Drinks", "slug": "sports-drinks"},
    ],
    "freezer": [
        {"name": "Frozen Meals", "slug": "frozen-meals"},
        {"name": "Ice Cream & Frozen Desserts", "slug": "ice-cream-frozen-desserts"},
        {"name": "Frozen Vegetables", "slug": "frozen-vegetables"},
        {"name": "Frozen Chips & Wedges", "slug": "frozen-chips-wedges"},
        {"name": "Frozen Seafood", "slug": "frozen-seafood"},
        {"name": "Frozen Meat & Poultry", "slug": "frozen-meat-poultry"},
        {"name": "Frozen Pizza", "slug": "frozen-pizza"},
        {"name": "Frozen Pastry", "slug": "frozen-pastry"},
    ],
    "snacks-confectionery": [
        {"name": "Chips & Crisps", "slug": "chips-crisps"},
        {"name": "Chocolate", "slug": "chocolate"},
        {"name": "Lollies", "slug": "lollies"},
        {"name": "Biscuits", "slug": "biscuits"},
        {"name": "Nuts & Snacks", "slug": "nuts-snacks"},
        {"name": "Popcorn & Pretzels", "slug": "popcorn-pretzels"},
        {"name": "Muesli & Snack Bars", "slug": "muesli-snack-bars"},
    ],
    "international": [
        {"name": "Asian", "slug": "asian-foods"},
        {"name": "Mexican", "slug": "mexican-foods"},
        {"name": "Indian", "slug": "indian-foods"},
        {"name": "Italian", "slug": "italian-foods"},
        {"name": "Middle Eastern", "slug": "middle-eastern-foods"},
        {"name": "European", "slug": "european-foods"},
    ],
    "liquor": [
        {"name": "Beer", "slug": "beer"},
        {"name": "Wine", "slug": "wine"},
        {"name": "Spirits", "slug": "spirits"},
        {"name": "Cider", "slug": "cider"},
        {"name": "Ready to Drink", "slug": "ready-to-drink"},
        {"name": "Non-Alcoholic", "slug": "non-alcoholic-drinks"},
    ],
    "beauty": [
        {"name": "Skincare", "slug": "skincare"},
        {"name": "Makeup & Cosmetics", "slug": "makeup-cosmetics"},
        {"name": "Suncare", "slug": "suncare"},
        {"name": "Fragrance", "slug": "fragrance"},
        {"name": "Nails", "slug": "nails"},
    ],
    "personal-care": [
        {"name": "Hair Care", "slug": "hair-care"},
        {"name": "Body Wash & Soap", "slug": "body-wash-soap"},
        {"name": "Deodorant", "slug": "deodorant"},
        {"name": "Oral Care", "slug": "oral-care"},
        {"name": "Shaving & Hair Removal", "slug": "shaving-hair-removal"},
        {"name": "Feminine Care", "slug": "feminine-care"},
    ],
    "health": [
        {"name": "Vitamins & Supplements", "slug": "vitamins-supplements"},
        {"name": "Pain Relief", "slug": "pain-relief"},
        {"name": "Cold & Flu", "slug": "cold-flu"},
        {"name": "First Aid", "slug": "first-aid"},
        {"name": "Digestive Health", "slug": "digestive-health"},
    ],
    "cleaning-household": [
        {"name": "Laundry", "slug": "laundry"},
        {"name": "Cleaning Products", "slug": "cleaning-products"},
        {"name": "Dishwashing", "slug": "dishwashing"},
        {"name": "Paper Products", "slug": "paper-products"},
        {"name": "Air Fresheners", "slug": "air-fresheners"},
        {"name": "Pest Control", "slug": "pest-control"},
        {"name": "Batteries & Electricals", "slug": "batteries-electricals"},
    ],
    "baby": [
        {"name": "Nappies & Wipes", "slug": "nappies-wipes"},
        {"name": "Baby Food", "slug": "baby-food"},
        {"name": "Baby Formula", "slug": "baby-formula"},
        {"name": "Baby Care", "slug": "baby-care"},
        {"name": "Baby Accessories", "slug": "baby-accessories"},
    ],
    "pet": [
        {"name": "Dog Food", "slug": "dog-food"},
        {"name": "Cat Food", "slug": "cat-food"},
        {"name": "Pet Treats", "slug": "pet-treats"},
        {"name": "Pet Care", "slug": "pet-care"},
        {"name": "Pet Accessories", "slug": "pet-accessories"},
    ],
}


def seed_categories():
    """Seed the categories table with the unified category structure."""
    print("Seeding categories...")

    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        created = 0
        updated = 0

        # Create main categories
        for cat_data in CATEGORIES:
            existing = db.query(Category).filter(Category.slug == cat_data["slug"]).first()

            if existing:
                # Update existing category
                existing.name = cat_data["name"]
                existing.display_order = cat_data["order"]
                existing.icon = cat_data.get("icon")
                updated += 1
                print(f"  Updated: {cat_data['name']}")
            else:
                # Create new category
                category = Category(
                    name=cat_data["name"],
                    slug=cat_data["slug"],
                    display_order=cat_data["order"],
                    icon=cat_data.get("icon"),
                    parent_id=None
                )
                db.add(category)
                created += 1
                print(f"  Created: {cat_data['name']}")

        db.commit()

        # Create subcategories
        for parent_slug, subcats in SUBCATEGORIES.items():
            parent = db.query(Category).filter(Category.slug == parent_slug).first()
            if not parent:
                print(f"  Warning: Parent category {parent_slug} not found")
                continue

            for i, subcat_data in enumerate(subcats):
                existing = db.query(Category).filter(Category.slug == subcat_data["slug"]).first()

                if existing:
                    existing.parent_id = parent.id
                    existing.display_order = i + 1
                    updated += 1
                else:
                    subcategory = Category(
                        name=subcat_data["name"],
                        slug=subcat_data["slug"],
                        parent_id=parent.id,
                        display_order=i + 1
                    )
                    db.add(subcategory)
                    created += 1
                    print(f"    Created: {subcat_data['name']} (under {parent.name})")

        db.commit()

        print(f"\nDone! Created {created}, Updated {updated} categories")

        # Print summary
        total = db.query(Category).count()
        main_cats = db.query(Category).filter(Category.parent_id.is_(None)).count()
        sub_cats = db.query(Category).filter(Category.parent_id.isnot(None)).count()

        print(f"\nSummary:")
        print(f"  Total categories: {total}")
        print(f"  Main categories: {main_cats}")
        print(f"  Subcategories: {sub_cats}")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_categories()
