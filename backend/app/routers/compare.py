from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_
from decimal import Decimal
from datetime import date
from typing import Optional
import re
from app.database import get_db
from app.models import Price, StoreProduct, Product, Store, Category, Special
from app.schemas.price import (
    PriceComparison,
    StorePrice,
    CategoryComparison,
    BrandPriceInfo,
    ProductTypeSuggestion,
    SpecialStorePrice,
    BrandMatchResult,
    TypeMatchResult,
    BrandProductsResult,
    FreshFoodItem,
    FreshFoodStorePrice,
    FreshFoodsResponse,
)
from app.services.product_matching import (
    extract_product_type,
    find_similar_products,
    get_product_type_suggestions,
)

router = APIRouter(prefix="/compare", tags=["compare"])


# ============== Fresh Foods Comparison Endpoints ==============
# NOTE: This route must be defined BEFORE /{product_id} to avoid routing conflicts

# Keywords for fresh food filtering (used when category_id not set)
PRODUCE_KEYWORDS = [
    "apple", "banana", "orange", "mango", "grape", "strawberry", "blueberry",
    "raspberry", "watermelon", "melon", "pear", "peach", "plum", "kiwi",
    "avocado", "lemon", "lime", "mandarin", "pineapple", "cherry", "nectarine",
    "potato", "onion", "carrot", "tomato", "lettuce", "broccoli", "capsicum",
    "cucumber", "spinach", "mushroom", "zucchini", "corn", "bean", "pea",
    "cauliflower", "celery", "garlic", "ginger", "chilli", "cabbage", "pumpkin",
    "sweet potato", "salad", "herb", "vegetable", "fruit"
]

MEAT_KEYWORDS = [
    "chicken", "beef", "lamb", "pork", "mince", "steak", "roast", "chop",
    "sausage", "bacon", "thigh", "breast", "wing", "drumstick", "fillet",
    "cutlet", "rump", "scotch", "salmon", "prawn", "fish", "barramundi",
    "tuna", "snapper", "calamari", "seafood", "meat"
]

# Exclusion keywords for processed foods
FRESH_EXCLUSIONS = [
    "frozen", "oven bake", "microwave", "heat & eat", "ready to cook",
    "schnitzel", "nugget", "crumbed", "battered", "coated", "breaded",
    "sauce", "paste", "powder", "seasoning", "stock", "marinade",
    "canned", "tinned", "preserved", "pickled", "jarred",
    "juice", "cordial", "soft drink", "wine", "beer", "cider",
    "yoghurt", "yogurt", "cheese", "milk", "cream", "butter", "ice cream",
    "chip", "crisp", "biscuit", "chocolate", "candy", "confectionery"
]


def _is_fresh_produce(name: str) -> bool:
    """Check if a product name matches fresh produce keywords."""
    name_lower = name.lower()
    # Check exclusions first
    if any(excl in name_lower for excl in FRESH_EXCLUSIONS):
        return False
    return any(kw in name_lower for kw in PRODUCE_KEYWORDS)


def _is_fresh_meat(name: str) -> bool:
    """Check if a product name matches fresh meat/seafood keywords."""
    name_lower = name.lower()
    # Check exclusions first
    if any(excl in name_lower for excl in FRESH_EXCLUSIONS):
        return False
    return any(kw in name_lower for kw in MEAT_KEYWORDS)


