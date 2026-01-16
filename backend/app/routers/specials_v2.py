"""
Optimized Specials API v2

Performance improvements:
- Redis caching for all read operations
- Keyset pagination for consistent performance
- Optimized queries with proper indexing
- Compatible with existing specials table (migration-ready)

Note: Currently uses existing specials table for compatibility.
After running migration script, update queries to use MasterProduct + ProductPrice.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, desc, and_, inspect
from datetime import date, datetime, timedelta
from typing import Optional
import logging

from app.database import get_db
from app.models import Special, Store
from app.services.cache import cache, PREFIX_SPECIALS, PREFIX_STATS
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/specials", tags=["specials-v2"])

# Check if new tables exist (for migration status)
def _new_tables_exist(db: Session) -> bool:
    """Check if master_products table exists."""
    try:
        inspector = inspect(db.bind)
        return "master_products" in inspector.get_table_names()
    except Exception:
        return False


# Pydantic schemas for v2 API
class ProductV2(BaseModel):
    id: int
    stockcode: str
    name: str
    brand: Optional[str] = None
    size: Optional[str] = None
    category: Optional[str] = None
    image_url: str
    product_url: Optional[str] = None
    store_id: int
    store_name: str
    store_slug: str

    # Current price info
    price: str
    price_cents: int
    was_price: Optional[str] = None
    was_price_cents: Optional[int] = None
    discount_percent: int
    unit_price: Optional[str] = None
    valid_until: datetime

    class Config:
        from_attributes = True


class SpecialsListV2(BaseModel):
    items: list[ProductV2]
    total: int
    cursor: Optional[str] = None  # For keyset pagination
    has_more: bool


class StatsV2(BaseModel):
    total_specials: int
    by_store: dict[str, int]
    half_price_count: int
    products_with_images: int
    last_updated: Optional[datetime] = None


class CategoryCountV2(BaseModel):
    name: str
    count: int


@router.get("/", response_model=SpecialsListV2)
async def get_specials_v2(
    store: Optional[str] = Query(None, description="Filter by store slug"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_discount: int = Query(0, ge=0, le=100, description="Minimum discount percentage"),
    search: Optional[str] = Query(None, min_length=2, description="Search in product name/brand"),
    sort: str = Query("discount", description="Sort by: discount, price, name"),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get current specials with optimized queries and caching.

    Uses keyset pagination for consistent performance with large datasets.
    Currently uses existing specials table for backward compatibility.
    """
    today = date.today()

    # Try cache first
    cache_params = {
        "store": store, "category": category, "min_discount": min_discount,
        "search": search, "sort": sort, "cursor": cursor, "limit": limit
    }
    cached_result = await cache.get_specials(cache_params)
    if cached_result:
        return SpecialsListV2(**cached_result)

    # Build query using existing specials table
    query = (
        db.query(Special)
        .join(Store, Special.store_id == Store.id)
        .filter(Special.valid_to >= today)
    )

    # Apply filters
    if store:
        query = query.filter(Store.slug == store)

    if category:
        query = query.filter(Special.category == category)

    if min_discount > 0:
        query = query.filter(Special.discount_percent >= min_discount)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Special.name.ilike(search_term),
                Special.brand.ilike(search_term)
            )
        )

    # Get total count
    total = query.count()

    # Apply sorting with keyset pagination support
    if sort == "discount":
        query = query.order_by(desc(Special.discount_percent), Special.id)
        if cursor:
            try:
                cursor_discount, cursor_id = cursor.split(":")
                query = query.filter(
                    or_(
                        Special.discount_percent < int(cursor_discount),
                        and_(
                            Special.discount_percent == int(cursor_discount),
                            Special.id > int(cursor_id)
                        )
                    )
                )
            except ValueError:
                pass
    elif sort == "price":
        query = query.order_by(Special.price, Special.id)
        if cursor:
            try:
                cursor_price, cursor_id = cursor.split(":")
                query = query.filter(
                    or_(
                        Special.price > float(cursor_price),
                        and_(
                            Special.price == float(cursor_price),
                            Special.id > int(cursor_id)
                        )
                    )
                )
            except ValueError:
                pass
    else:  # name
        query = query.order_by(Special.name, Special.id)
        if cursor:
            try:
                cursor_name, cursor_id = cursor.split(":", 1)
                query = query.filter(
                    or_(
                        Special.name > cursor_name,
                        and_(
                            Special.name == cursor_name,
                            Special.id > int(cursor_id)
                        )
                    )
                )
            except ValueError:
                pass

    # Fetch one extra to check if there's more
    results = query.limit(limit + 1).all()
    has_more = len(results) > limit
    results = results[:limit]

    # Build response
    items = []
    next_cursor = None

    for special in results:
        # Get store info
        store_obj = db.query(Store).filter(Store.id == special.store_id).first()

        # Convert price to cents
        price_cents = int(float(special.price) * 100) if special.price else 0
        was_price_cents = int(float(special.was_price) * 100) if special.was_price else None

        item = ProductV2(
            id=special.id,
            stockcode=special.store_product_id or str(special.id),
            name=special.name,
            brand=special.brand,
            size=special.size,
            category=special.category,
            image_url=special.image_url or "",
            product_url=special.product_url,
            store_id=special.store_id,
            store_name=store_obj.name if store_obj else "Unknown",
            store_slug=store_obj.slug if store_obj else "unknown",
            price=f"${float(special.price):.2f}" if special.price else "$0.00",
            price_cents=price_cents,
            was_price=f"${float(special.was_price):.2f}" if special.was_price else None,
            was_price_cents=was_price_cents,
            discount_percent=special.discount_percent or 0,
            unit_price=special.unit_price,
            valid_until=datetime.combine(special.valid_to, datetime.min.time()) if special.valid_to else datetime.now()
        )
        items.append(item)

    # Generate cursor for next page
    if has_more and results:
        last = results[-1]
        if sort == "discount":
            next_cursor = f"{last.discount_percent}:{last.id}"
        elif sort == "price":
            next_cursor = f"{float(last.price):.2f}:{last.id}"
        else:
            next_cursor = f"{last.name}:{last.id}"

    response = SpecialsListV2(
        items=items,
        total=total,
        cursor=next_cursor,
        has_more=has_more
    )

    # Cache the response
    await cache.set_specials(cache_params, response.model_dump())

    return response


