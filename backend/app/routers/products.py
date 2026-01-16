from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func, desc
from app.database import get_db
from app.models import Product, Category, Price, Store, StoreProduct
from app.schemas.product import Product as ProductSchema, ProductCreate, ProductWithPrices, StorePriceInfo

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=list[ProductSchema])
def list_products(
    skip: int = 0,
    limit: int = 100,
    category_id: int | None = None,
    key_only: bool = False,
    db: Session = Depends(get_db)
):
    """List all products with optional filters."""
    query = db.query(Product)

    if category_id:
        query = query.filter(Product.category_id == category_id)

    if key_only:
        query = query.filter(Product.is_key_product == True)

    return query.offset(skip).limit(limit).all()


@router.get("/search", response_model=list[ProductSchema])
def search_products(
    q: str = Query(..., min_length=2),
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Search products by name or brand."""
    query = db.query(Product).filter(
        or_(
            Product.name.ilike(f"%{q}%"),
            Product.brand.ilike(f"%{q}%")
        )
    )
    return query.limit(limit).all()


@router.get("/key", response_model=list[ProductSchema])
def get_key_products(db: Session = Depends(get_db)):
    """Get all key (tracked) products."""
    return db.query(Product).filter(Product.is_key_product == True).all()


@router.get("/with-prices", response_model=list[ProductWithPrices])
def list_products_with_prices(
    skip: int = 0,
    limit: int = 50,
    category_id: int | None = None,
    search: str | None = None,
    specials_only: bool = False,
    db: Session = Depends(get_db)
):
    """List products with current prices from all stores."""
    # Build base query
    query = db.query(Product)

    if category_id:
        query = query.filter(Product.category_id == category_id)

    if search:
        query = query.filter(
            or_(
                Product.name.ilike(f"%{search}%"),
                Product.brand.ilike(f"%{search}%")
            )
        )

    # Get products
    products = query.offset(skip).limit(limit).all()
    product_ids = [p.id for p in products]

    if not product_ids:
        return []

    # Get store products and their latest prices
    # Using subquery to get latest price per store_product
    from sqlalchemy.orm import aliased
    from sqlalchemy import and_

    # Get all store products for these products
    store_products = db.query(StoreProduct).filter(
        StoreProduct.product_id.in_(product_ids)
    ).options(joinedload(StoreProduct.store)).all()

    # Group store_products by product_id
    sp_map: dict[int, list] = {}
    for sp in store_products:
        if sp.product_id not in sp_map:
            sp_map[sp.product_id] = []
        sp_map[sp.product_id].append(sp)

    # Get latest prices for all store products
    sp_ids = [sp.id for sp in store_products]
    if not sp_ids:
        # No store products, return products without prices
        return [
            ProductWithPrices(
                id=product.id,
                name=product.name,
                brand=product.brand,
                category_id=product.category_id,
                unit=product.unit,
                size=product.size,
                barcode=product.barcode,
                image_url=product.image_url,
                is_key_product=product.is_key_product,
                created_at=product.created_at,
                prices=[]
            )
            for product in products
        ]

    # For each store_product, get the latest price
    # Using a more efficient approach: get all recent prices and filter in Python
    from datetime import datetime, timedelta
    recent_cutoff = datetime.utcnow() - timedelta(days=30)

    prices_query = db.query(Price).filter(
        Price.store_product_id.in_(sp_ids),
        Price.recorded_at >= recent_cutoff
    )

    if specials_only:
        prices_query = prices_query.filter(Price.is_special == True)

    all_prices = prices_query.order_by(desc(Price.recorded_at)).all()

    # Get latest price per store_product
    latest_prices: dict[int, Price] = {}
    for price in all_prices:
        if price.store_product_id not in latest_prices:
            latest_prices[price.store_product_id] = price

    # Build price map by product_id
    price_map: dict[int, list] = {}
    for sp in store_products:
        if sp.id in latest_prices:
            price = latest_prices[sp.id]
            if sp.product_id not in price_map:
                price_map[sp.product_id] = []
            price_map[sp.product_id].append(StorePriceInfo(
                store_id=sp.store_id,
                store_name=sp.store.name,
                store_slug=sp.store.slug,
                price=price.price,
                unit_price=price.unit_price,
                was_price=price.was_price,
                is_special=price.is_special or False,
                special_type=price.special_type,
                recorded_at=price.recorded_at,
                image_url=sp.image_url  # Store CDN image
            ))

    # Build response
    result = []
    for product in products:
        product_prices = price_map.get(product.id, [])
        # Only include products that have at least one price (or include all if not specials_only)
        if not specials_only or product_prices:
            result.append(ProductWithPrices(
                id=product.id,
                name=product.name,
                brand=product.brand,
                category_id=product.category_id,
                unit=product.unit,
                size=product.size,
                barcode=product.barcode,
                image_url=product.image_url,
                is_key_product=product.is_key_product,
                created_at=product.created_at,
                prices=product_prices
            ))

    return result


@router.get("/search-with-prices", response_model=list[ProductWithPrices])
def search_products_with_prices(
    q: str = Query(..., min_length=2),
    limit: int = 30,
    db: Session = Depends(get_db)
):
    """Search products by name or brand and return with all store prices."""
    from datetime import datetime, timedelta

    # Search products
    products = db.query(Product).filter(
        or_(
            Product.name.ilike(f"%{q}%"),
            Product.brand.ilike(f"%{q}%")
        )
    ).limit(limit).all()

    if not products:
        return []

    product_ids = [p.id for p in products]

    # Get all store products for these products
    store_products = db.query(StoreProduct).filter(
        StoreProduct.product_id.in_(product_ids)
    ).options(joinedload(StoreProduct.store)).all()

    sp_ids = [sp.id for sp in store_products]
    if not sp_ids:
        # No store products, return products without prices
        return [
            ProductWithPrices(
                id=product.id,
                name=product.name,
                brand=product.brand,
                category_id=product.category_id,
                unit=product.unit,
                size=product.size,
                barcode=product.barcode,
                image_url=product.image_url,
                is_key_product=product.is_key_product,
                created_at=product.created_at,
                prices=[]
            )
            for product in products
        ]

    # Get recent prices
    recent_cutoff = datetime.utcnow() - timedelta(days=30)
    all_prices = db.query(Price).filter(
        Price.store_product_id.in_(sp_ids),
        Price.recorded_at >= recent_cutoff
    ).order_by(desc(Price.recorded_at)).all()

    # Get latest price per store_product
    latest_prices: dict[int, Price] = {}
    for price in all_prices:
        if price.store_product_id not in latest_prices:
            latest_prices[price.store_product_id] = price

    # Build price map by product_id
    price_map: dict[int, list] = {}
    for sp in store_products:
        if sp.id in latest_prices:
            price = latest_prices[sp.id]
            if sp.product_id not in price_map:
                price_map[sp.product_id] = []
            price_map[sp.product_id].append(StorePriceInfo(
                store_id=sp.store_id,
                store_name=sp.store.name,
                store_slug=sp.store.slug,
                price=price.price,
                unit_price=price.unit_price,
                was_price=price.was_price,
                is_special=price.is_special or False,
                special_type=price.special_type,
                recorded_at=price.recorded_at,
                image_url=sp.image_url  # Store CDN image
            ))

    # Build response - sort by products with most prices first
    result = []
    for product in products:
        product_prices = price_map.get(product.id, [])
        result.append(ProductWithPrices(
            id=product.id,
            name=product.name,
            brand=product.brand,
            category_id=product.category_id,
            unit=product.unit,
            size=product.size,
            barcode=product.barcode,
            image_url=product.image_url,
            is_key_product=product.is_key_product,
            created_at=product.created_at,
            prices=product_prices
        ))

    # Sort: products with more prices first, then by name
    result.sort(key=lambda x: (-len(x.prices), x.name))

    return result


@router.get("/{product_id}", response_model=ProductSchema)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a specific product by ID."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("/", response_model=ProductSchema)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """Create a new product."""
    db_product = Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product