@router.get("/fresh-foods", response_model=FreshFoodsResponse)
def get_fresh_foods(
    limit: int = Query(50, le=100, description="Max items per category"),
    db: Session = Depends(get_db)
):
    """
    Get fresh food prices (produce and meat) across all stores.

    Returns products grouped by category with prices from each store.
    Pulls from both regular products AND specials tables.
    """
    today = date.today()

    # Find produce categories
    produce_cats = db.query(Category).filter(
        Category.slug.in_(["fruit-veg", "fruit-vegetables", "fresh-fruit", "fresh-vegetables"])
    ).all()
    produce_cat_ids = [c.id for c in produce_cats]

    # Also include parent category if we have subcategories
    produce_parent = db.query(Category).filter(Category.slug == "fruit-veg").first()
    if produce_parent:
        produce_cat_ids.append(produce_parent.id)
        # Add all subcategory IDs
        subcats = db.query(Category).filter(Category.parent_id == produce_parent.id).all()
        produce_cat_ids.extend([c.id for c in subcats])

    produce_cat_ids = list(set(produce_cat_ids))  # Dedupe

    # Find meat categories
    meat_cats = db.query(Category).filter(
        Category.slug.in_(["meat-seafood", "poultry-meat-seafood", "beef-veal", "chicken", "pork", "lamb", "seafood"])
    ).all()
    meat_cat_ids = [c.id for c in meat_cats]

    # Also include parent category
    meat_parent = db.query(Category).filter(Category.slug == "meat-seafood").first()
    if meat_parent:
        meat_cat_ids.append(meat_parent.id)
        subcats = db.query(Category).filter(Category.parent_id == meat_parent.id).all()
        meat_cat_ids.extend([c.id for c in subcats])

    meat_cat_ids = list(set(meat_cat_ids))  # Dedupe

    # Get stores
    stores = {s.id: s for s in db.query(Store).all()}

    # Helper to get fresh food items from specials
    def get_specials_items(category_ids: list[int], category_name: str, keyword_filter) -> list[FreshFoodItem]:
        """Get fresh food items from the specials table."""
        # Query specials - include both categorized and uncategorized items
        specials_query = db.query(Special).join(Store).filter(
            Special.valid_to >= today
        )

        if category_ids:
            specials_query = specials_query.filter(
                or_(
                    Special.category_id.in_(category_ids),
                    Special.category_id.is_(None)  # Include uncategorized for keyword matching
                )
            )

        specials = specials_query.all()

        # Group specials by product name (to find same product across stores)
        product_groups: dict[str, list[Special]] = {}

        for special in specials:
            # Apply keyword filter
            if not keyword_filter(special.name):
                continue

            name_key = special.name.lower().strip()
            if name_key not in product_groups:
                product_groups[name_key] = []
            product_groups[name_key].append(special)

        items = []
        for name_key, group in product_groups.items():
            # Get unique prices from different stores
            store_prices = []
            prices_numeric = []
            seen_stores = set()

            # Sort by price to get cheapest first per store
            group.sort(key=lambda s: float(s.price))

            for special in group:
                if special.store_id in seen_stores:
                    continue
                seen_stores.add(special.store_id)

                store = stores.get(special.store_id)
                if not store:
                    continue

                store_prices.append(FreshFoodStorePrice(
                    store_id=store.id,
                    store_name=store.name,
                    store_slug=store.slug,
                    price=special.price,
                    unit_price=special.unit_price,
                    image_url=special.image_url,
                    product_url=special.product_url
                ))
                prices_numeric.append(float(special.price))

            if not store_prices:
                continue

            min_price = min(prices_numeric)
            max_price = max(prices_numeric)
            cheapest = next((sp for sp in store_prices if float(sp.price) == min_price), None)

            # Use first special for product info
            first = group[0]
            items.append(FreshFoodItem(
                product_id=first.id,
                product_name=first.name,
                brand=first.brand,
                size=first.size,
                category=category_name,
                stores=sorted(store_prices, key=lambda x: float(x.price)),
                cheapest_store=cheapest.store_name if cheapest else None,
                cheapest_price=Decimal(str(min_price)),
                price_range=f"${min_price:.2f} - ${max_price:.2f}" if min_price != max_price else None
            ))

            if len(items) >= limit:
                break

        return items

    # Helper to get fresh food items from products table
    def get_products_items(category_ids: list[int], category_name: str) -> list[FreshFoodItem]:
        if not category_ids:
            return []

        # Get products with their store products and latest prices
        products = db.query(Product).filter(
            Product.category_id.in_(category_ids)
        ).limit(limit * 2).all()  # Get more to filter duplicates

        items = []
        seen_names = set()

        for product in products:
            # Skip duplicates (same name)
            name_key = product.name.lower().strip()
            if name_key in seen_names:
                continue
            seen_names.add(name_key)

            # Get all store products for this product
            store_products = db.query(StoreProduct).filter(
                StoreProduct.product_id == product.id
            ).all()

            if not store_products:
                continue

            store_prices = []
            prices_numeric = []

            for sp in store_products:
                # Get latest price
                latest_price = db.query(Price).filter(
                    Price.store_product_id == sp.id
                ).order_by(desc(Price.recorded_at)).first()

                if latest_price and sp.store_id in stores:
                    store = stores[sp.store_id]
                    store_prices.append(FreshFoodStorePrice(
                        store_id=store.id,
                        store_name=store.name,
                        store_slug=store.slug,
                        price=latest_price.price,
                        unit_price=f"${latest_price.unit_price}/unit" if latest_price.unit_price else None,
                        image_url=sp.image_url or product.image_url,
                        product_url=None
                    ))
                    prices_numeric.append(float(latest_price.price))

            if not store_prices:
                continue

            # Calculate cheapest and price range
            min_price = min(prices_numeric)
            max_price = max(prices_numeric)
            cheapest = next((sp for sp in store_prices if float(sp.price) == min_price), None)

            items.append(FreshFoodItem(
                product_id=product.id,
                product_name=product.name,
                brand=product.brand,
                size=product.size,
                category=category_name,
                stores=sorted(store_prices, key=lambda x: float(x.price)),
                cheapest_store=cheapest.store_name if cheapest else None,
                cheapest_price=Decimal(str(min_price)),
                price_range=f"${min_price:.2f} - ${max_price:.2f}" if min_price != max_price else None
            ))

            if len(items) >= limit:
                break

        return items

    # Get items from both products table AND specials table
    produce_from_products = get_products_items(produce_cat_ids, "produce")
    produce_from_specials = get_specials_items(produce_cat_ids, "produce", _is_fresh_produce)

    meat_from_products = get_products_items(meat_cat_ids, "meat")
    meat_from_specials = get_specials_items(meat_cat_ids, "meat", _is_fresh_meat)

    # Merge results (avoid duplicates by name)
    def merge_items(from_products: list[FreshFoodItem], from_specials: list[FreshFoodItem]) -> list[FreshFoodItem]:
        seen_names = {item.product_name.lower().strip() for item in from_products}
        merged = list(from_products)
        for item in from_specials:
            if item.product_name.lower().strip() not in seen_names:
                merged.append(item)
                seen_names.add(item.product_name.lower().strip())
        return merged[:limit]

    produce_items = merge_items(produce_from_products, produce_from_specials)
    meat_items = merge_items(meat_from_products, meat_from_specials)

    return FreshFoodsResponse(
        produce=produce_items,
        meat=meat_items,
        total_products=len(produce_items) + len(meat_items),
        last_updated=None  # Could track this in the future
    )


