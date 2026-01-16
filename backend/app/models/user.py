from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    display_name = Column(String(100))
    hashed_password = Column(String(255))  # Optional - for registered users
    is_anonymous = Column(Boolean, default=True)
    reputation_score = Column(Integer, default=0)
    submissions_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Subscription fields
    stripe_customer_id = Column(String(100), unique=True, nullable=True)
    subscription_status = Column(String(20), default="free")  # free, active, cancelled, past_due
    subscription_ends_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    submitted_prices = relationship("Price", back_populates="source_user")
    verifications = relationship("PriceVerification", back_populates="user")
    alerts = relationship("Alert", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
