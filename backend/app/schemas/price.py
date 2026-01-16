from pydantic import BaseModel
from datetime import datetime, date
from decimal import Decimal


class PriceBase(BaseModel):
    price: Decimal
    unit_price: Decimal | None = None
    was_price: Decimal | None = None
    is_special: bool = False
    special_type: str | None = None
    special_ends: date | None = None


class PriceCreate(PriceBase):
    store_product_id: int
    source: str = "manual"
    valid_from: date | None = None
    valid_to: date | None = None


class Price(PriceBase):
    id: int
    store_product_id: int
    source: str
    verified_count: int
    recorded_at: datetime

    class Config:
        from_attributes = True


class PriceSubmission(BaseModel):
    """Schema for user price submissions."""
    product_id: int
    store_id: int
    price: Decimal
    was_price: Decimal | None = None
    is_special: bool = False
    special_type: str | None = None


class PriceComparison(BaseModel):
    """Comparison of a product across stores."""
    product_id: int
    product_name: str
    stores: list["StorePrice"]
    cheapest_store: str | None = None
    price_difference: Decimal | None = None


class StorePrice(BaseModel):
    store_id: int
    store_name: str
    store_slug: str
    price: Decimal
    unit_price: Decimal | None = None
    is_special: bool = False
    was_price: Decimal | None = None
    savings: Decimal | None = None

    class Config:
        from_attributes = True


class SpecialItem(BaseModel):
    """A product currently on special."""
    product_id: int
    product_name: str
    brand: str | None = None
    category: str | None = None
    store_id: int
    store_name: str
    price: Decimal
    was_price: Decimal | None = None
    discount_percent: int | None = None
    special_type: str | None = None
    valid_until: date | None = None

    class Config:
        from_attributes = True


# ============== Category Comparison Schemas ==============

class BrandPriceInfo(BaseModel):
    """Price info for a single brand across all stores."""
    product_id: int
    brand: str | None = None
    product_name: str
    image_url: str | None = None
    store_prices: list["StorePrice"]
    cheapest_price: Decimal | None = None
    cheapest_store: str | None = None


class CategoryComparison(BaseModel):
    """Comparison of all brands for a product type."""
    product_type: str  # e.g., "Full Cream Milk 2L"
    size: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    brands: list[BrandPriceInfo]  # All brands with their store prices, sorted by cheapest
    cheapest_overall: Decimal | None = None
    cheapest_brand: str | None = None
    cheapest_store: str | None = None
    total_options: int = 0


class ProductTypeSuggestion(BaseModel):
    """Suggestion for product type search."""
    product_type: str
    size: str | None = None
    sample_product_id: int
    brand_count: int
    category_id: int | None = None


# ============== Specials Comparison Schemas ==============

class SpecialStorePrice(BaseModel):
    """Price info for a special at a specific store."""
    special_id: int
    store_id: int
    store_name: str
    store_slug: str
    price: Decimal
    was_price: Decimal | None = None
    discount_percent: int | None = None
    unit_price: str | None = None
    image_url: str | None = None
    product_url: str | None = None
    valid_to: date | None = None


class BrandMatchResult(BaseModel):
    """Result of matching identical products across stores."""
    product_name: str
    brand: str | None = None
    size: str | None = None
    stores: list[SpecialStorePrice]
    cheapest_store: str | None = None
    price_spread: Decimal | None = None  # Difference between highest and lowest
    savings_potential: Decimal | None = None  # How much you'd save vs most expensive


class TypeMatchResult(BaseModel):
    """Result of matching similar product types across stores/brands."""
    product_type: str  # e.g., "Milk 2L", "Chocolate 180g"
    category_id: int | None = None
    category_name: str | None = None
    reference_product: SpecialStorePrice
    similar_products: list[SpecialStorePrice]  # Sorted by price ascending
    cheapest_option: str | None = None  # Product name
    cheapest_price: Decimal | None = None
    total_options: int = 0


# ============== Fresh Foods Schemas ==============

class FreshFoodStorePrice(BaseModel):
    """Price info for a fresh food item at a specific store."""
    store_id: int
    store_name: str
    store_slug: str
    price: Decimal
    unit_price: str | None = None  # e.g., "$2.90/kg"
    image_url: str | None = None
    product_url: str | None = None


class FreshFoodItem(BaseModel):
    """A fresh food item with prices across stores."""
    product_id: int
    product_name: str
    brand: str | None = None
    size: str | None = None
    category: str  # "produce" or "meat"
    stores: list[FreshFoodStorePrice]
    cheapest_store: str | None = None
    cheapest_price: Decimal | None = None
    price_range: str | None = None  # e.g., "$2.90 - $4.50"


class FreshFoodsResponse(BaseModel):
    """Response for fresh foods comparison."""
    produce: list[FreshFoodItem]
    meat: list[FreshFoodItem]
    total_products: int
    last_updated: str | None = None


# Update forward references
PriceComparison.model_rebuild()
BrandPriceInfo.model_rebuild()
CategoryComparison.model_rebuild()
