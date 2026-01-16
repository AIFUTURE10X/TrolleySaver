from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal


class ProductBase(BaseModel):
    name: str
    brand: str | None = None
    category_id: int | None = None
    unit: str | None = None
    size: str | None = None
    barcode: str | None = None
    image_url: str | None = None
    is_key_product: bool = False


class ProductCreate(ProductBase):
    pass


class Product(ProductBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProductSearch(BaseModel):
    query: str
    category_id: int | None = None
    limit: int = 20


class ProductWithPrices(Product):
    """Product with current prices from all stores."""
    prices: list["StorePriceInfo"] = []


class StorePriceInfo(BaseModel):
    store_id: int
    store_name: str
    store_slug: str
    price: Decimal
    unit_price: Decimal | None = None
    was_price: Decimal | None = None
    is_special: bool = False
    special_type: str | None = None
    recorded_at: datetime
    image_url: str | None = None  # Store CDN image URL

    class Config:
        from_attributes = True


# Update forward reference
ProductWithPrices.model_rebuild()
