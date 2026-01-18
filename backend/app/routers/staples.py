"""
Staples Router - API endpoints for everyday staple products.

Provides price comparison for fresh produce, meat, and other staple items
across all stores, even when not on special.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_
from typing import Optional
from decimal import Decimal
from datetime import date

from app.database import get_db
from app.models import Special, Store, Category, Product, StoreProduct, Price
from app.schemas.price import (
    StapleStorePrice,
    StapleProduct,
    StaplesListResponse,
    StapleCategory,
    StaplesCategoriesResponse,
    BasketItem,
    BasketStoreTotal,
    BasketCompareRequest,
    BasketCompareResponse,
)

router = APIRouter(prefix="/staples", tags=["staples"])

# Exclusion keywords - products containing these are NOT fresh food
EXCLUSION_KEYWORDS = [
    # Frozen/processed indicators
    "frozen", "oven bake", "oven ready", "microwave", "heat & eat", "ready to cook",
    # Processed meat products
    "schnitzel", "nugget", "crumbed", "battered", "coated", "breaded", "kiev",
    "finger", "patty", "pattie", "burger", "ball", "bite", "pop",
    # Condiments and sauces
    "sauce", "paste", "powder", "seasoning", "stock", "marinade", "rub",
    "flavour", "flavored", "flavoured", "seasoned", "relish", "chutney",
    # Frozen food brands
    "birds eye", "mccain", "i&j", "cafe series", "on the menu", "herbert adams",
    "lean cuisine", "healthy choice", "weight watchers", "chiko",
    # Canned/preserved products
    "canned", "tinned", "preserved", "diced tomato", "peeled tomato", "crushed tomato",
    "whole peeled", "vine ripened tomatoes", "chopped tomato", "tomato puree",
    "ardmona", "leggo's", "mutti",  # Canned tomato brands
    # Pickled/jarred products
    "pickle", "pickled", "gherkin", "jarred", "in brine", "in vinegar",
    "always fresh",  # Brand that makes pickled/jarred products
    "gourmet garden",  # Brand that makes paste/processed herbs
    # Pet food
    "dog", "cat", "pet",
    # Other processed
    "chip", "crisp", "noodle", "soup", "pizza", "pie", "pastry", "pasty",
    "spring roll", "dim sim", "dumpling", "quiche", "gozleme", "pastizzi",
    # Confectionery and sweets
    "jelly", "lolly", "lollies", "confectionery", "candy", "chocolate", "gummy",
    "licorice", "liquorice", "sweet", "toffee", "fudge", "fizzer",
    # Biscuits and crackers
    "biscuit", "cookie", "cracker", "cruskits", "salada", "crispbread",
    # Personal care (brand names often contain fruit words)
    "sunscreen", "lotion", "spf", "after sun", "candle", "air wick", "essential oil",
    "shampoo", "conditioner", "soap", "body wash", "deodorant", "lip balm", "chapstick",
    "antiperspirant", "lynx", "palmolive", "roll-on",
    # Beverages and drinks
    "juice", "cordial", "soft drink", "soda", "wine", "beer", "spirits", "cider",
    "energy drink", "celsius", "sparkling", "somersby", "apple cider",
    "nectar", "mineral water", "ice tea", "iced tea", "tea ", "lager", "vodka",
    "fruit drink", "coconut water", "poppers", "powerade", "h2coco", "lipton",
    # Dairy and processed dairy
    "yoghurt", "yogurt", "cheese", "milk", "cream", "butter", "ice cream",
    "custard", "weis",
    # Canned fish/meat (not fresh)
    "canned salmon", "canned tuna", "pink salmon", "ally salmon", "ally pink",
    # Breakfast cereals
    "cereal", "muesli", "granola", "oats", "porridge",
    # Spreads and jams
    "jam", "spread", "peanut butter", "honey", "syrup", "marmalade",
    # Baby food (processed)
    "baby food", "baby bellies", "organic puffs", "softcorn", "months+", "heinz",
    # Baked goods
    "cake", "muffin", "bread", "croissant", "danish", "donut", "doughnut", "scone",
    # Snack brands
    "allen's", "arnott's", "aeroplane", "nestle", "cadbury", "smiths", "pringles",
    "beacon", "baxters", "uncle tobys", "roll-ups", "spc ",
    # Oils (not fresh produce)
    "seed oil", "grape seed", "olive oil", "cooking oil", "vegetable oil",
    # Guacamole and prepared dips (processed)
    "guacamole", "dip", "hummus", "tzatziki",
    # Prepared foods
    "macaroni", "lasagne", "lasagna", "bolognese", "cottage pie", "pasta bake",
    # Rice products (processed)
    "ben's original", "uncle bens", "sunrice",
    # Canned vegetables
    "corn kernel", "cut bean", "peas and", "champignon", "black & gold",
    # Processed avocado products
    "avofresh", "smashed avocado",
    # Cooked/prepared meat products
    "beak & sons", "bbq beef", "bbq pork", "bbq chicken", "maple bbq",
    "bourbon bbq", "char siu", "teriyaki",
    # Processed seafood
    "prawn cone", "blue wave",
    # Sprouts/bean sprouts (processed)
    "bean sprouts", "aussie sprouts", "super sprouts",
    # Dried/processed herbs
    "dried", "dehydrated",
    # Minced/processed garlic
    "minced garlic", "finely minced",
    # Alcohol brands
    "xxxx", "smirnoff", "golden circle",
    # Ice cream brands
    "connoisseur", "magnum", "peters", "bulla",
]

# Staple categories configuration - maps to database category IDs
STAPLE_CATEGORIES = {
    "fresh-fruit": {
        "name": "Fresh Fruit",
        "icon": "🍎",
        "category_ids": [18],  # Fresh Fruit
        "parent_ids": [1],  # Fruit & Veg
        "keywords": ["fruit", "apple", "banana", "orange", "berry", "grape", "mango", "melon", "pear", "peach", "plum", "kiwi", "avocado", "lemon", "lime", "mandarin", "pineapple", "watermelon", "strawberry", "blueberry", "raspberry"],
    },
    "fresh-vegetables": {
        "name": "Fresh Vegetables",
        "icon": "🥬",
        "category_ids": [19, 20],  # Fresh Vegetables, Salad & Herbs
        "parent_ids": [1],  # Fruit & Veg
        "keywords": ["vegetable", "potato", "onion", "carrot", "tomato", "lettuce", "broccoli", "capsicum", "cucumber", "spinach", "mushroom", "zucchini", "corn", "bean", "pea", "cauliflower", "celery", "garlic", "ginger", "chilli", "cabbage", "pumpkin", "sweet potato", "salad", "herb"],
    },
    "fresh-meat": {
        "name": "Meat & Poultry",
        "icon": "🥩",
        "category_ids": [21, 22, 23, 24, 25, 26, 46],  # Beef, Chicken, Pork, Lamb, Seafood, Mince, Sausages
        "parent_ids": [2],  # Poultry, Meat & Seafood
        "keywords": ["meat", "chicken", "beef", "lamb", "pork", "mince", "steak", "roast", "chop", "sausage", "bacon", "thigh", "breast", "wing", "drumstick", "fillet", "cutlet", "rump", "scotch"],
    },
    "seafood": {
        "name": "Seafood",
        "icon": "🐟",
        "category_ids": [25, 27],  # Seafood categories
        "parent_ids": [2],  # Poultry, Meat & Seafood
        "keywords": ["seafood", "fish", "salmon", "prawn", "shrimp", "barramundi", "tuna", "cod", "snapper", "bream", "calamari", "squid", "crab", "lobster", "oyster", "mussel"],
    },
}


def _price_to_cents(price: Decimal) -> int:
    """Convert a decimal price to cents."""
    return int(price * 100)


def _cents_to_display(cents: int) -> str:
    """Convert cents to display string like '$3.90'."""
    return f"${cents / 100:.2f}"


def _is_excluded_product(name_lower: str) -> bool:
    """Check if a product name contains any exclusion keywords."""
    return any(exclude in name_lower for exclude in EXCLUSION_KEYWORDS)


def _get_category_for_special(special: Special, db: Session) -> tuple[str, str] | tuple[None, None]:
    """
    Determine the staple category for a special based on its category and name.
    Returns (category_slug, category_display_name) or (None, None) if not a staple.
    """
    special_name_lower = special.name.lower() if special.name else ""

    # First check exclusions - skip non-fresh items
    if _is_excluded_product(special_name_lower):
        return None, None

    category_id = special.category_id

    # Check each staple category
    for cat_slug, cat_config in STAPLE_CATEGORIES.items():
        # Check if special's category matches
        if category_id:
            if category_id in cat_config["category_ids"] or category_id in cat_config.get("parent_ids", []):
                return cat_slug, cat_config["name"]

        # Keyword-based matching as fallback
        for keyword in cat_config["keywords"]:
            if keyword in special_name_lower:
                return cat_slug, cat_config["name"]

    return None, None


def _group_specials_by_product_type(specials: list[Special], db: Session) -> dict[str, list[Special]]:
    """
    Group specials by product type for comparison across stores.
    Returns a dict mapping product_type -> list of specials from different stores.
    """
    # Simple grouping by normalized product name
    groups: dict[str, list[Special]] = {}

    for special in specials:
        # Normalize product name - remove brand, size info for basic matching
        name = special.name.lower().strip()

        # Use the name directly for now (could be enhanced with fuzzy matching)
        if name not in groups:
            groups[name] = []
        groups[name].append(special)

    return groups


def _get_category_for_product_name(name: str) -> tuple[str, str] | tuple[None, None]:
    """
    Determine the staple category for a product based on its name.
    Returns (category_slug, category_display_name) or (None, None) if not a staple.
    """
    name_lower = name.lower() if name else ""

    # First check exclusions - skip non-fresh items
    if _is_excluded_product(name_lower):
        return None, None

    # Check each staple category
    for cat_slug, cat_config in STAPLE_CATEGORIES.items():
        # Keyword-based matching
        for keyword in cat_config["keywords"]:
            if keyword in name_lower:
                return cat_slug, cat_config["name"]

    return None, None


@router.get("/", response_model=StaplesListResponse)
def list_staples(
    category: Optional[str] = Query(None, description="Filter by category slug"),
    store: Optional[str] = Query(None, description="Filter by store slug"),
    sort: str = Query("name", description="Sort by: name, price_low, price_high, savings"),
    search: Optional[str] = Query(None, min_length=2, description="Search by product name"),
    limit: int = Query(50, le=100, description="Maximum items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """
    List staple products with prices from all stores.

    Combines data from:
    - Specials table (items on special)
    - Product/StoreProduct/Price tables (everyday prices)
    """
    today = date.today()
    stores_db = {s.id: s for s in db.query(Store).all()}
    products_map: dict[str, StapleProduct] = {}

    # Get all staple category IDs
    all_cat_ids = []
    for cat_config in STAPLE_CATEGORIES.values():
        all_cat_ids.extend(cat_config["category_ids"])
        all_cat_ids.extend(cat_config.get("parent_ids", []))
    all_cat_ids = list(set(all_cat_ids))

    # If filtering by category, get specific IDs
    if category and category in STAPLE_CATEGORIES:
        cat_config = STAPLE_CATEGORIES[category]
        filter_cat_ids = cat_config["category_ids"] + cat_config.get("parent_ids", [])
    else:
        filter_cat_ids = all_cat_ids

    # Get store filter
    store_id_filter = None
    if store:
        store_obj = db.query(Store).filter(Store.slug == store).first()
        if store_obj:
            store_id_filter = store_obj.id

    # ========== 1. Query Specials table ==========
    # Get ALL valid specials, then filter by category using keywords
    # This ensures we catch fresh products even if category_id isn't set
    specials_query = db.query(Special).join(Store).filter(
        Special.valid_to >= today
    )

    # Optionally filter by category_id if available (performance optimization)
    # But also include specials without category_id for keyword matching
    if filter_cat_ids:
        specials_query = specials_query.filter(
            or_(
                Special.category_id.in_(filter_cat_ids),
                Special.category_id.is_(None)  # Include uncategorized for keyword matching
            )
        )

    if store_id_filter:
        specials_query = specials_query.filter(Special.store_id == store_id_filter)

    if search:
        search_term = f"%{search}%"
        specials_query = specials_query.filter(
            or_(
                Special.name.ilike(search_term),
                Special.brand.ilike(search_term)
            )
        )

    specials = specials_query.all()

    for special in specials:
        # Determine category
        cat_slug, cat_display = _get_category_for_special(special, db)
        if not cat_slug:
            continue

        # Filter by category if specified
        if category and cat_slug != category:
            continue

        # Create a key for this product type (using name as identifier)
        product_key = special.name.lower().strip()

        price_cents = _price_to_cents(special.price)
        store_obj = stores_db.get(special.store_id)
        if not store_obj:
            continue

        store_price = StapleStorePrice(
            store_id=store_obj.id,
            store_name=store_obj.name,
            store_slug=store_obj.slug,
            price=f"${special.price}",
            price_numeric=price_cents,
            unit_price=special.unit_price,
            image_url=special.image_url,
            product_url=special.product_url,
            is_special=True
        )

        if product_key not in products_map:
            products_map[product_key] = StapleProduct(
                id=special.id,
                name=special.name,
                category=cat_slug,
                category_display=cat_display,
                unit=special.size,
                image_url=special.image_url,
                prices=[store_price],
                best_price=store_price,
                price_range=None,
                savings_amount=None
            )
        else:
            # Add this store's price
            existing = products_map[product_key]
            # Check if we already have a price from this store
            if not any(p.store_id == store_obj.id for p in existing.prices):
                existing.prices.append(store_price)

    # ========== 2. Query Product/StoreProduct/Price tables (everyday prices) ==========
    # Get the Fruit & Veg category (ID 1) for imported products
    fruit_veg_category_id = 1  # From the database check earlier

    everyday_query = db.query(
        Product, StoreProduct, Price, Store
    ).select_from(Product).join(
        StoreProduct, StoreProduct.product_id == Product.id
    ).join(
        Price, Price.store_product_id == StoreProduct.id
    ).join(
        Store, Store.id == StoreProduct.store_id
    ).filter(
        Product.category_id == fruit_veg_category_id
    )

    if store_id_filter:
        everyday_query = everyday_query.filter(StoreProduct.store_id == store_id_filter)

    if search:
        search_term = f"%{search}%"
        everyday_query = everyday_query.filter(
            or_(
                Product.name.ilike(search_term),
                Product.brand.ilike(search_term)
            )
        )

    everyday_products = everyday_query.all()

    for product, store_product, price, store_obj in everyday_products:
        # Determine category by name keywords
        cat_slug, cat_display = _get_category_for_product_name(product.name)
        if not cat_slug:
            # Skip products that don't match any fresh food category
            # (either excluded by keyword or simply not a fresh food item)
            continue

        # Filter by category if specified
        if category and cat_slug != category:
            continue

        # Create a key for this product type
        product_key = product.name.lower().strip()

        price_cents = _price_to_cents(price.price) if price.price else 0
        if price_cents == 0:
            continue

        store_price = StapleStorePrice(
            store_id=store_obj.id,
            store_name=store_obj.name,
            store_slug=store_obj.slug,
            price=f"${price.price}",
            price_numeric=price_cents,
            unit_price=str(price.unit_price) if price.unit_price else None,
            image_url=store_product.image_url or product.image_url,
            product_url=None,
            is_special=price.is_special or False
        )

        if product_key not in products_map:
            products_map[product_key] = StapleProduct(
                id=product.id,
                name=product.name,
                category=cat_slug,
                category_display=cat_display,
                unit=product.size,
                image_url=store_product.image_url or product.image_url,
                prices=[store_price],
                best_price=store_price,
                price_range=None,
                savings_amount=None
            )
        else:
            # Add this store's price if not already present
            existing = products_map[product_key]
            if not any(p.store_id == store_obj.id for p in existing.prices):
                existing.prices.append(store_price)

    # ========== 3. Calculate best prices and ranges ==========
    staple_products = []
    for product in products_map.values():
        if product.prices:
            # Sort prices (cheapest first)
            product.prices.sort(key=lambda p: p.price_numeric)
            product.best_price = product.prices[0]

            if len(product.prices) > 1:
                min_price = product.prices[0].price_numeric
                max_price = product.prices[-1].price_numeric
                product.price_range = f"{_cents_to_display(min_price)} - {_cents_to_display(max_price)}"
                product.savings_amount = max_price - min_price

            staple_products.append(product)

    # Sort products
    if sort == "price_low":
        staple_products.sort(key=lambda p: p.best_price.price_numeric if p.best_price else 999999)
    elif sort == "price_high":
        staple_products.sort(key=lambda p: p.best_price.price_numeric if p.best_price else 0, reverse=True)
    elif sort == "savings":
        staple_products.sort(key=lambda p: p.savings_amount or 0, reverse=True)
    else:  # Default: name
        staple_products.sort(key=lambda p: p.name.lower())

    # Pagination
    total = len(staple_products)
    staple_products = staple_products[offset:offset + limit]
    has_more = offset + len(staple_products) < total

    # Get unique categories in results
    result_categories = list(set(p.category for p in staple_products))

    return StaplesListResponse(
        products=staple_products,
        total=total,
        categories=result_categories,
        has_more=has_more
    )


@router.get("/categories", response_model=StaplesCategoriesResponse)
def get_staple_categories(db: Session = Depends(get_db)):
    """
    Get staple categories with product counts.
    Counts products from both Specials and everyday Product tables.
    """
    today = date.today()
    category_counts: dict[str, set[str]] = {cat_slug: set() for cat_slug in STAPLE_CATEGORIES}

    # ========== 1. Count from Specials table ==========
    all_cat_ids = []
    for cat_config in STAPLE_CATEGORIES.values():
        all_cat_ids.extend(cat_config["category_ids"])
        all_cat_ids.extend(cat_config.get("parent_ids", []))
    all_cat_ids = list(set(all_cat_ids))

    specials = db.query(Special).filter(
        Special.valid_to >= today,
        Special.category_id.in_(all_cat_ids)
    ).all()

    for special in specials:
        cat_slug, _ = _get_category_for_special(special, db)
        if cat_slug:
            # Use lowercase name as key to dedupe
            category_counts[cat_slug].add(special.name.lower().strip())

    # ========== 2. Count from Product/StoreProduct tables (everyday prices) ==========
    fruit_veg_category_id = 1

    everyday_products = db.query(Product).join(
        StoreProduct, StoreProduct.product_id == Product.id
    ).join(
        Price, Price.store_product_id == StoreProduct.id
    ).filter(
        Product.category_id == fruit_veg_category_id
    ).distinct().all()

    for product in everyday_products:
        cat_slug, _ = _get_category_for_product_name(product.name)
        if cat_slug:
            category_counts[cat_slug].add(product.name.lower().strip())

    # ========== 3. Build response ==========
    categories = []
    total_products = 0

    for cat_slug, cat_config in STAPLE_CATEGORIES.items():
        count = len(category_counts[cat_slug])
        if count > 0:
            categories.append(StapleCategory(
                slug=cat_slug,
                name=cat_config["name"],
                count=count,
                icon=cat_config.get("icon")
            ))
            total_products += count

    # Sort by count descending
    categories.sort(key=lambda c: c.count, reverse=True)

    return StaplesCategoriesResponse(
        categories=categories,
        total_products=total_products
    )


@router.get("/search", response_model=StaplesListResponse)
def search_staples(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, le=50, description="Maximum items to return"),
    db: Session = Depends(get_db)
):
    """
    Search for staple products by name.
    """
    return list_staples(
        category=None,
        store=None,
        sort="name",
        search=q,
        limit=limit,
        offset=0,
        db=db
    )


@router.get("/{product_id}", response_model=StapleProduct)
def get_staple(product_id: int, db: Session = Depends(get_db)):
    """
    Get a single staple product with prices from all stores.
    """
    special = db.query(Special).filter(Special.id == product_id).first()
    if not special:
        raise HTTPException(status_code=404, detail="Product not found")

    cat_slug, cat_display = _get_category_for_special(special, db)

    stores = {s.id: s for s in db.query(Store).all()}
    store = stores.get(special.store_id)

    price_cents = _price_to_cents(special.price)
    store_price = StapleStorePrice(
        store_id=store.id if store else 0,
        store_name=store.name if store else "Unknown",
        store_slug=store.slug if store else "unknown",
        price=f"${special.price}",
        price_numeric=price_cents,
        unit_price=special.unit_price,
        image_url=special.image_url,
        product_url=special.product_url
    )

    return StapleProduct(
        id=special.id,
        name=special.name,
        category=cat_slug or "other",
        category_display=cat_display or "Other",
        unit=special.size,
        image_url=special.image_url,
        prices=[store_price],
        best_price=store_price,
        price_range=None,
        savings_amount=None
    )


@router.post("/basket-compare", response_model=BasketCompareResponse)
def compare_basket(
    request: BasketCompareRequest,
    db: Session = Depends(get_db)
):
    """
    Compare a shopping basket across all stores.
    """
    if not request.items:
        raise HTTPException(status_code=400, detail="Basket is empty")

    stores = db.query(Store).all()
    store_totals = {
        store.id: {
            "store": store,
            "total_cents": 0,
            "items_found": 0,
            "items_missing": []
        }
        for store in stores
    }

    for item in request.items:
        # Find the special by ID
        special = db.query(Special).filter(Special.id == item.product_id).first()
        if not special:
            for store_id in store_totals:
                store_totals[store_id]["items_missing"].append(item.product_name)
            continue

        # Add price to the store that has this special
        store_id = special.store_id
        if store_id in store_totals:
            price_cents = _price_to_cents(special.price)
            store_totals[store_id]["total_cents"] += price_cents * item.quantity
            store_totals[store_id]["items_found"] += 1

        # Mark as missing for other stores
        for sid in store_totals:
            if sid != store_id:
                store_totals[sid]["items_missing"].append(special.name)

    # Build response
    basket_totals = []
    for store_id, data in store_totals.items():
        store = data["store"]
        basket_totals.append(BasketStoreTotal(
            store_id=store.id,
            store_name=store.name,
            store_slug=store.slug,
            total=_cents_to_display(data["total_cents"]),
            total_numeric=data["total_cents"],
            items_available=data["items_found"],
            items_missing=data["items_missing"]
        ))

    # Sort by total (cheapest first), but prioritize stores with items
    basket_totals.sort(key=lambda t: (t.items_available == 0, t.total_numeric))

    # Find best store (must have at least one item)
    valid_totals = [t for t in basket_totals if t.items_available > 0]

    best_store = None
    best_total = None
    best_total_numeric = None
    savings_vs_worst = None
    savings_numeric = None

    if valid_totals:
        best = valid_totals[0]
        best_store = best.store_name
        best_total = best.total
        best_total_numeric = best.total_numeric

        if len(valid_totals) > 1:
            worst = max(valid_totals, key=lambda t: t.total_numeric)
            if worst.total_numeric > best.total_numeric:
                savings_numeric = worst.total_numeric - best.total_numeric
                savings_vs_worst = f"Save {_cents_to_display(savings_numeric)}"

    return BasketCompareResponse(
        basket_totals=basket_totals,
        best_store=best_store,
        best_total=best_total,
        best_total_numeric=best_total_numeric,
        savings_vs_worst=savings_vs_worst,
        savings_numeric=savings_numeric
    )
