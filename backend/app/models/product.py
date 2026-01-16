from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)  # Canonical name
    brand = Column(String(100))
    category_id = Column(Integer, ForeignKey("categories.id"))
    unit = Column(String(50))  # 'kg', 'L', 'each', '100g'
    size = Column(String(50))  # '2L', '500g', etc.
    barcode = Column(String(50), index=True)
    image_url = Column(String(500))
    is_key_product = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    category = relationship("Category", back_populates="products")
    store_products = relationship("StoreProduct", back_populates="product")
    alerts = relationship("Alert", back_populates="product")
