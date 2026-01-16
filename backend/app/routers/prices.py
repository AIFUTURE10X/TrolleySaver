from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from app.database import get_db
from app.models import Price, StoreProduct, Product, Store
from app.schemas.price import Price as PriceSchema, SpecialItem

router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("/latest/{product_id}")
def get_latest_prices(product_id: int, db: Session = Depends(get_db)):
    """Get the latest price for a product from each store."""
    # Get all store products for this product
    store_products = db.query(StoreProduct).filter(
        StoreProduct.product_id == product_id
    ).all()

    if not store_products:
        raise HTTPException(status_code=404, detail="Product not found in any store")

    result = []
    for sp in store_products:
        # Get latest price for this store product
        latest_price = db.query(Price).filter(
            Price.store_product_id == sp.id
        ).order_by(desc(Price.recorded_at)).first()

        if latest_price:
            store = db.query(Store).filter(Store.id == sp.store_id).first()
            result.append({
                "store_id": store.id,
                "store_name": store.name,
                "store_slug": store.slug,
                "price": float(latest_price.price),
                "unit_price": float(latest_price.unit_price) if latest_price.unit_price else None,
                "was_price": float(latest_price.was_price) if latest_price.was_price else None,
                "is_special": latest_price.is_special,
                "special_type": latest_price.special_type,
                "recorded_at": latest_price.recorded_at
            })

    return result


@router.get("/history/{product_id}")
def get_price_history(
    product_id: int,
    store_id: int | None = None,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get price history for a product."""
    from datetime import datetime, timedelta

    query = db.query(Price, StoreProduct, Store).join(
        StoreProduct, Price.store_product_id == StoreProduct.id
    ).join(
        Store, StoreProduct.store_id == Store.id
    ).filter(
        StoreProduct.product_id == product_id
    ).filter(
        Price.recorded_at >= datetime.now() - timedelta(days=days)
    )

    if store_id:
        query = query.filter(StoreProduct.store_id == store_id)

    results = query.order_by(Price.recorded_at).all()

    return [
        {
            "store_name": store.name,
            "price": float(price.price),
            "is_special": price.is_special,
            "recorded_at": price.recorded_at
        }
        for price, sp, store in results
    ]


@router.get("/specials", response_model=list[SpecialItem])
def get_all_specials(
    limit: int = 50,
    category_id: int | None = None,
    db: Session = Depends(get_db)
):
    """Get all current specials across all stores."""
    query = db.query(Price, StoreProduct, Product, Store).join(
        StoreProduct, Price.store_product_id == StoreProduct.id
    ).join(
        Product, StoreProduct.product_id == Product.id
    ).join(
        Store, StoreProduct.store_id == Store.id
    ).filter(
        Price.is_special == True
    )

    if category_id:
        query = query.filter(Product.category_id == category_id)

    # Get most recent specials
    results = query.order_by(desc(Price.recorded_at)).limit(limit).all()

    specials = []
    for price, sp, product, store in results:
        discount_percent = None
        if price.was_price and price.price:
            discount_percent = int(
                ((float(price.was_price) - float(price.price)) / float(price.was_price)) * 100
            )

        specials.append(SpecialItem(
            product_id=product.id,
            product_name=product.name,
            brand=product.brand,
            category=None,  # Would need to join category
            store_id=store.id,
            store_name=store.name,
            price=price.price,
            was_price=price.was_price,
            discount_percent=discount_percent,
            special_type=price.special_type,
            valid_until=price.special_ends
        ))

    return specials


@router.get("/specials/{store_slug}", response_model=list[SpecialItem])
def get_store_specials(
    store_slug: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get current specials for a specific store."""
    store = db.query(Store).filter(Store.slug == store_slug).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    results = db.query(Price, StoreProduct, Product).join(
        StoreProduct, Price.store_product_id == StoreProduct.id
    ).join(
        Product, StoreProduct.product_id == Product.id
    ).filter(
        StoreProduct.store_id == store.id,
        Price.is_special == True
    ).order_by(desc(Price.recorded_at)).limit(limit).all()

    specials = []
    for price, sp, product in results:
        discount_percent = None
        if price.was_price and price.price:
            discount_percent = int(
                ((float(price.was_price) - float(price.price)) / float(price.was_price)) * 100
            )

        specials.append(SpecialItem(
            product_id=product.id,
            product_name=product.name,
            brand=product.brand,
            category=None,
            store_id=store.id,
            store_name=store.name,
            price=price.price,
            was_price=price.was_price,
            discount_percent=discount_percent,
            special_type=price.special_type,
            valid_until=price.special_ends
        ))

    return specials
