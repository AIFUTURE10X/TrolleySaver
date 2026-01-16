from pydantic import BaseModel


class CategoryBase(BaseModel):
    name: str
    slug: str
    parent_id: int | None = None


class CategoryCreate(CategoryBase):
    pass


class Category(CategoryBase):
    id: int

    class Config:
        from_attributes = True
