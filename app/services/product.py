import math
import json
import pika
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import UUID

from app.models.product import Product
from app.schemas.product import ProductCreate
from app.services.audit import AuditService
from app.services.messenger import MessengerService

class ProductService:
    
    @staticmethod
    def create(db: Session, product_in: ProductCreate, tenant_id: UUID, user_id: UUID) -> Optional[Product]:
        """
        Creates or restores a product. Validates SKU uniqueness within the tenant's isolated schema.
        """
        existing = ProductService.get_by_sku(
            db=db, tenant_id=tenant_id, sku_pai=product_in.sku_pai, 
            sku_filho=product_in.sku_filho, include_deleted=True
        )
        
        if existing:
            if existing.deleted_at is None:
                return None 
            
            # Restore soft-deleted record
            for key, value in product_in.model_dump(exclude_unset=True).items():
                setattr(existing, key, value)
            
            existing.deleted_at = None
            db.flush()
            
            AuditService.log_action(db, tenant_id, user_id, "RESTORE", "Product", str(existing.id), product_in.model_dump())
            db.commit()
            db.refresh(existing)
            return existing

        db_product = Product(**product_in.model_dump(), tenant_id=tenant_id)
        db.add(db_product)
        db.flush() 
        
        AuditService.log_action(db, tenant_id, user_id, "CREATE", "Product", str(db_product.id), product_in.model_dump())
        db.commit()
        db.refresh(db_product)
        return db_product

    @classmethod
    def bulk_create(cls, db: Session, products_in: List[ProductCreate], tenant_id: UUID, user_id: UUID) -> Optional[List[Product]]:
        """
        Processes atomic batch insertion of products.
        """
        try:
            db_products = [Product(**p.model_dump(), tenant_id=tenant_id) for p in products_in]
            db.add_all(db_products)
            db.flush()

            for product in db_products:
                AuditService.log_action(db, tenant_id, user_id, "BULK_CREATE", "Product", str(product.id))
            
            db.commit()
            for product in db_products:
                db.refresh(product)
            return db_products
        except IntegrityError:
            db.rollback()
            return None

    @staticmethod
    def update_image_url(db: Session, product_id: UUID, tenant_id: UUID, image_url: str) -> Optional[Product]:
        """
        Updates image and dispatches background task to RabbitMQ for orphaned file cleanup.
        """
        product = db.query(Product).filter(
            Product.id == product_id, Product.tenant_id == tenant_id, Product.deleted_at == None
        ).first()
        
        if not product:
            return None
            
        old_image_url = product.image_url
        product.image_url = image_url
        db.commit()
        db.refresh(product)
        
        if old_image_url and old_image_url != image_url:
            ProductService._dispatch_image_cleanup(old_image_url)

        return product

    @staticmethod
    def _dispatch_image_cleanup(file_path: str) -> None:
        """Internal helper to manage RabbitMQ task queuing."""
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
            channel = connection.channel()
            channel.queue_declare(queue='nexcore_tasks', durable=True)
            
            payload = {"action": "delete_image", "data": {"file_path": file_path}}
            channel.basic_publish(
                exchange='', routing_key='nexcore_tasks',
                body=json.dumps(payload),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            connection.close()
        except Exception as e:
            print(f"MQ Error: {e}")

    @staticmethod
    def delete(db: Session, product_id: UUID, tenant_id: UUID, user_id: UUID) -> bool:
        """Performs soft delete and triggers external notifications."""
        product = db.query(Product).filter(
            Product.id == product_id, Product.tenant_id == tenant_id, Product.deleted_at == None
        ).first()

        if not product:
            return False
            
        product.deleted_at = datetime.now(timezone.utc)
        product.last_deleted_by = user_id
        product.deactivation_count = (product.deactivation_count or 0) + 1
        db.flush()

        MessengerService.send_notification({
            "event": "PRODUCT_DELETED", "tenant_id": str(tenant_id),
            "product_name": product.name, "sku": product.sku_pai, "deleted_by": str(user_id)
        })
        
        AuditService.log_action(db, tenant_id, user_id, "DELETE", "Product", str(product.id))
        db.commit()
        return True

    @staticmethod
    def get_paginated_products(db: Session, tenant_id: UUID, page: int = 1, size: int = 20, name_filter: str = None) -> dict:
        query = db.query(Product).filter(Product.tenant_id == tenant_id, Product.deleted_at == None)
        if name_filter:
            query = query.filter(Product.name.ilike(f"%{name_filter}%"))

        total = query.count()
        pages = math.ceil(total / size) if total > 0 else 1
        items = query.offset((page - 1) * size).limit(size).all()
        return {"items": items, "total": total, "page": page, "size": size, "pages": pages}

    @staticmethod
    def get_by_sku(db: Session, tenant_id: UUID, sku_pai: str, sku_filho: str = None, include_deleted: bool = False) -> Optional[Product]:
        query = db.query(Product).filter(Product.tenant_id == tenant_id, Product.sku_pai == sku_pai)
        if not include_deleted:
            query = query.filter(Product.deleted_at == None)
        if sku_filho:
            query = query.filter(Product.sku_filho == sku_filho)
        return query.first()