from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, desc
from datetime import date, datetime
from typing import Optional, List, Tuple

from app.database import get_db
from app.config import get_settings
from app.models import Special, Store, ScrapeLog, Category


# Search term to category slug mapping for smart search
# When user searches for these terms, filter to the matching category instead of text search
SEARCH_CATEGORY_MAP = {
    # Sauces & Condiments
    "sauce": "sauces-condiments",
    "sauces": "sauces-condiments",
    "ketchup": "sauces-condiments",
    "mayonnaise": "sauces-condiments",
    "mustard": "sauces-condiments",
    "condiment": "sauces-condiments",
    "condiments": "sauces-condiments",
    # Chips & Crisps
    "chips": "chips-crisps",
    "crisps": "chips-crisps",
    # Chocolate
    "chocolate": "chocolate",
    # Biscuits
    "biscuit": "biscuits",
    "biscuits": "biscuits",
    "cookie": "biscuits",
    "cookies": "biscuits",
    # Drinks subcategories
    "soft drink": "soft-drinks",
    "soft drinks": "soft-drinks",
    "juice": "juice",
    "water": "water",
    "coffee": "coffee-tea",
    "tea": "coffee-tea",
    "energy drink": "energy-drinks",
    "energy drinks": "energy-drinks",
    # Dairy
    "milk": "milk",
    "cheese": "cheese",
    "yoghurt": "yoghurt",
    "yogurt": "yoghurt",
    "butter": "butter-cream",
    "eggs": "eggs",
    # Meat
    "chicken": "chicken",
    "beef": "beef-veal",
    "pork": "pork",
    "lamb": "lamb",
    "seafood": "seafood",
    "sausage": "sausages-bbq",
    "sausages": "sausages-bbq",
    # Pantry
    "pasta": "pasta-noodles",
    "noodles": "pasta-noodles",
    "rice": "rice-grains",
    "cereal": "breakfast-cereals",
    "cereals": "breakfast-cereals",
    # Cleaning
    "laundry": "laundry",
    "cleaning": "cleaning-products",
    "dishwashing": "dishwashing",
    # Pet
    "dog food": "dog-food",
    "cat food": "cat-food",
    "pet food": "pet",
    # Baby
    "nappies": "nappies-wipes",
    "baby food": "baby-food",
    "baby formula": "baby-formula",
    # Personal care
    "shampoo": "hair-care",
    "deodorant": "deodorant",
    "toothpaste": "oral-care",
    # Frozen
    "ice cream": "ice-cream-frozen-desserts",
    "frozen pizza": "frozen-pizza",
    "frozen meals": "frozen-meals",
}


def find_category_for_search(search_term: str, db: Session) -> Optional[int]:
    """
    Check if search term matches a category and return the category ID.
    Returns None if no category match found.
    """
    search_lower = search_term.lower().strip()

    # First check our explicit mapping
    if search_lower in SEARCH_CATEGORY_MAP:
        slug = SEARCH_CATEGORY_MAP[search_lower]
        cat = db.query(Category).filter(Category.slug == slug).first()
        if cat:
            return cat.id

    # Then try to match against category names/slugs directly
    cat = db.query(Category).filter(
        or_(
            func.lower(Category.name).contains(search_lower),
            func.lower(Category.slug).contains(search_lower.replace(" ", "-"))
        )
    ).first()

    if cat:
        return cat.id

    return None


from app.schemas.special import (
    Special as SpecialSchema,
    SpecialsList,
    SpecialsStats,
    CategoryCount,
    ScrapeLogResponse,
    CategoryTreeItem,
    CategoryTreeResponse,
    SubcategoryItem,
)

router = APIRouter(prefix="/specials", tags=["specials"])