# ============== Product Comparison Endpoints ==============

@router.get("/{product_id}", response_model=PriceComparison)
def compare_product(product_id: int, db: Session = Depends(get_db)):
    """Compare prices for a product across all stores."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get all store products
    store_products = db.query(StoreProduct).filter(
        StoreProduct.product_id == product_id
    ).all()

    store_prices = []
    min_price = None
    min_store = None

    for sp in store_products:
        # Get latest price
        latest_price = db.query(Price).filter(
            Price.store_product_id == sp.id
        ).order_by(desc(Price.recorded_at)).first()

        if latest_price:
            store = db.query(Store).filter(Store.id == sp.store_id).first()

            store_price = StorePrice(
                store_id=store.id,
                store_name=store.name,
                store_slug=store.slug,
                price=latest_price.price,
                unit_price=latest_price.unit_price,
                is_special=latest_price.is_special,
                was_price=latest_price.was_price,
                savings=None
            )
            store_prices.append(store_price)

            # Track minimum price
            if min_price is None or latest_price.price < min_price:
                min_price = latest_price.price
                min_store = store.name

    # Calculate savings relative to cheapest
    if min_price and len(store_prices) > 1:
        for sp in store_prices:
            if sp.price > min_price:
                sp.savings = sp.price - min_price

    # Calculate price difference between highest and lowest
    price_diff = None
    if store_prices:
        prices = [sp.price for sp in store_prices]
        price_diff = max(prices) - min(prices)

    return PriceComparison(
        product_id=product_id,
        product_name=product.name,
        stores=store_prices,
        cheapest_store=min_store,
        price_difference=price_diff
    )


@router.post("/basket")
def compare_basket(
    product_ids: list[int],
    db: Session = Depends(get_db)
):
    """Compare total basket price across stores."""
    stores = db.query(Store).all()
    store_totals = {store.slug: {"store_name": store.name, "total": Decimal(0), "items_found": 0, "items_missing": []} for store in stores}

    for product_id in product_ids:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            continue

        for store in stores:
            sp = db.query(StoreProduct).filter(
                StoreProduct.product_id == product_id,
                StoreProduct.store_id == store.id
            ).first()

            if sp:
                latest_price = db.query(Price).filter(
                    Price.store_product_id == sp.id
                ).order_by(desc(Price.recorded_at)).first()

                if latest_price:
                    store_totals[store.slug]["total"] += latest_price.price
                    store_totals[store.slug]["items_found"] += 1
                else:
                    store_totals[store.slug]["items_missing"].append(product.name)
            else:
                store_totals[store.slug]["items_missing"].append(product.name)

    # Find cheapest
    cheapest = min(store_totals.items(), key=lambda x: x[1]["total"])

    return {
        "basket_size": len(product_ids),
        "store_totals": store_totals,
        "cheapest_store": cheapest[0],
        "cheapest_total": float(cheapest[1]["total"])
    }


# ============== Category/Type Comparison Endpoints ==============

@router.get("/type/search", response_model=list[ProductTypeSuggestion])
def search_product_types(
    q: str = Query(..., min_length=2, description="Search query"),
    category_id: Optional[int] = None,
    limit: int = Query(20, le=50),
    db: Session = Depends(get_db)
):
    """
    Search for product types (not individual products).

    Returns unique product type + size combinations with brand counts.
    Useful for finding comparable products across brands.
    """
    results = get_product_type_suggestions(db, q, category_id, limit)
    return [ProductTypeSuggestion(**r) for r in results]


@router.get("/type/{product_id}", response_model=CategoryComparison)
def compare_product_type(
    product_id: int,
    db: Session = Depends(get_db)
):
    """
    Compare ALL brands of the same product type + size.

    Given a product like "Dairy Farmers Full Cream Milk 2L", finds all other
    brands of "Full Cream Milk 2L" and compares prices across all stores.

    Returns brands sorted by cheapest price (lowest first).
    """
    # 1. Get the reference product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # 2. Extract the product type (name without brand)
    product_type = extract_product_type(product.name, product.brand)

    # 3. Find all products with matching type + size
    similar_products = find_similar_products(
        db,
        product_type,
        product.size,
        product.category_id
    )

    if not similar_products:
        similar_products = [product]  # At minimum, include the queried product

    # 4. Get category name
    category_name = None
    if product.category_id:
        category = db.query(Category).filter(Category.id == product.category_id).first()
        if category:
            category_name = category.name

    # 5. Get prices for all matching products
    brands: list[BrandPriceInfo] = []
    overall_cheapest_price = None
    overall_cheapest_brand = None
    overall_cheapest_store = None

    for prod in similar_products:
        store_prices = _get_product_store_prices(db, prod.id)

        if not store_prices:
            continue

        # Find cheapest for this brand
        brand_cheapest_price = min(sp.price for sp in store_prices)
        brand_cheapest_store = next(
            (sp.store_name for sp in store_prices if sp.price == brand_cheapest_price),
            None
        )

        brand_info = BrandPriceInfo(
            product_id=prod.id,
            brand=prod.brand,
            product_name=prod.name,
            image_url=prod.image_url,
            store_prices=store_prices,
            cheapest_price=brand_cheapest_price,
            cheapest_store=brand_cheapest_store
        )
        brands.append(brand_info)

        # Track overall cheapest
        if overall_cheapest_price is None or brand_cheapest_price < overall_cheapest_price:
            overall_cheapest_price = brand_cheapest_price
            overall_cheapest_brand = prod.brand or prod.name
            overall_cheapest_store = brand_cheapest_store

    # 6. Sort brands by cheapest price (lowest first)
    brands.sort(key=lambda b: b.cheapest_price if b.cheapest_price else Decimal("999999"))

    # 7. Count total options (all store-brand combinations)
    total_options = sum(len(b.store_prices) for b in brands)

    return CategoryComparison(
        product_type=product_type,
        size=product.size,
        category_id=product.category_id,
        category_name=category_name,
        brands=brands,
        cheapest_overall=overall_cheapest_price,
        cheapest_brand=overall_cheapest_brand,
        cheapest_store=overall_cheapest_store,
        total_options=total_options
    )


def _get_product_store_prices(db: Session, product_id: int) -> list[StorePrice]:
    """Helper to get all store prices for a single product."""
    store_products = db.query(StoreProduct).filter(
        StoreProduct.product_id == product_id
    ).all()

    store_prices = []

    for sp in store_products:
        latest_price = db.query(Price).filter(
            Price.store_product_id == sp.id
        ).order_by(desc(Price.recorded_at)).first()

        if latest_price:
            store = db.query(Store).filter(Store.id == sp.store_id).first()
            if store:
                store_prices.append(StorePrice(
                    store_id=store.id,
                    store_name=store.name,
                    store_slug=store.slug,
                    price=latest_price.price,
                    unit_price=latest_price.unit_price,
                    is_special=latest_price.is_special,
                    was_price=latest_price.was_price,
                    savings=None
                ))

    return store_prices


# ============== Specials Comparison Endpoints ==============

@router.get("/specials/brand-match", response_model=list[BrandMatchResult])
def compare_specials_brand_match(
    search: str = Query(..., min_length=2, description="Product name to search for"),
    db: Session = Depends(get_db)
):
    """
    Find identical/similar products on special across different stores.

    Searches for products with matching names and groups them by store,
    showing where you can find the same product cheapest.

    Example: Search "Cadbury Dairy Milk" to see prices at Woolworths, Coles, ALDI, IGA.
    """
    today = date.today()

    # Search for matching specials across stores
    specials = db.query(Special).join(Store).filter(
        Special.valid_to >= today,
        or_(
            Special.name.ilike(f"%{search}%"),
            Special.brand.ilike(f"%{search}%")
        )
    ).order_by(Special.name, Special.price).all()

    if not specials:
        return []

    # Group by normalized product name (name + size)
    product_groups: dict[str, list[Special]] = {}

    for special in specials:
        # Create a key from brand + name + size for exact matching
        key = _normalize_product_key(special.name, special.brand, special.size)
        if key not in product_groups:
            product_groups[key] = []
        product_groups[key].append(special)

    results = []
    for key, group in product_groups.items():
        # Skip products only at one store
        unique_stores = set(s.store_id for s in group)
        if len(unique_stores) < 2 and len(group) < 2:
            continue

        # Get cheapest per store (in case of duplicates)
        store_prices = {}
        for special in group:
            store_id = special.store_id
            if store_id not in store_prices or special.price < store_prices[store_id].price:
                store_prices[store_id] = special

        stores = [
            SpecialStorePrice(
                special_id=s.id,
                store_id=s.store_id,
                store_name=s.store.name,
                store_slug=s.store.slug,
                price=s.price,
                was_price=s.was_price,
                discount_percent=s.discount_percent,
                unit_price=s.unit_price,
                image_url=s.image_url,
                product_url=s.product_url,
                valid_to=s.valid_to
            )
            for s in sorted(store_prices.values(), key=lambda x: x.price)
        ]

        if stores:
            prices = [s.price for s in stores]
            min_price = min(prices)
            max_price = max(prices)

            results.append(BrandMatchResult(
                product_name=group[0].name,
                brand=group[0].brand,
                size=group[0].size,
                stores=stores,
                cheapest_store=stores[0].store_name if stores else None,
                price_spread=max_price - min_price if len(stores) > 1 else None,
                savings_potential=max_price - min_price if len(stores) > 1 else None
            ))

    # Sort by number of store matches (more stores = more relevant)
    results.sort(key=lambda r: len(r.stores), reverse=True)

    return results[:20]  # Limit to top 20 matches


@router.get("/specials/type-match/{special_id}", response_model=TypeMatchResult)
def compare_specials_type_match(
    special_id: int,
    db: Session = Depends(get_db)
):
    """
    Find similar product types across all stores and brands.

    Given a specific special, finds all other products of the same type
    (regardless of brand) and compares prices.

    Example: Given "Dairy Farmers Full Cream Milk 2L", find all other
    2L milk products from any brand at any store currently on special.
    """
    today = date.today()

    # Get the reference special
    reference = db.query(Special).join(Store).filter(
        Special.id == special_id
    ).first()

    if not reference:
        raise HTTPException(status_code=404, detail="Special not found")

    # Extract product type (remove brand from name)
    product_type = _extract_special_type(reference.name, reference.brand)

    # Get category info
    category_name = None
    if reference.category_id:
        category = db.query(Category).filter(Category.id == reference.category_id).first()
        if category:
            category_name = category.name

    # Find similar products
    # Strategy: Match on extracted product type within same category
    similar_query = db.query(Special).join(Store).filter(
        Special.valid_to >= today,
        Special.id != special_id
    )

    # Filter by category if available
    if reference.category_id:
        similar_query = similar_query.filter(Special.category_id == reference.category_id)

    # Filter by size if available (exact match on size)
    if reference.size:
        similar_query = similar_query.filter(Special.size == reference.size)

    # Get all candidates and filter by product type match
    candidates = similar_query.all()

    similar_products = []
    for candidate in candidates:
        candidate_type = _extract_special_type(candidate.name, candidate.brand)

        # Check if product types are similar enough
        if _is_similar_type(product_type, candidate_type):
            similar_products.append(SpecialStorePrice(
                special_id=candidate.id,
                store_id=candidate.store_id,
                store_name=candidate.store.name,
                store_slug=candidate.store.slug,
                price=candidate.price,
                was_price=candidate.was_price,
                discount_percent=candidate.discount_percent,
                unit_price=candidate.unit_price,
                image_url=candidate.image_url,
                product_url=candidate.product_url,
                valid_to=candidate.valid_to
            ))

    # Sort by price ascending
    similar_products.sort(key=lambda x: x.price)

    # Build reference product info
    reference_price = SpecialStorePrice(
        special_id=reference.id,
        store_id=reference.store_id,
        store_name=reference.store.name,
        store_slug=reference.store.slug,
        price=reference.price,
        was_price=reference.was_price,
        discount_percent=reference.discount_percent,
        unit_price=reference.unit_price,
        image_url=reference.image_url,
        product_url=reference.product_url,
        valid_to=reference.valid_to
    )

    # Find cheapest option
    all_options = [reference_price] + similar_products
    cheapest = min(all_options, key=lambda x: x.price)

    return TypeMatchResult(
        product_type=product_type,
        category_id=reference.category_id,
        category_name=category_name,
        reference_product=reference_price,
        similar_products=similar_products,
        cheapest_option=f"Special #{cheapest.special_id}",
        cheapest_price=cheapest.price,
        total_options=len(all_options)
    )


# Brand products endpoint - find all products from same brand across stores
@router.get("/specials/brand-products/{special_id}", response_model=BrandProductsResult)
def get_brand_products(
    special_id: int,
    db: Session = Depends(get_db)
):
    """
    Find ALL products from the same brand across all stores.

    Given a specific special, finds all other products with the same brand
    currently on special at any store.

    Example: Given "Coca-Cola Classic 10 pack" at Woolworths, find all other
    Coca-Cola products on special at Woolworths, Coles, IGA, ALDI.
    """
    today = date.today()

    # Get the reference special
    reference = db.query(Special).join(Store).filter(
        Special.id == special_id
    ).first()

    if not reference:
        raise HTTPException(status_code=404, detail="Special not found")

    # Get the brand
    brand = reference.brand
    if not brand:
        # Try to extract brand from name if not set
        from app.services.brand_extractor import extract_brand_from_name
        brand = extract_brand_from_name(reference.name)

    if not brand:
        # No brand found - return empty result
        reference_price = SpecialStorePrice(
            special_id=reference.id,
            store_id=reference.store_id,
            store_name=reference.store.name,
            store_slug=reference.store.slug,
            price=reference.price,
            was_price=reference.was_price,
            discount_percent=reference.discount_percent,
            unit_price=reference.unit_price,
            image_url=reference.image_url,
            product_url=reference.product_url,
            valid_to=reference.valid_to
        )
        return BrandProductsResult(
            brand="Unknown",
            reference_product=reference_price,
            brand_products=[],
            cheapest_price=reference.price,
            total_products=1,
            stores_with_brand=[reference.store.name]
        )

    # Find all products with this brand across all stores
    brand_specials = db.query(Special).join(Store).filter(
        Special.valid_to >= today,
        Special.brand.ilike(brand)  # Case-insensitive brand match
    ).order_by(Special.price).all()

    # Build reference product info
    reference_price = SpecialStorePrice(
        special_id=reference.id,
        store_id=reference.store_id,
        store_name=reference.store.name,
        store_slug=reference.store.slug,
        price=reference.price,
        was_price=reference.was_price,
        discount_percent=reference.discount_percent,
        unit_price=reference.unit_price,
        image_url=reference.image_url,
        product_url=reference.product_url,
        valid_to=reference.valid_to
    )

    # Build list of other brand products (excluding reference)
    brand_products = []
    stores_with_brand = set()
    stores_with_brand.add(reference.store.name)

    for special in brand_specials:
        stores_with_brand.add(special.store.name)
        if special.id != reference.id:
            brand_products.append(SpecialStorePrice(
                special_id=special.id,
                store_id=special.store_id,
                store_name=special.store.name,
                store_slug=special.store.slug,
                price=special.price,
                was_price=special.was_price,
                discount_percent=special.discount_percent,
                unit_price=special.unit_price,
                image_url=special.image_url,
                product_url=special.product_url,
                valid_to=special.valid_to
            ))

    # Find cheapest price
    all_prices = [reference.price] + [p.price for p in brand_products]
    cheapest_price = min(all_prices) if all_prices else reference.price

    return BrandProductsResult(
        brand=brand,
        reference_product=reference_price,
        brand_products=brand_products,
        cheapest_price=cheapest_price,
        total_products=len(brand_products) + 1,  # Include reference
        stores_with_brand=sorted(list(stores_with_brand))
    )


def _normalize_product_key(name: str, brand: str | None, size: str | None) -> str:
    """Create a normalized key for grouping identical products."""
    parts = []
    if brand:
        parts.append(brand.lower().strip())
    parts.append(name.lower().strip())
    if size:
        parts.append(size.lower().strip())
    return "|".join(parts)


def _extract_special_type(name: str, brand: str | None) -> str:
    """Extract the product type from a special name (removing brand)."""
    product_type = name

    if brand:
        # Remove brand from the beginning of the name
        brand_pattern = re.compile(re.escape(brand), re.IGNORECASE)
        product_type = brand_pattern.sub("", product_type).strip()

        # If removing brand leaves empty string, use original name
        if not product_type:
            product_type = name

    # Remove size info from the end (e.g., "180g", "2L", "500ml")
    product_type = re.sub(r'\s*\d+\s*(g|kg|ml|l|pk|pack|each)\s*$', '', product_type, flags=re.IGNORECASE)

    # Clean up extra whitespace and punctuation
    product_type = re.sub(r'\s+', ' ', product_type).strip()
    product_type = product_type.strip('| -')

    return product_type


def _is_similar_type(type1: str, type2: str) -> bool:
    """Check if two product types are similar enough to compare."""
    t1 = type1.lower().strip()
    t2 = type2.lower().strip()

    # Skip empty types
    if not t1 or not t2:
        return False

    # Exact match
    if t1 == t2:
        return True

    # Normalize common plurals for produce
    def normalize_plural(s: str) -> str:
        # Handle common plural patterns
        if s.endswith('oes'):  # mangoes -> mango, tomatoes -> tomato
            return s[:-2]
        if s.endswith('ies'):  # cherries -> cherry
            return s[:-3] + 'y'
        if s.endswith('es'):   # peaches -> peach
            return s[:-2]
        if s.endswith('s'):    # apples -> apple
            return s[:-1]
        return s

    t1_norm = normalize_plural(t1)
    t2_norm = normalize_plural(t2)

    # Check normalized exact match
    if t1_norm == t2_norm:
        return True

    # Containment check - but only for meaningful lengths (>3 chars)
    # This prevents "s" or "es" from matching everything
    if len(t1) > 3 and len(t2) > 3:
        if t1 in t2 or t2 in t1:
            return True
        if t1_norm in t2_norm or t2_norm in t1_norm:
            return True

    # Word overlap check
    words1 = set(t1.split())
    words2 = set(t2.split())

    # Remove common filler words
    common_words = {'the', 'a', 'an', 'and', 'or', 'of', 'with', 'in', 'on',
                    'fresh', 'australian', 'coles', 'woolworths', 'aldi', 'iga'}
    words1 = words1 - common_words
    words2 = words2 - common_words

    if not words1 or not words2:
        return False

    # Normalize words for comparison
    words1_norm = {normalize_plural(w) for w in words1}
    words2_norm = {normalize_plural(w) for w in words2}

    # Check for overlap in normalized words
    overlap = len(words1_norm & words2_norm)

    # For produce (typically 1-2 significant words), require actual word match
    min_words = min(len(words1_norm), len(words2_norm))

    if min_words <= 2:
        # Must have at least 1 word in common
        return overlap >= 1
    else:
        # For longer product names, 50% overlap is ok
        return overlap >= min_words / 2
