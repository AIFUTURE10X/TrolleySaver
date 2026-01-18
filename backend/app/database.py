from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

settings = get_settings()

# SQLite needs different config than PostgreSQL
if settings.database_url.startswith("sqlite"):
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False}  # Needed for SQLite
    )
else:
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables and seed default data."""
    Base.metadata.create_all(bind=engine)

    # Seed default stores if none exist
    from app.models import Store, Category
    db = SessionLocal()
    try:
        if db.query(Store).count() == 0:
            print("Seeding default stores...")
            default_stores = [
                Store(name="Woolworths", slug="woolworths", logo_url="https://www.woolworths.com.au/static/wowlogo/logo.svg", website_url="https://www.woolworths.com.au", specials_day="wednesday"),
                Store(name="Coles", slug="coles", logo_url="https://www.coles.com.au/content/dam/coles/coles-logo.svg", website_url="https://www.coles.com.au", specials_day="wednesday"),
                Store(name="ALDI", slug="aldi", logo_url="https://www.aldi.com.au/static/aldi/logo.svg", website_url="https://www.aldi.com.au", specials_day="wednesday"),
                Store(name="IGA", slug="iga", logo_url="https://www.iga.com.au/sites/default/files/IGA_Logo.png", website_url="https://www.iga.com.au", specials_day="wednesday"),
            ]
            for store in default_stores:
                db.add(store)
            db.commit()
            print(f"Seeded {len(default_stores)} stores")

        # Seed default categories if none exist
        if db.query(Category).count() == 0:
            print("Seeding default categories...")
            default_categories = [
                # Parent categories (using IDs 1-17 for main categories)
                Category(id=1, name="Fruit & Veg", slug="fruit-veg", icon="🥬", display_order=1),
                Category(id=2, name="Poultry, Meat & Seafood", slug="meat-seafood", icon="🥩", display_order=2),
                Category(id=3, name="Bakery", slug="bakery", icon="🍞", display_order=3),
                Category(id=4, name="Dairy, Eggs & Fridge", slug="dairy-eggs-fridge", icon="🥛", display_order=4),
                Category(id=5, name="Pantry", slug="pantry", icon="🥫", display_order=5),
                Category(id=6, name="Freezer", slug="freezer", icon="❄️", display_order=6),
                Category(id=7, name="Drinks", slug="drinks", icon="🥤", display_order=7),
                Category(id=8, name="Liquor", slug="liquor", icon="🍷", display_order=8),
                Category(id=9, name="Health & Beauty", slug="health-beauty", icon="💄", display_order=9),
                Category(id=10, name="Household", slug="household", icon="🧹", display_order=10),
                Category(id=11, name="Baby", slug="baby", icon="👶", display_order=11),
                Category(id=12, name="Pet", slug="pet", icon="🐕", display_order=12),
                Category(id=13, name="Lunch Box", slug="lunch-box", icon="🍱", display_order=13),
                Category(id=14, name="Entertaining", slug="entertaining", icon="🎉", display_order=14),
                Category(id=15, name="International Foods", slug="international", icon="🌍", display_order=15),
                Category(id=16, name="Tobacco", slug="tobacco", icon="🚬", display_order=16),
                Category(id=17, name="Deli & Charcuterie", slug="deli", icon="🥪", display_order=17),

                # Fresh subcategories (IDs 18-27 for staples/fresh foods)
                Category(id=18, name="Fresh Fruit", slug="fresh-fruit", parent_id=1, icon="🍎", display_order=1),
                Category(id=19, name="Fresh Vegetables", slug="fresh-vegetables", parent_id=1, icon="🥬", display_order=2),
                Category(id=20, name="Salads & Herbs", slug="salads-herbs", parent_id=1, icon="🥗", display_order=3),
                Category(id=21, name="Beef & Veal", slug="beef-veal", parent_id=2, icon="🥩", display_order=1),
                Category(id=22, name="Lamb", slug="lamb", parent_id=2, icon="🍖", display_order=2),
                Category(id=23, name="Pork", slug="pork", parent_id=2, icon="🥓", display_order=3),
                Category(id=24, name="Chicken", slug="chicken", parent_id=2, icon="🍗", display_order=4),
                Category(id=25, name="Seafood", slug="seafood", parent_id=2, icon="🐟", display_order=5),
                Category(id=26, name="Mince", slug="mince", parent_id=2, icon="🥩", display_order=6),
                Category(id=27, name="Sausages", slug="sausages", parent_id=2, icon="🌭", display_order=7),

                # More subcategories for other parent categories
                Category(id=28, name="Bread", slug="bread", parent_id=3, icon="🍞", display_order=1),
                Category(id=29, name="Milk", slug="milk", parent_id=4, icon="🥛", display_order=1),
                Category(id=30, name="Cheese", slug="cheese", parent_id=4, icon="🧀", display_order=2),
                Category(id=31, name="Eggs", slug="eggs", parent_id=4, icon="🥚", display_order=3),
                Category(id=32, name="Butter & Margarine", slug="butter-margarine", parent_id=4, icon="🧈", display_order=4),
                Category(id=33, name="Yoghurt", slug="yoghurt", parent_id=4, icon="🥛", display_order=5),
                Category(id=34, name="Snacks", slug="snacks", parent_id=5, icon="🍿", display_order=1),
                Category(id=35, name="Confectionery", slug="confectionery", parent_id=5, icon="🍬", display_order=2),
                Category(id=36, name="Biscuits", slug="biscuits", parent_id=5, icon="🍪", display_order=3),
            ]
            for cat in default_categories:
                db.add(cat)
            db.commit()
            print(f"Seeded {len(default_categories)} categories")
    finally:
        db.close()