@router.get("/", response_model=SpecialsList)
def get_specials(
    store: Optional[str] = Query(None, description="Filter by store slug (woolworths, coles, aldi)"),
    category: Optional[str] = Query(None, description="Filter by original category string"),
    category_id: Optional[int] = Query(None, description="Filter by unified category ID"),
    min_discount: int = Query(0, ge=0, le=100, description="Minimum discount percentage"),
    search: Optional[str] = Query(None, min_length=2, description="Search in product name/brand"),
    sort: str = Query("discount", description="Sort by: discount, price, name"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get current specials with filters and pagination."""
    today = date.today()

    # Base query - only active specials
    query = db.query(Special).join(Store).filter(
        Special.valid_to >= today
    )

    # Apply filters
    if store:
        query = query.filter(Store.slug == store)

    if category:
        query = query.filter(Special.category == category)

    if category_id:
        # Get category and its subcategories
        cat = db.query(Category).filter(Category.id == category_id).first()
        if cat:
            # If this is a parent category, include all subcategory IDs
            if cat.parent_id is None:
                subcategory_ids = [c.id for c in cat.subcategories]
                category_ids = [category_id] + subcategory_ids
                query = query.filter(Special.category_id.in_(category_ids))
            else:
                query = query.filter(Special.category_id == category_id)

    if min_discount > 0:
        query = query.filter(Special.discount_percent >= min_discount)

    if search:
        # Smart search: check if search term matches a category
        # If so, filter by that category instead of just text matching
        if not category_id:  # Only apply smart search if no explicit category filter
            matched_category_id = find_category_for_search(search, db)
            if matched_category_id:
                # Search term matches a category - filter to that category
                cat = db.query(Category).filter(Category.id == matched_category_id).first()
                if cat:
                    if cat.parent_id is None:
                        # Parent category - include subcategories
                        subcategory_ids = [c.id for c in cat.subcategories]
                        category_ids = [matched_category_id] + subcategory_ids
                        query = query.filter(Special.category_id.in_(category_ids))
                    else:
                        query = query.filter(Special.category_id == matched_category_id)
            else:
                # No category match - do regular text search
                query = query.filter(
                    or_(
                        Special.name.ilike(f"%{search}%"),
                        Special.brand.ilike(f"%{search}%")
                    )
                )
        else:
            # Explicit category already set - just do text search within that category
            query = query.filter(
                or_(
                    Special.name.ilike(f"%{search}%"),
                    Special.brand.ilike(f"%{search}%")
                )
            )

    # Get total count before pagination
    total = query.count()

    # Apply sorting
    if sort == "discount":
        query = query.order_by(desc(Special.discount_percent))
    elif sort == "price":
        query = query.order_by(Special.price)
    elif sort == "name":
        query = query.order_by(Special.name)
    else:
        query = query.order_by(desc(Special.discount_percent))

    # Apply pagination
    skip = (page - 1) * limit
    specials = query.offset(skip).limit(limit).all()

    # Add store info to response
    result = []
    for special in specials:
        item = SpecialSchema(
            id=special.id,
            name=special.name,
            brand=special.brand,
            size=special.size,
            category=special.category,
            price=special.price,
            was_price=special.was_price,
            discount_percent=special.discount_percent,
            unit_price=special.unit_price,
            store_product_id=special.store_product_id,
            product_url=special.product_url,
            image_url=special.image_url,
            valid_from=special.valid_from,
            valid_to=special.valid_to,
            store_id=special.store_id,
            store_name=special.store.name,
            store_slug=special.store.slug,
            scraped_at=special.scraped_at,
            created_at=special.created_at,
        )
        result.append(item)

    return SpecialsList(
        items=result,
        total=total,
        page=page,
        limit=limit,
        has_more=(skip + limit) < total
    )


@router.get("/stats", response_model=SpecialsStats)
def get_stats(db: Session = Depends(get_db)):
    """Get summary statistics for specials."""
    today = date.today()

    # Total active specials
    total = db.query(Special).filter(Special.valid_to >= today).count()

    # Count by store
    store_counts = db.query(
        Store.slug,
        func.count(Special.id)
    ).join(Special).filter(
        Special.valid_to >= today
    ).group_by(Store.slug).all()

    by_store = {slug: count for slug, count in store_counts}

    # Half price count (50%+ discount)
    half_price = db.query(Special).filter(
        Special.valid_to >= today,
        Special.discount_percent >= 50
    ).count()

    # Last scrape time
    last_scrape = db.query(func.max(ScrapeLog.completed_at)).filter(
        ScrapeLog.status == "success"
    ).scalar()

    return SpecialsStats(
        total_specials=total,
        by_store=by_store,
        half_price_count=half_price,
        last_updated=last_scrape
    )


@router.get("/categories", response_model=list[CategoryCount])
def get_categories(db: Session = Depends(get_db)):
    """Get list of categories with counts (legacy - original category strings)."""
    today = date.today()

    categories = db.query(
        Special.category,
        func.count(Special.id).label("count")
    ).filter(
        Special.valid_to >= today,
        Special.category.isnot(None)
    ).group_by(Special.category).order_by(desc("count")).all()

    return [CategoryCount(name=cat, count=count) for cat, count in categories if cat]


@router.get("/categories/tree", response_model=CategoryTreeResponse)
def get_category_tree(db: Session = Depends(get_db)):
    """Get hierarchical category tree with product counts."""
    today = date.today()

    # Get all parent categories ordered by display_order
    parent_categories = db.query(Category).filter(
        Category.parent_id.is_(None)
    ).order_by(Category.display_order).all()

    # Build category counts mapping (category_id -> count of active specials)
    category_counts = db.query(
        Special.category_id,
        func.count(Special.id).label("count")
    ).filter(
        Special.valid_to >= today,
        Special.category_id.isnot(None)
    ).group_by(Special.category_id).all()

    count_map = {cat_id: count for cat_id, count in category_counts}

    # Count uncategorized specials
    uncategorized_count = db.query(func.count(Special.id)).filter(
        Special.valid_to >= today,
        Special.category_id.is_(None)
    ).scalar() or 0

    # Total categorized
    total_categorized = sum(count_map.values())

    # Build tree structure
    result = []
    for parent in parent_categories:
        # Get subcategories
        subcats = db.query(Category).filter(
            Category.parent_id == parent.id
        ).order_by(Category.display_order).all()

        # Calculate parent count (direct + all subcategories)
        parent_count = count_map.get(parent.id, 0)
        subcat_items = []

        for sub in subcats:
            sub_count = count_map.get(sub.id, 0)
            parent_count += sub_count
            subcat_items.append(SubcategoryItem(
                id=sub.id,
                name=sub.name,
                slug=sub.slug,
                count=sub_count
            ))

        result.append(CategoryTreeItem(
            id=parent.id,
            name=parent.name,
            slug=parent.slug,
            icon=parent.icon,
            count=parent_count,
            subcategories=subcat_items
        ))

    return CategoryTreeResponse(
        categories=result,
        total_categorized=total_categorized,
        total_uncategorized=uncategorized_count
    )


@router.get("/stores")
def get_stores_with_specials(db: Session = Depends(get_db)):
    """Get stores with their special counts."""
    today = date.today()

    stores = db.query(Store).all()

    result = []
    for store in stores:
        count = db.query(Special).filter(
            Special.store_id == store.id,
            Special.valid_to >= today
        ).count()

        result.append({
            "id": store.id,
            "name": store.name,
            "slug": store.slug,
            "logo_url": store.logo_url,
            "specials_count": count
        })

    return result


@router.get("/scrape-logs", response_model=list[ScrapeLogResponse])
def get_scrape_logs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get recent scrape logs for monitoring."""
    logs = db.query(ScrapeLog).join(Store, isouter=True).order_by(
        desc(ScrapeLog.started_at)
    ).limit(limit).all()

    return [
        ScrapeLogResponse(
            id=log.id,
            store_id=log.store_id,
            store_name=log.store.name if log.store else None,
            started_at=log.started_at,
            completed_at=log.completed_at,
            items_found=log.items_found,
            status=log.status,
            error_message=log.error_message
        )
        for log in logs
    ]


@router.post("/admin/scrape")
def trigger_scrape(
    store: Optional[str] = Query(None, description="Store slug to scrape (or all if not specified)"),
    x_admin_key: str = Header(..., description="Admin API key"),
    db: Session = Depends(get_db)
):
    """Manually trigger a scrape (admin only)."""
    # Verify admin key
    admin_key = get_settings().admin_api_key
    if not admin_key or x_admin_key != admin_key:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    from app.services.firecrawl_scraper import FirecrawlScraper

    try:
        scraper = FirecrawlScraper()

        if store:
            # Scrape specific store
            count = scraper.scrape_store(store, db)
            return {"status": "success", "store": store, "items_scraped": count}
        else:
            # Scrape all stores
            results = scraper.scrape_all_stores(db)
            return {"status": "success", "results": results}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scrape failed: {str(e)}")


@router.delete("/admin/clear-expired")
def clear_expired(
    x_admin_key: str = Header(..., description="Admin API key"),
    db: Session = Depends(get_db)
):
    """Clear expired specials from database (admin only)."""
    admin_key = get_settings().admin_api_key
    if not admin_key or x_admin_key != admin_key:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    from app.services.firecrawl_scraper import FirecrawlScraper

    scraper = FirecrawlScraper()
    deleted = scraper.clear_expired_specials(db)

    return {"status": "success", "deleted_count": deleted}


@router.post("/admin/rescrape")
def rescrape_all(
    x_admin_key: str = Header(..., description="Admin API key"),
):
    """Clear ALL specials and run fresh scrape (admin only)."""
    admin_key = get_settings().admin_api_key
    if not admin_key or x_admin_key != admin_key:
        raise HTTPException(status_code=403, detail="Invalid admin key")

    from app.services.firecrawl_scraper import FirecrawlScraper

    try:
        scraper = FirecrawlScraper()

        # Clear all existing specials (uses its own session)
        deleted = scraper.clear_all_specials()

        # Run fresh scrape (uses its own sessions per store)
        results = scraper.scrape_all_stores()

        return {
            "status": "success",
            "cleared": deleted,
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rescrape failed: {str(e)}")


@router.get("/{special_id}", response_model=SpecialSchema)
def get_special(special_id: int, db: Session = Depends(get_db)):
    """Get a specific special by ID."""
    special = db.query(Special).join(Store).filter(Special.id == special_id).first()
    if not special:
        raise HTTPException(status_code=404, detail="Special not found")

    return SpecialSchema(
        id=special.id,
        name=special.name,
        brand=special.brand,
        size=special.size,
        category=special.category,
        price=special.price,
        was_price=special.was_price,
        discount_percent=special.discount_percent,
        unit_price=special.unit_price,
        store_product_id=special.store_product_id,
        product_url=special.product_url,
        image_url=special.image_url,
        valid_from=special.valid_from,
        valid_to=special.valid_to,
        store_id=special.store_id,
        store_name=special.store.name,
        store_slug=special.store.slug,
        scraped_at=special.scraped_at,
        created_at=special.created_at,
    )
