import uuid
from sqlalchemy import Column, String, Float, ForeignKey, DateTime, BigInteger, Boolean, Identity
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.session import Base

class Product(Base):
    """
    Core entity for the e-commerce catalog.
    Implements orthogonal state management and tenant-isolated identity sequences.
    """
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Architectural Fix: Replaced implicit autoincrement with explicit PostgreSQL Identity Sequence
    friendly_id = Column(
        BigInteger, 
        Identity(start=1000, cycle=False, always=False), 
        unique=True, 
        index=True
    )
    
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("public.tenants.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    sku = Column(String, nullable=False)
    ean = Column(String, nullable=True)
    
    # Business Logic State
    is_active = Column(Boolean, default=True, server_default="true", nullable=False)
    is_variation = Column(Boolean, default=False)

    price = Column(Float, nullable=False, default=0.0)
    promotional_price = Column(Float, nullable=True)

    stock = Column(BigInteger, nullable=False, default=0)
    reserved_stock = Column(BigInteger, nullable=False, default=0)

    attributes = Column(JSONB, nullable=True, default={})
    
    # Immutable Birth Date & Mutable Audit Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_updated_by = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="SET NULL"), nullable=True)
    
    # Infrastructure Lifecycle State (Soft Delete)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    last_deleted_by = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="SET NULL"), nullable=True)
    deactivation_count = Column(BigInteger, default=0)

    # Relationships
    tenant = relationship("Tenant")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")