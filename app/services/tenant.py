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
    Manages Tenant lifecycle, including Stripe integration and 
    physical DDL schema provisioning with selective table creation.
    """
    
    @staticmethod
    def create(db: Session, tenant_in: TenantCreate) -> Tenant:
        """
        Provisions a new tenant. Orchestrates global record creation, 
        Stripe customer attachment, and isolated schema generation.
        """
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
            
            # 3. Selective Migration (The Architectural Fix)
            # We filter create_all to deploy ONLY tenant-specific tables.
            with engine.connect() as conn:
                conn.execute(text(f'SET search_path TO "{schema_name}", public'))
                
                # Targeted metadata deployment
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

    @staticmethod
    def get(db: Session, tenant_id: str) -> Tenant | None:
        return db.query(Tenant).get(tenant_id)