import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.session import Base

class AuditLog(Base):
    """
    Relational model for system auditing.
    Stored within dedicated tenant schemas but references global public tables.
    """
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Architectural Fix: Explicitly anchor foreign keys to the global 'public' schema
    # to maintain integrity across isolated database dimensions.
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("public.tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="SET NULL"), nullable=True)
    
    action = Column(String(50), nullable=False)
    entity_name = Column(String(50), nullable=False)
    entity_id = Column(String(50), nullable=False)
    
    changes = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())

    # Relationships point to global models already anchored in 'public'
    user = relationship("User")