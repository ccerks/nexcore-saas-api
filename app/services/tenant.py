from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid

from app.models.tenant import Tenant
from app.models.product import Product
from app.models.audit import AuditLog
from app.schemas.tenant import TenantCreate
from app.services.stripe_service import StripeService
from app.db.session import engine, Base

# Internal service bindings for unified provisioning
from app.services.user import UserService
from app.schemas.user import UserCreate
from app.services.audit import AuditService

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
        Stripe billing generation, physical schema materialization,
        default master user injection, and initial audit logs.
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
            
            # 2. Physical Schema Provisioning
            schema_name = f"tenant_{db_tenant.slug}"
            db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
            db.commit()
            
            # 3. Isolated DDL Materialization
            tenant_specific_tables = [Product.__table__, AuditLog.__table__]
            with engine.connect().execution_options(schema_translate_map={None: schema_name}) as conn:
                Base.metadata.create_all(conn, tables=tenant_specific_tables)
                conn.commit()
                
            # 4. Automated Master User Provisioning
            master_email = f"master@{db_tenant.slug}.com"
            master_password = "SecurePassword123!"
            
            admin_in = UserCreate(
                tenant_id=db_tenant.id,
                email=master_email,
                password=master_password,
                full_name=f"Master {db_tenant.name}",
                role="admin"
            )
            UserService.create(db, user_in=admin_in)

            # 5. Schema Alignment & Initial Audit Log Injection
            db.execute(text(f'SET search_path TO "{schema_name}"'))
            
            AuditService.log_action(
                db=db,
                tenant_id=db_tenant.id,
                user_id=None,
                action="PROVISION_TENANT",
                entity_name="Tenant",
                entity_id=str(db_tenant.id),
                changes={"name": db_tenant.name, "slug": db_tenant.slug}
            )
            
            AuditService.log_action(
                db=db,
                tenant_id=db_tenant.id,
                user_id=None,
                action="PROVISION_MASTER_USER",
                entity_name="User",
                entity_id=master_email,
                changes={"email": master_email, "role": "admin"}
            )
            db.commit()
                
            return db_tenant
            
        except Exception as e:
            db.rollback()
            raise ValueError(f"Failed to provision Tenant architecture: {str(e)}")