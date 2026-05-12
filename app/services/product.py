import math
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.models.product import Product
from app.schemas.product import ProductCreate
from app.services.audit import AuditService

class ProductService:
    
    @staticmethod
    def create(db: Session, product_in: ProductCreate, tenant_id: UUID, user_id: UUID) -> Product:
        """
        Create a new product and log the action atomically.
        The user_id is now required for the audit trail.
        """
        db_product = Product(
            **product_in.model_dump(),
            tenant_id=tenant_id
        )
        
        db.add(db_product)
        db.flush() 
        
        AuditService.log_action(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            action="CREATE",
            entity_name="Product",
            entity_id=str(db_product.id),
            changes=product_in.model_dump()
        )
        
        db.commit()
        db.refresh(db_product)
        return db_product

    @staticmethod
    def get_paginated_products(
        db: Session, 
        tenant_id: UUID, 
        page: int = 1, 
        size: int = 20, 
        name_filter: str | None = None
    ) -> dict:
        query = db.query(Product).filter(Product.tenant_id == tenant_id)

        if name_filter:
            query = query.filter(Product.name.ilike(f"%{name_filter}%"))

        total_records = query.count()
        total_pages = math.ceil(total_records / size) if total_records > 0 else 1
        
        offset_value = (page - 1) * size
        products = query.offset(offset_value).limit(size).all()

        return {
            "items": products,
            "total": total_records,
            "page": page,
            "size": size,
            "pages": total_pages
        }

    @staticmethod
    def get_by_sku(db: Session, tenant_id: UUID, sku_pai: str, sku_filho: str | None = None) -> Product | None:
        query = db.query(Product).filter(
            Product.tenant_id == tenant_id,
            Product.sku_pai == sku_pai
        )
        if sku_filho:
            query = query.filter(Product.sku_filho == sku_filho)
        return query.first()

    @staticmethod
    def update_image_url(db: Session, product_id: UUID, tenant_id: UUID, image_url: str) -> Product | None:
        product = db.query(Product).filter(
            Product.id == product_id, 
            Product.tenant_id == tenant_id
        ).first()
        if not product:
            return None
        product.image_url = image_url
        db.commit()
        db.refresh(product)
        return product