@router.get("/stats", response_model=StatsV2)
async def get_stats_v2(db: Session = Depends(get_db)):
    """Get summary statistics with caching."""
    # Try cache
    cached_result = await cache.get_stats()
    if cached_result:
        return StatsV2(**cached_result)

    today = date.today()

    # Total active specials
    total = (
        db.query(func.count(Special.id))
        .filter(Special.valid_to >= today)
        .scalar()
    )

    # Count by store
    store_counts = (
        db.query(Store.slug, func.count(Special.id))
        .join(Special, Special.store_id == Store.id)
        .filter(Special.valid_to >= today)
        .group_by(Store.slug)
        .all()
    )
    by_store = {slug: count for slug, count in store_counts}

    # Half price count
    half_price = (
        db.query(func.count(Special.id))
        .filter(
            Special.valid_to >= today,
            Special.discount_percent >= 50
        )
        .scalar()
    )

    # Count specials with images
    images_count = (
        db.query(func.count(Special.id))
        .filter(
            Special.valid_to >= today,
            Special.image_url.isnot(None)
        )
        .scalar()
    )

    # Last scrape time
    last_update = (
        db.query(func.max(Special.scraped_at))
        .scalar()
    )

    response = StatsV2(
        total_specials=total or 0,
        by_store=by_store,
        half_price_count=half_price or 0,
        products_with_images=images_count or 0,
        last_updated=last_update
    )

    # Cache
    await cache.set_stats(response.model_dump())

    return response


@router.get("/categories", response_model=list[CategoryCountV2])
async def get_categories_v2(db: Session = Depends(get_db)):
    """Get categories with counts, cached."""
    # Try cache
    cached_result = await cache.get_categories()
    if cached_result:
        return [CategoryCountV2(**c) for c in cached_result]

    today = date.today()

    categories = (
        db.query(Special.category, func.count(Special.id).label("count"))
        .filter(
            Special.valid_to >= today,
            Special.category.isnot(None)
        )
        .group_by(Special.category)
        .order_by(desc("count"))
        .all()
    )

    result = [CategoryCountV2(name=cat, count=count) for cat, count in categories if cat]

    # Cache
    await cache.set_categories([c.model_dump() for c in result])

    return result


@router.get("/stores")
async def get_stores_v2(db: Session = Depends(get_db)):
    """Get stores with special counts."""
    today = date.today()

    stores = db.query(Store).all()
    result = []

    for store in stores:
        count = (
            db.query(func.count(Special.id))
            .filter(
                Special.store_id == store.id,
                Special.valid_to >= today
            )
            .scalar()
        )

        result.append({
            "id": store.id,
            "name": store.name,
            "slug": store.slug,
            "logo_url": store.logo_url,
            "specials_count": count or 0
        })

    return result


@router.get("/product/{product_id}")
async def get_product_v2(product_id: int, db: Session = Depends(get_db)):
    """Get a single product/special details."""
    special = db.query(Special).filter(Special.id == product_id).first()

    if not special:
        raise HTTPException(status_code=404, detail="Product not found")

    store_obj = db.query(Store).filter(Store.id == special.store_id).first()

    return {
        "product": {
            "id": special.id,
            "stockcode": special.store_product_id or str(special.id),
            "name": special.name,
            "brand": special.brand,
            "size": special.size,
            "category": special.category,
            "image_url": special.image_url,
            "product_url": special.product_url,
            "store_name": store_obj.name if store_obj else "Unknown",
            "store_slug": store_obj.slug if store_obj else "unknown"
        },
        "current_price": {
            "price": f"${float(special.price):.2f}" if special.price else None,
            "was_price": f"${float(special.was_price):.2f}" if special.was_price else None,
            "discount_percent": special.discount_percent or 0,
            "valid_until": special.valid_to
        },
        "price_history": []  # Not available in current schema
    }


@router.post("/admin/invalidate-cache")
async def invalidate_cache():
    """Clear all specials caches (call after scraping)."""
    await cache.invalidate_specials()
    return {"status": "success", "message": "Cache invalidated"}
