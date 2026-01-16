from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)  # 'Woolworths', 'Coles', 'ALDI'
    slug = Column(String(50), unique=True, nullable=False)  # 'woolworths', 'coles', 'aldi'
    logo_url = Column(Text)
    website_url = Column(Text)
    catalogue_url = Column(Text)
    specials_day = Column(String(20))  # 'wednesday', 'saturday'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    store_products = relationship("StoreProduct", back_populates="store")
    specials = relationship("Special", back_populates="store")
    master_products = relationship("MasterProduct", back_populates="store")
