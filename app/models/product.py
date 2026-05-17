import uuid
# Architectural Fix: Imported 'Identity' to enforce PostgreSQL native sequence generation
from sqlalchemy import Column, String, Float, Integer, Boolean, ForeignKey, JSON, DateTime, BigInteger, Identity
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.session import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Architectural Fix: Explicit Identity definition for non-PK autoincrement in PostgreSQL
    friendly_id = Column(BigInteger, Identity(start=1), unique=True, index=True)
    
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("public.tenants.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=True)
    
    name = Column(String(255), nullable=False)
    description = Column(String, nullable=True)
    sku = Column(String(100), unique=True, index=True, nullable=False)
    ean = Column(String(13), nullable=True)
    is_variation = Column(Boolean, default=False)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    attributes = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    last_deleted_by = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="SET NULL"), nullable=True)
    deactivation_count = Column(Integer, default=0)

    tenant = relationship("Tenant", back_populates="products")
    children = relationship("Product", backref="parent", remote_side=[id])