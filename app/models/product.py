import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Boolean, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # O Cabo Link de Conexão entre Dimensões:
    # Ao adicionar 'public.' antes do nome da tabela, garantimos que o PostgreSQL
    # saia da dimensão atual da loja e valide a existência do lojista no mapa global.
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("public.tenants.id", ondelete="CASCADE"), nullable=False)
    
    # Como o pai e o filho (variações de cor/tamanho) são produtos, 
    # eles moram no mesmo schema. Portanto, NÃO colocamos 'public' aqui.
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
    
    # Auditoria (Soft Delete)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Outro Cabo Link cruzando a dimensão para o mapa de Usuários globais.
    # Garante que saibamos quem apagou o produto, mesmo que o usuário esteja no 'public'
    last_deleted_by = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="SET NULL"), nullable=True)
    deactivation_count = Column(Integer, default=0)

    tenant = relationship("Tenant", back_populates="products")
    children = relationship("Product", backref="parent", remote_side=[id])