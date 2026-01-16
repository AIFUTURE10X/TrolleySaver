from sqlalchemy import Column, Integer, String, DateTime, Text, Numeric, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Special(Base):
    """Weekly special/discounted product from a store."""
    __tablename__ = "specials"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)

    # Product info
    name = Column(String(255), nullable=False)
    brand = Column(String(100))
    size = Column(String(50))
    category = Column(String(100), index=True)  # Original scraped category string
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True, index=True)  # FK to unified categories

    # Pricing
    price = Column(Numeric(10, 2), nullable=False)
    was_price = Column(Numeric(10, 2))
    discount_percent = Column(Integer, index=True)  # ((was_price - price) / was_price * 100)
    unit_price = Column(String(50))  # "$2.50 per 100g"

    # Store reference
    store_product_id = Column(String(100))  # Stockcode for image URL
    product_url = Column(Text)
    image_url = Column(String(500))

    # Validity
    valid_from = Column(Date)
    valid_to = Column(Date, index=True)

    # Metadata
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    store = relationship("Store", back_populates="specials")
    category_rel = relationship("Category", backref="specials")

    # Unique constraint: one entry per product per store per week
    __table_args__ = (
        UniqueConstraint('store_id', 'store_product_id', 'valid_from', name='uq_special_store_product_week'),
    )


class ScrapeLog(Base):
    """Log of scraping runs for monitoring."""
    __tablename__ = "scrape_logs"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    items_found = Column(Integer, default=0)
    status = Column(String(20))  # 'success', 'failed', 'partial'
    error_message = Column(Text)

    # Relationships
    store = relationship("Store")
