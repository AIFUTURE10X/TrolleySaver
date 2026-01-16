from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr | None = None
    display_name: str | None = None


class UserCreate(UserBase):
    password: str | None = None  # Optional for anonymous users


class User(UserBase):
    id: int
    is_anonymous: bool
    reputation_score: int
    submissions_count: int
    created_at: datetime

    class Config:
        from_attributes = True
