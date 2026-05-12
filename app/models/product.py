# app/models/product.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Boolean, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=True)
    
    name = Column(String(255), nullable=False)
    description = Column(String, nullable=True)
    sku_pai = Column(String(100), nullable=False)
    sku_filho = Column(String(100), nullable=True)
    ean = Column(String(13), nullable=True)
    is_variation = Column(Boolean, default=False)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    attributes = Column(JSON, nullable=True)
    image_url = Column(String, nullable=True)
    
    # Soft delete and historical metadata
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    last_deleted_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    deactivation_count = Column(Integer, default=0)

    tenant = relationship("Tenant", back_populates="products")
    children = relationship("Product", backref="parent", remote_side=[id])