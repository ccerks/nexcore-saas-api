import math
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.models.product import Product
from app.schemas.product import ProductCreate

class ProductService:
    
    @staticmethod
    def create(db: Session, product_in: ProductCreate, tenant_id: UUID) -> Product:
        """
        Create a new product.
        The tenant_id is injected by the backend to ensure data isolation.
        """
        # Unpack the validated Pydantic model and inject the tenant_id
        db_product = Product(
            **product_in.model_dump(),
            tenant_id=tenant_id
        )
        
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        return db_product

    @staticmethod
    def get_all_by_tenant(db: Session, tenant_id: UUID, skip: int = 0, limit: int = 100) -> List[Product]:
        """
        Retrieve products isolated by tenant_id.
        """
        return db.query(Product).filter(
            Product.tenant_id == tenant_id
        ).offset(skip).limit(limit).all()

    @staticmethod
    def get_by_sku(db: Session, tenant_id: UUID, sku_pai: str, sku_filho: str | None = None) -> Product | None:
        """
        Check if a specific SKU already exists within a tenant's catalog.
        """
        query = db.query(Product).filter(
            Product.tenant_id == tenant_id,
            Product.sku_pai == sku_pai
        )
        if sku_filho:
            query = query.filter(Product.sku_filho == sku_filho)
            
        return query.first()
    
    @staticmethod
    def get_paginated_products(
        db: Session, 
        tenant_id: UUID, 
        page: int = 1, 
        size: int = 20, 
        name_filter: str | None = None
    ) -> dict:
        """
        Retrieve a paginated list of products with optional filtering.
        Returns a dictionary compatible with the PaginatedResponse schema.
        """
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
    def update_image_url(db: Session, product_id: UUID, tenant_id: UUID, image_url: str) -> Product | None:
        """
        Updates the image URL of a specific product.
        Enforces tenant isolation to prevent unauthorized modifications.
        """
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