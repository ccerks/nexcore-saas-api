from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate
from app.services.stripe_service import StripeService
from app.db.session import engine, Base

class TenantService:
    """
    Handles all business logic and database operations for Tenants.
    """
    
    @staticmethod
    def create(db: Session, tenant_in: TenantCreate) -> Tenant:
        """
        Creates a new Tenant, provisions a Stripe Customer, and constructs a 
        physically isolated dedicated database schema (DDL) within a single transaction.
        """
        db_tenant = Tenant(**tenant_in.model_dump())
        db.add(db_tenant)
        db.flush() 

        try:
            billing_email = f"billing@{db_tenant.slug}.com"
            stripe_customer_id = StripeService.create_customer(
                email=billing_email,
                name=db_tenant.name,
                tenant_id=str(db_tenant.id)
            )
            db_tenant.stripe_customer_id = stripe_customer_id
            db.commit()
            db.refresh(db_tenant)
            
            # Enterprise Isolation: Create Dedicated Schema
            schema_name = f"tenant_{db_tenant.slug}"
            db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
            db.commit()
            
            # Migrate tables into the newly isolated schema
            with engine.connect() as conn:
                conn.execute(text(f'SET search_path TO "{schema_name}"'))
                Base.metadata.create_all(conn)
                conn.commit()
                
            return db_tenant
            
        except Exception as e:
            db.rollback()
            raise ValueError(f"Failed to provision Tenant architecture: {str(e)}")

    @staticmethod
    def get(db: Session, tenant_id: str) -> Tenant | None:
        return db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    @staticmethod
    def get_by_slug(db: Session, slug: str) -> Tenant | None:
        return db.query(Tenant).filter(Tenant.slug == slug).first()
    
    @staticmethod
    def get_by_stripe_id(db: Session, stripe_customer_id: str) -> Tenant | None:
        return db.query(Tenant).filter(Tenant.stripe_customer_id == stripe_customer_id).first()

    @staticmethod
    def set_active_status(db: Session, tenant: Tenant, is_active: bool) -> Tenant:
        tenant.is_active = is_active
        db.commit()
        db.refresh(tenant)
        return tenant