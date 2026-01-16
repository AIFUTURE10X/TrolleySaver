from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Date, Numeric, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Price(Base):
    __tablename__ = "prices"

    id = Column(Integer, primary_key=True, index=True)
    store_product_id = Column(Integer, ForeignKey("store_products.id"), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    unit_price = Column(Numeric(10, 4))  # Price per unit (kg/L/100g)
    was_price = Column(Numeric(10, 2))  # Original price if on special
    is_special = Column(Boolean, default=False, index=True)
    special_type = Column(String(50))  # 'half_price', 'multi_buy', etc.
    special_ends = Column(Date)
    source = Column(String(50), nullable=False)  # 'catalogue', 'user', 'manual'
    source_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_count = Column(Integer, default=0)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    valid_from = Column(Date)
    valid_to = Column(Date)

    # Indexes
    __table_args__ = (
        Index("idx_prices_store_product_recorded", "store_product_id", "recorded_at"),
    )

    # Relationships
    store_product = relationship("StoreProduct", back_populates="prices")
    source_user = relationship("User", back_populates="submitted_prices")
    verifications = relationship("PriceVerification", back_populates="price")


class PriceVerification(Base):
    __tablename__ = "price_verifications"

    id = Column(Integer, primary_key=True, index=True)
    price_id = Column(Integer, ForeignKey("prices.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    verified_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    price = relationship("Price", back_populates="verifications")
    user = relationship("User", back_populates="verifications")
