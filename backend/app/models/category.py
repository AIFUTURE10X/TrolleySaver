from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # 'Dairy', 'Meat', 'Cleaning'
    slug = Column(String(100), unique=True, nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    display_order = Column(Integer, default=0)  # For consistent ordering
    icon = Column(String(50), nullable=True)  # Icon identifier (e.g., 'apple', 'milk')

    # Self-referential relationship for subcategories
    parent = relationship("Category", remote_side=[id], backref="subcategories")

    # Relationship to products
    products = relationship("Product", back_populates="category")
