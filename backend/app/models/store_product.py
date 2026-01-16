from sqlalchemy import Column, Integer, String, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class StoreProduct(Base):
    __tablename__ = "store_products"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    store_product_id = Column(String(100))  # Store's internal ID (stockcode)
    store_product_name = Column(String(255))  # Name as shown in store
    product_url = Column(Text)
    image_url = Column(String(500))  # Store CDN image URL

    # Unique constraint on product + store
    __table_args__ = (
        UniqueConstraint("product_id", "store_id", name="uq_store_product"),
    )

    # Relationships
    product = relationship("Product", back_populates="store_products")
    store = relationship("Store", back_populates="store_products")
    prices = relationship("Price", back_populates="store_product")
