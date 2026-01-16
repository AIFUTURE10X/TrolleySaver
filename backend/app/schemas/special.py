from pydantic import BaseModel
from datetime import datetime, date
from decimal import Decimal


class SpecialBase(BaseModel):
    name: str
    brand: str | None = None
    size: str | None = None
    category: str | None = None
    price: Decimal
    was_price: Decimal | None = None
    discount_percent: int | None = None
    unit_price: str | None = None
    store_product_id: str | None = None
    product_url: str | None = None
    image_url: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None


class SpecialCreate(SpecialBase):
    store_id: int


class Special(SpecialBase):
    id: int
    store_id: int
    store_name: str | None = None
    store_slug: str | None = None
    scraped_at: datetime | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class SpecialsList(BaseModel):
    items: list[Special]
    total: int
    page: int
    limit: int
    has_more: bool


class SpecialsStats(BaseModel):
    total_specials: int
    by_store: dict[str, int]
    half_price_count: int
    last_updated: datetime | None


class CategoryCount(BaseModel):
    name: str
    count: int


class SubcategoryItem(BaseModel):
    id: int
    name: str
    slug: str
    count: int


class CategoryTreeItem(BaseModel):
    id: int
    name: str
    slug: str
    icon: str | None = None
    count: int
    subcategories: list[SubcategoryItem] = []


class CategoryTreeResponse(BaseModel):
    categories: list[CategoryTreeItem]
    total_categorized: int
    total_uncategorized: int


class ScrapeLogResponse(BaseModel):
    id: int
    store_id: int | None
    store_name: str | None = None
    started_at: datetime | None
    completed_at: datetime | None
    items_found: int | None
    status: str | None
    error_message: str | None = None

    class Config:
        from_attributes = True
