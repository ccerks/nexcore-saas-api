import math
import json
import pika
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError
from uuid import UUID

from app.models.product import Product
from app.models.product_image import ProductImage
from app.schemas.product import ProductCreate
from app.services.audit import AuditService
from app.services.messenger import MessengerService

class ProductService:
    """
    Handles lifecycle and business logic for the Product entity.
    Enforces strict English-only naming conventions, unified SKU isolation boundaries,
    and orthogonal state management tracking.
    """
    
    @staticmethod
    def create(db: Session, product_in: ProductCreate, tenant_id: UUID, user_id: UUID) -> Optional[Product]:
        """Creates a new product or restores a soft-deleted one, updating actor tracking metadata."""
        existing = ProductService.get_by_sku(
            db=db, tenant_id=tenant_id, sku=product_in.sku, include_deleted=True
        )
        
        if existing:
            if existing.deleted_at is None:
                return None 
            
            for key, value in product_in.model_dump(exclude_unset=True).items():
                setattr(existing, key, value)
            
            existing.deleted_at = None
            existing.is_active = True
            existing.last_updated_by = user_id
            db.flush()
            
            AuditService.log_action(
                db, tenant_id, user_id, "RESTORE", "Product", str(existing.id), product_in.model_dump(mode='json')
            )
            db.commit()
            db.refresh(existing)
            return existing

        db_product = Product(
            **product_in.model_dump(), 
            tenant_id=tenant_id,
            last_updated_by=user_id
        )
        db.add(db_product)
        db.flush() 
        
        AuditService.log_action(
            db, tenant_id, user_id, "CREATE", "Product", str(db_product.id), product_in.model_dump(mode='json')
        )
        db.commit()
        db.refresh(db_product)
        return db_product

    @classmethod
    def bulk_create(cls, db: Session, products_in: List[ProductCreate], tenant_id: UUID, user_id: UUID) -> Optional[List[Product]]:
        """Processes atomic batch insertion of products safely."""
        try:
            db_products = [Product(**p.model_dump(), tenant_id=tenant_id, last_updated_by=user_id) for p in products_in]
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
    def update(db: Session, product_id: UUID, product_in: dict, tenant_id: UUID, user_id: UUID) -> Optional[Product]:
        """Applies partial updates to a product record and updates actor metadata."""
        product = db.query(Product).filter(
            Product.id == product_id,
            Product.tenant_id == tenant_id,
            Product.deleted_at == None
        ).first()

        if not product:
            return None

        for key, value in product_in.items():
            if hasattr(product, key):
                setattr(product, key, value)

        product.last_updated_by = user_id
        db.flush()

        AuditService.log_action(db, tenant_id, user_id, "UPDATE", "Product", str(product.id), product_in)
        db.commit()
        db.refresh(product)
        return product

    @staticmethod
    def delete(db: Session, product_id: UUID, tenant_id: UUID, user_id: UUID) -> bool:
        """Performs logical soft delete, toggles business visibility, and triggers external auditing syncs."""
        product = db.query(Product).filter(
            Product.id == product_id, Product.tenant_id == tenant_id, Product.deleted_at == None
        ).first()

        if not product:
            return False
            
        product.deleted_at = datetime.now(timezone.utc)
        product.is_active = False
        product.last_deleted_by = user_id
        product.last_updated_by = user_id
        product.deactivation_count = (product.deactivation_count or 0) + 1
        db.flush()

        MessengerService.send_notification({
            "event": "PRODUCT_DELETED", "tenant_id": str(tenant_id),
            "product_name": product.name, "sku": product.sku, "deleted_by": str(user_id)
        })
        
        AuditService.log_action(db, tenant_id, user_id, "DELETE", "Product", str(product.id))
        db.commit()
        return True
        
    @staticmethod
    def restore(db: Session, product_id: UUID, tenant_id: UUID, user_id: UUID) -> Optional[Product]:
        """Idempotent restoration of a soft-deleted product."""
        product = db.query(Product).filter(
            Product.id == product_id,
            Product.tenant_id == tenant_id,
            Product.deleted_at != None
        ).first()

        if not product:
            return None

        product.deleted_at = None
        product.is_active = True
        product.last_updated_by = user_id
        db.flush()

        AuditService.log_action(db, tenant_id, user_id, "RESTORE", "Product", str(product.id))
        db.commit()
        db.refresh(product)
        return product

    @staticmethod
    def get_paginated_products(db: Session, tenant_id: UUID, page: int = 1, size: int = 20, name_filter: str = None) -> dict:
        """Retrieves paginated catalog items dynamically filtered by tenant. Includes N+1 query optimization."""
        query = db.query(Product).options(selectinload(Product.images)).filter(
            Product.tenant_id == tenant_id, Product.deleted_at == None
        )
        if name_filter:
            query = query.filter(Product.name.ilike(f"%{name_filter}%"))

        total = query.count()
        pages = math.ceil(total / size) if total > 0 else 1
        items = query.offset((page - 1) * size).limit(size).all()
        return {"items": items, "total": total, "page": page, "size": size, "pages": pages}

    @staticmethod
    def get_by_sku(db: Session, tenant_id: UUID, sku: str, include_deleted: bool = False) -> Optional[Product]:
        query = db.query(Product).filter(Product.tenant_id == tenant_id, Product.sku == sku)
        if not include_deleted:
            query = query.filter(Product.deleted_at == None)
        return query.first()

    @staticmethod
    def _dispatch_image_cleanup(file_path: str) -> None:
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
    def add_image_record(db: Session, product_id: UUID, tenant_id: UUID, url: str, filename: str) -> None:
        existing_images_count = db.query(ProductImage).filter(ProductImage.product_id == product_id).count()
        is_main_image = (existing_images_count == 0)
        
        image_record = ProductImage(
            product_id=product_id, url=url, alt_text=filename, is_main=is_main_image
        )
        db.add(image_record)
        db.flush()

    @staticmethod
    def set_main_image(db: Session, product_id: UUID, image_id: UUID, tenant_id: UUID) -> bool:
        product = db.query(Product).filter(Product.id == product_id, Product.tenant_id == tenant_id).first()
        if not product: return False

        target_image = db.query(ProductImage).filter(
            ProductImage.id == image_id, ProductImage.product_id == product_id
        ).first()
        if not target_image: return False

        db.query(ProductImage).filter(ProductImage.product_id == product_id).update({"is_main": False})
        target_image.is_main = True
        db.commit()
        return True

    @staticmethod
    def delete_image_record(db: Session, product_id: UUID, image_id: UUID, tenant_id: UUID) -> bool:
        product = db.query(Product).filter(Product.id == product_id, Product.tenant_id == tenant_id).first()
        if not product: return False

        image = db.query(ProductImage).filter(
            ProductImage.id == image_id, ProductImage.product_id == product_id
        ).first()
        if not image: return False

        ProductService._dispatch_image_cleanup(image.url)
        db.delete(image)
        db.commit()
        return True