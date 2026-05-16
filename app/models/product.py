import uuid
from sqlalchemy import Column, String, Float, Integer, Boolean, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.session import Base

class Product(Base):
    """
    Relational model for the Product entity.
    Implements a Flat Structure for variations and soft-delete auditing.
    """
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Cross-dimension Link: Forces PostgreSQL to validate the tenant's existence in the global 'public' schema.
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("public.tenants.id", ondelete="CASCADE"), nullable=False)
    
    # Intra-schema Link: Parent and child variations reside within the same tenant schema.
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
    
    # Temporal Auditing: Automatically records the exact timestamp of creation.
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    
    # Soft Delete Implementation
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Global Audit Link: Identifies which global user soft-deleted the product.
    last_deleted_by = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="SET NULL"), nullable=True)
    deactivation_count = Column(Integer, default=0)

    tenant = relationship("Tenant", back_populates="products")
    children = relationship("Product", backref="parent", remote_side=[id])