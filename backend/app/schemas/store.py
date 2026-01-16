from pydantic import BaseModel
from datetime import datetime


class StoreBase(BaseModel):
    name: str
    slug: str
    logo_url: str | None = None
    website_url: str | None = None
    catalogue_url: str | None = None
    specials_day: str | None = None


class StoreCreate(StoreBase):
    pass


class Store(StoreBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
