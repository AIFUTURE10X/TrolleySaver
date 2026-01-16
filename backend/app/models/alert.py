"""
Models for price alerts and notifications.
"""
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Numeric, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Alert(Base):
    """A user's watch on a product for price alerts."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    # Alert type and settings
    alert_type = Column(String(50), nullable=False)  # 'price_drop', 'special', 'threshold'
    threshold_price = Column(Numeric(10, 2))  # Trigger when price below this
    notify_any_drop = Column(Boolean, default=True)  # Alert on any price drop
    notify_special = Column(Boolean, default=True)  # Alert when item goes on special

    # Status
    is_active = Column(Boolean, default=True)
    last_notified_at = Column(DateTime(timezone=True), nullable=True)
    last_price_seen = Column(Numeric(10, 2), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="alerts")
    product = relationship("Product", back_populates="alerts")
    alert_notifications = relationship("AlertNotification", back_populates="alert")


class AlertNotification(Base):
    """Record of an alert being triggered."""
    __tablename__ = "alert_notifications"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False)
    price_id = Column(Integer, ForeignKey("prices.id"), nullable=False)

    # Notification details
    old_price = Column(Numeric(10, 2), nullable=True)
    new_price = Column(Numeric(10, 2), nullable=True)

    # Status
    sent_email = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True))
    read_at = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    alert = relationship("Alert", back_populates="alert_notifications")


class Notification(Base):
    """A general notification for a user (in-app notifications)."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Notification content
    type = Column(String(50), nullable=False)  # 'price_drop', 'new_special', 'threshold_reached', 'welcome'
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    data = Column(JSON, nullable=True)  # Additional data like product_id, old_price, new_price

    # Status
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="notifications")
