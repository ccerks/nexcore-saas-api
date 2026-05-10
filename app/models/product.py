from sqlalchemy import Column, String, Float, Integer, ForeignKey, Text, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.session import Base 

class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Core Information
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # E-commerce Identifiers
    sku_pai = Column(String, nullable=False, index=True)
    sku_filho = Column(String, nullable=True, index=True)
    ean = Column(String, nullable=True, index=True)
    
    # Variations Handling
    is_variation = Column(Boolean, default=False)
    attributes = Column(JSON, nullable=True) 
    
    # Pricing & Inventory
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)

    # Relationships
    tenant = relationship("Tenant", back_populates="products")
    
    # Self-Referential Relationship (Parent -> Children)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    children = relationship("Product", backref="parent", remote_side=[id])