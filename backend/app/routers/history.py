"""
Price history router for viewing historical price data.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from decimal import Decimal

from ..database import get_db
from .auth import get_current_user, require_premium
from ..models import Product, Price, Store, User, StoreProduct

router = APIRouter(prefix="/history", tags=["history"])


# Schemas
class PricePoint(BaseModel):
    date: str
    price: float
    is_special: bool
    store_name: str
    store_slug: str


class PriceHistoryResponse(BaseModel):
    product_id: int
    product_name: str
    product_brand: Optional[str]
    history: list[PricePoint]
    stats: dict


@router.get("/{product_id}", response_model=PriceHistoryResponse)
async def get_price_history(
    product_id: int,
    days: int = Query(90, ge=7, le=365, description="Number of days of history"),
    store_id: Optional[int] = Query(None, description="Filter by store"),
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db)
):
    """Get price history for a product. Premium feature."""
    # Get product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Build query through StoreProduct
    query = db.query(Price, StoreProduct, Store).join(
        StoreProduct, Price.store_product_id == StoreProduct.id
    ).join(
        Store, StoreProduct.store_id == Store.id
    ).filter(
        StoreProduct.product_id == product_id,
        Price.recorded_at >= start_date
    )

    if store_id:
        query = query.filter(StoreProduct.store_id == store_id)

    results = query.order_by(Price.recorded_at).all()

    # Build history list
    history = [
        PricePoint(
            date=price.recorded_at.strftime("%Y-%m-%d"),
            price=float(price.price),
            is_special=price.is_special or False,
            store_name=store.name,
            store_slug=store.slug
        )
        for price, sp, store in results
    ]

    # Calculate stats
    if results:
        price_values = [float(price.price) for price, sp, store in results]

        # Get current prices (most recent per store)
        recent_query = db.query(Price, StoreProduct).join(
            StoreProduct, Price.store_product_id == StoreProduct.id
        ).filter(
            StoreProduct.product_id == product_id
        ).order_by(desc(Price.recorded_at))

        recent_results = recent_query.all()
        seen_stores = set()
        current_prices = []
        for price, sp in recent_results:
            if sp.store_id not in seen_stores:
                current_prices.append(float(price.price))
                seen_stores.add(sp.store_id)

        current_min = min(current_prices) if current_prices else None
        current_max = max(current_prices) if current_prices else None

        stats = {
            "min_price": min(price_values),
            "max_price": max(price_values),
            "avg_price": round(sum(price_values) / len(price_values), 2),
            "current_min": current_min,
            "current_max": current_max,
            "price_points": len(results),
            "special_count": sum(1 for price, sp, store in results if price.is_special),
        }
    else:
        stats = {
            "min_price": None,
            "max_price": None,
            "avg_price": None,
            "current_min": None,
            "current_max": None,
            "price_points": 0,
            "special_count": 0,
        }

    return PriceHistoryResponse(
        product_id=product.id,
        product_name=product.name,
        product_brand=product.brand,
        history=history,
        stats=stats
    )


@router.get("/{product_id}/summary")
async def get_price_summary(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a quick price summary (available to all users, limited data)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get 30-day stats
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_query = db.query(Price, StoreProduct).join(
        StoreProduct, Price.store_product_id == StoreProduct.id
    ).filter(
        StoreProduct.product_id == product_id,
        Price.recorded_at >= thirty_days_ago
    ).order_by(desc(Price.recorded_at))

    recent_results = recent_query.all()

    if recent_results:
        price_values = [float(price.price) for price, sp in recent_results]
        min_30d = min(price_values)
        max_30d = max(price_values)
        avg_30d = round(sum(price_values) / len(price_values), 2)

        # Get current prices (most recent per store)
        seen_stores = set()
        current_prices = []
        has_special = False
        for price, sp in recent_results:
            if sp.store_id not in seen_stores:
                current_prices.append(float(price.price))
                seen_stores.add(sp.store_id)
                if price.is_special:
                    has_special = True

        current_min = min(current_prices) if current_prices else None
        current_max = max(current_prices) if current_prices else None
    else:
        min_30d = max_30d = avg_30d = None
        current_min = current_max = None
        has_special = False

    # Determine price trend
    trend = "stable"
    if current_min and min_30d:
        if current_min < min_30d * 0.95:
            trend = "down"
        elif current_min > min_30d * 1.05:
            trend = "up"

    return {
        "product_id": product.id,
        "current_min": current_min,
        "current_max": current_max,
        "avg_30d": avg_30d,
        "min_30d": min_30d,
        "max_30d": max_30d,
        "trend": trend,
        "has_special": has_special,
    }


@router.get("/{product_id}/chart-data")
async def get_chart_data(
    product_id: int,
    days: int = Query(90, ge=7, le=365),
    current_user: User = Depends(require_premium),
    db: Session = Depends(get_db)
):
    """Get aggregated chart data for a product by store. Premium feature."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Get all stores
    stores = db.query(Store).all()

    # Get prices grouped by date and store
    results = db.query(Price, StoreProduct, Store).join(
        StoreProduct, Price.store_product_id == StoreProduct.id
    ).join(
        Store, StoreProduct.store_id == Store.id
    ).filter(
        StoreProduct.product_id == product_id,
        Price.recorded_at >= start_date
    ).order_by(Price.recorded_at).all()

    # Group by date
    date_data = {}
    for price, sp, store in results:
        date_str = price.recorded_at.strftime("%Y-%m-%d")
        if date_str not in date_data:
            date_data[date_str] = {"date": date_str}
        date_data[date_str][store.slug] = float(price.price)
        if price.is_special:
            date_data[date_str][f"{store.slug}_special"] = True

    # Convert to list sorted by date
    chart_data = sorted(date_data.values(), key=lambda x: x["date"])

    # Get store info
    store_info = [
        {"slug": s.slug, "name": s.name, "color": get_store_color(s.slug)}
        for s in stores
    ]

    return {
        "product_name": product.name,
        "product_brand": product.brand,
        "data": chart_data,
        "stores": store_info,
    }


def get_store_color(slug: str) -> str:
    """Get the color for a store."""
    colors = {
        "woolworths": "#00A651",
        "coles": "#E01A22",
        "aldi": "#00448C",
    }
    return colors.get(slug, "#666666")
