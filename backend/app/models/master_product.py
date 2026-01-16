"""
Master Product model - permanent product catalog.

Products are stored once and never deleted. Only prices change weekly.
This eliminates duplicate product data and enables efficient image caching.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, UniqueConstraint, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class MasterProduct(Base):
    """
    Permanent product catalog entry.

    Each product exists once per store, identified by stockcode.
    Product info (name, brand, image) rarely changes.
    """
    __tablename__ = "master_products"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)

    # Unique identifier from store (stockcode/product ID)
    stockcode = Column(String(100), nullable=False)

    # Product info (permanent, rarely changes)
    name = Column(String(255), nullable=False, index=True)
    brand = Column(String(100), index=True)
    size = Column(String(50))
    category = Column(String(100), index=True)

    # URLs
    product_url = Column(Text)
    original_image_url = Column(String(500))  # Original CDN URL

    # Local image cache path (e.g., "/images/woolworths/123456.jpg")
    local_image_path = Column(String(255))
    image_cached = Column(Boolean, default=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    store = relationship("Store", back_populates="master_products")
    prices = relationship("ProductPrice", back_populates="product", cascade="all, delete-orphan")

    # Unique constraint: one product per stockcode per store
    __table_args__ = (
        UniqueConstraint('store_id', 'stockcode', name='uq_master_product_store_stockcode'),
        Index('ix_master_products_store_category', 'store_id', 'category'),
        Index('ix_master_products_name_search', 'name'),
    )

    @property
    def image_url(self):
        """Return local cached image or fallback to original CDN."""
        if self.image_cached and self.local_image_path:
            return f"/static{self.local_image_path}"
        return self.original_image_url


class ProductPrice(Base):
    """
    Weekly price record for a product.

    Each week creates new price entries for products on special.
    Historical prices are preserved for analytics.
    """
    __tablename__ = "product_prices"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("master_products.id", ondelete="CASCADE"), nullable=False)

    # Pricing
    price = Column(String(20), nullable=False)  # Store as string to preserve formatting
    price_numeric = Column(Integer, nullable=False)  # Price in cents for sorting/filtering
    was_price = Column(String(20))
    was_price_numeric = Column(Integer)  # Was price in cents
    discount_percent = Column(Integer, nullable=False, index=True)
    unit_price = Column(String(50))  # "$2.50 per 100g"

    # Validity period
    valid_from = Column(DateTime(timezone=True), nullable=False)
    valid_to = Column(DateTime(timezone=True), nullable=False, index=True)

    # Is this the current active price?
    is_current = Column(Boolean, default=True, index=True)

    # Timestamps
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    product = relationship("MasterProduct", back_populates="prices")

    __table_args__ = (
        # Index for fast "current specials" queries
        Index('ix_product_prices_current_valid', 'is_current', 'valid_to'),
        # Index for product price history
        Index('ix_product_prices_product_date', 'product_id', 'valid_from'),
        # Index for discount filtering
        Index('ix_product_prices_discount', 'discount_percent', 'is_current'),
    )
