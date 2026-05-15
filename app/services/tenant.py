from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List

from app.models.tenant import Tenant
from app.models.product import Product
from app.models.audit import AuditLog
from app.schemas.tenant import TenantCreate
from app.services.stripe_service import StripeService
from app.db.session import engine

class TenantService:
    """
    Manages Tenant lifecycle, including Stripe integration, 
    physical DDL schema provisioning, and global entity retrieval.
    """
    
    @staticmethod
    def get(db: Session, tenant_id: str) -> Tenant | None:
        db.execute(text('SET search_path TO "public"'))
        return db.query(Tenant).get(tenant_id)

    @staticmethod
    def get_by_slug(db: Session, slug: str) -> Tenant | None:
        """
        Retrieves a tenant by slug for validation purposes.
        """
        db.execute(text('SET search_path TO "public"'))
        return db.query(Tenant).filter(Tenant.slug == slug).first()

    @staticmethod
    def get_by_stripe_id(db: Session, stripe_id: str) -> Tenant | None:
        """
        Retrieves a tenant associated with a specific Stripe Customer ID.
        """
        db.execute(text('SET search_path TO "public"'))
        return db.query(Tenant).filter(Tenant.stripe_customer_id == stripe_id).first()

    @staticmethod
    def set_active_status(db: Session, tenant: Tenant, is_active: bool) -> Tenant:
        """
        Toggles the tenant's operational status (e.g., due to billing events).
        Uses an atomic ORM update to bypass SQLAlchemy's session caching 
        and guarantee a physical write to the database.
        """
        db.execute(text('SET search_path TO "public"'))
        
        # Architectural Fix: Atomic Direct Update 
        db.query(Tenant).filter(Tenant.id == tenant.id).update({"is_active": is_active})
        db.commit()
        
        # Synchronize the Python object state with the new Database reality
        db.refresh(tenant)
        return tenant

    @staticmethod
    def create(db: Session, tenant_in: TenantCreate) -> Tenant:
        """
        Provisions a new tenant, orchestrating global record creation, 
        Stripe customer attachment, and isolated schema generation.
        """
        db.execute(text('SET search_path TO "public"'))
        db_tenant = Tenant(**tenant_in.model_dump())
        db.add(db_tenant)
        db.flush() 

        try:
            # 1. Billing integration
            billing_email = f"billing@{db_tenant.slug}.com"
            stripe_id = StripeService.create_customer(
                email=billing_email,
                name=db_tenant.name,
                tenant_id=str(db_tenant.id)
            )
            db_tenant.stripe_customer_id = stripe_id
            db.commit()
            db.refresh(db_tenant)
            
            # 2. Schema Provisioning
            schema_name = f"tenant_{db_tenant.slug}"
            db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
            db.commit()
            
            # 3. Selective Migration (Architectural Fix)
            with engine.connect() as conn:
                conn.execute(text(f'SET search_path TO "{schema_name}", public'))
                
                tenant_specific_tables = [
                    Product.__table__,
                    AuditLog.__table__
                ]
                
                Product.metadata.create_all(conn, tables=tenant_specific_tables)
                conn.commit()
                
            return db_tenant
            
        except Exception as e:
            db.rollback()
            raise ValueError(f"Failed to provision Tenant architecture: {str(e)}")