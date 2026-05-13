import math
import json
import pika
from typing import List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from uuid import UUID

from app.models.product import Product
from app.schemas.product import ProductCreate
from app.services.audit import AuditService

class ProductService:
    
    @staticmethod
    def create(db: Session, product_in: ProductCreate, tenant_id: UUID, user_id: UUID) -> Product | None:
        existing_product = ProductService.get_by_sku(
            db=db, tenant_id=tenant_id, sku_pai=product_in.sku_pai, sku_filho=product_in.sku_filho, include_deleted=True
        )
        
        if existing_product:
            if existing_product.deleted_at is None:
                return None 
            
            for key, value in product_in.model_dump().items():
                setattr(existing_product, key, value)
            
            existing_product.deleted_at = None
            db.flush()
            
            AuditService.log_action(db, tenant_id, user_id, "RESTORE_AND_UPDATE", "Product", str(existing_product.id), product_in.model_dump())
            db.commit()
            db.refresh(existing_product)
            return existing_product

        db_product = Product(**product_in.model_dump(), tenant_id=tenant_id)
        db.add(db_product)
        db.flush() 
        
        AuditService.log_action(db, tenant_id, user_id, "CREATE", "Product", str(db_product.id), product_in.model_dump())
        db.commit()
        db.refresh(db_product)
        return db_product

    @classmethod
    def bulk_create(cls, db: Session, products_in: List[ProductCreate], tenant_id: UUID, user_id: UUID) -> List[Product] | None:
        """
        Processes a bulk insertion of products using an atomic transaction.
        Rolls back the entire batch if an IntegrityError (e.g., duplicate SKU) occurs.
        """
        try:
            db_products = []
            for p_in in products_in:
                product_data = p_in.model_dump(exclude_unset=True)
                db_product = Product(**product_data, tenant_id=tenant_id)
                db_products.append(db_product)

            db.add_all(db_products)
            db.commit()

            for product in db_products:
                db.refresh(product)
                
            return db_products
            
        except IntegrityError:
            db.rollback()
            return None

    @staticmethod
    def get_paginated_products(db: Session, tenant_id: UUID, page: int = 1, size: int = 20, name_filter: str | None = None) -> dict:
        query = db.query(Product).filter(Product.tenant_id == tenant_id, Product.deleted_at == None)

        if name_filter:
            query = query.filter(Product.name.ilike(f"%{name_filter}%"))

        total_records = query.count()
        total_pages = math.ceil(total_records / size) if total_records > 0 else 1
        
        offset_value = (page - 1) * size
        products = query.offset(offset_value).limit(size).all()

        return {"items": products, "total": total_records, "page": page, "size": size, "pages": total_pages}

    @staticmethod
    def get_by_sku(db: Session, tenant_id: UUID, sku_pai: str, sku_filho: str | None = None, include_deleted: bool = False) -> Product | None:
        query = db.query(Product).filter(Product.tenant_id == tenant_id, Product.sku_pai == sku_pai)
        
        if not include_deleted:
            query = query.filter(Product.deleted_at == None)
            
        if sku_filho:
            query = query.filter(Product.sku_filho == sku_filho)
            
        return query.first()

    @staticmethod
    def update_image_url(db: Session, product_id: UUID, tenant_id: UUID, image_url: str) -> Product | None:
        """
        Updates the product image and dispatches a background event to remove the orphaned file.
        """
        product = db.query(Product).filter(
            Product.id == product_id, 
            Product.tenant_id == tenant_id, 
            Product.deleted_at == None
        ).first()
        
        if not product:
            return None
            
        old_image_url = product.image_url
        product.image_url = image_url
        db.commit()
        db.refresh(product)
        
        if old_image_url and old_image_url != image_url:
            try:
                connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
                channel = connection.channel()
                channel.queue_declare(queue='nexcore_tasks', durable=True)
                
                payload = {
                    "action": "delete_image",
                    "data": {"file_path": old_image_url}
                }
                
                channel.basic_publish(
                    exchange='',
                    routing_key='nexcore_tasks',
                    body=json.dumps(payload),
                    properties=pika.BasicProperties(delivery_mode=2)
                )
                connection.close()
            except Exception as e:
                print(f"Failed to queue image for deletion: {e}")

        return product
    
    @staticmethod
    def delete(db: Session, product_id: UUID, tenant_id: UUID, user_id: UUID) -> bool:
        product = db.query(Product).filter(
            Product.id == product_id, 
            Product.tenant_id == tenant_id, 
            Product.deleted_at == None
        ).first()

        if not product:
            return False
            
        product.deleted_at = datetime.now(timezone.utc)
        product.last_deleted_by = user_id
        product.deactivation_count = (product.deactivation_count or 0) + 1
        
        db.flush()

        from app.services.messenger import MessengerService
        MessengerService.send_notification({
            "event": "PRODUCT_DELETED",
            "tenant_id": str(tenant_id),
            "product_name": product.name,
            "sku": product.sku_pai,
            "deleted_by": str(user_id)
        })
        
        AuditService.log_action(db, tenant_id, user_id, "DELETE", "Product", str(product.id), {"status": "soft_deleted"})
        db.commit()
        return True