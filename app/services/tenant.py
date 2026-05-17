import secrets
import string
import math
from datetime import datetime, timezone, timedelta
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
from app.services.discord import DiscordService

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
        """Retrieves a tenant by slug for validation purposes."""
        db.execute(text('SET search_path TO "public"'))
        return db.query(Tenant).filter(Tenant.slug == slug).first()

    @staticmethod
    def get_by_stripe_id(db: Session, stripe_id: str) -> Tenant | None:
        """Retrieves a tenant associated with a specific Stripe Customer ID."""
        db.execute(text('SET search_path TO "public"'))
        return db.query(Tenant).filter(Tenant.stripe_customer_id == stripe_id).first()

    @staticmethod
    def set_active_status(db: Session, tenant: Tenant, is_active: bool) -> Tenant:
        """
        Toggles the tenant's operational status (e.g., due to billing events).
        Uses an atomic ORM update to bypass SQLAlchemy's session caching.
        """
        db.execute(text('SET search_path TO "public"'))
        db.query(Tenant).filter(Tenant.id == tenant.id).update({"is_active": is_active})
        db.commit()
        db.refresh(tenant)
        return tenant

    @staticmethod
    def get_paginated(db: Session, page: int = 1, size: int = 20, name: str = None, is_active: bool = None) -> dict:
        """Global tenant search restricted to Superadmin."""
        db.execute(text('SET search_path TO "public"'))
        query = db.query(Tenant)
        
        if name:
            query = query.filter(Tenant.name.ilike(f"%{name}%"))
        if is_active is not None:
            query = query.filter(Tenant.is_active == is_active)
            
        total = query.count()
        pages = math.ceil(total / size) if total > 0 else 1
        items = query.order_by(Tenant.created_at.desc()).offset((page - 1) * size).limit(size).all()
        return {"items": items, "total": total, "page": page, "size": size, "pages": pages}

    @staticmethod
    def create(db: Session, tenant_in: TenantCreate) -> dict:
        """
        Provisions a new tenant, orchestrating global record creation, 
        Stripe billing generation, physical schema materialization,
        default master user injection, and initial audit logs.
        Returns a rich dictionary to prevent SQLAlchemy post-commit expiration issues.
        """
        db.execute(text('SET search_path TO "public"'))
        db_tenant = Tenant(**tenant_in.model_dump())
        db.add(db_tenant)
        db.flush() 

        try:
            # 1. Billing integration
            billing_email = f"billing@{db_tenant.slug}.com"
            stripe_id = StripeService.create_customer(email=billing_email, name=db_tenant.name, tenant_id=str(db_tenant.id))
            db_tenant.stripe_customer_id = stripe_id
            db.commit()
            db.refresh(db_tenant)
            
            # 2. Schema Provisioning & DDL
            schema_name = f"tenant_{db_tenant.slug}"
            db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
            db.commit()
            
            with engine.connect().execution_options(schema_translate_map={None: schema_name}) as conn:
                Base.metadata.create_all(conn, tables=[Product.__table__, AuditLog.__table__])
                conn.commit()
                
            # 3. Cryptographic Password Generation
            alphabet = string.ascii_letters + string.digits + "!@#$%*"
            while True:
                temp_pwd = ''.join(secrets.choice(alphabet) for _ in range(12))
                if (any(c.islower() for c in temp_pwd) and any(c.isupper() for c in temp_pwd) and 
                    sum(c.isdigit() for c in temp_pwd) >= 1 and any(c in "!@#$%*" for c in temp_pwd)):
                    break

            # 4. Master User with 15-Minute TTL
            master_email = f"master@{db_tenant.slug}.com"
            
            # CORREÇÃO ARQUITETURAL: Geração de username aleatório (KISS)
            # Evita colisões e cumpre o requisito de username único e autogerado
            random_suffix = uuid.uuid4().hex[:6]
            master_username = f"master_{random_suffix}"
            
            admin_in = UserCreate(
                tenant_id=db_tenant.id,
                username=master_username, # O campo preenchido com a hash aleatória
                email=master_email,
                password=temp_pwd,
                full_name=f"Master {db_tenant.name}",
                role="admin"
            )
            master_user = UserService.create(db, user_in=admin_in)
            master_user.password_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
            db.commit()

            # 5. Schema Alignment & Initial Audit Log Injection
            db.execute(text(f'SET search_path TO "{schema_name}"'))
            AuditService.log_action(db=db, tenant_id=db_tenant.id, user_id=None, action="PROVISION_TENANT", entity_name="Tenant", entity_id=str(db_tenant.id), changes={"name": db_tenant.name, "slug": db_tenant.slug})
            AuditService.log_action(db=db, tenant_id=db_tenant.id, user_id=None, action="PROVISION_MASTER_USER", entity_name="User", entity_id=master_email, changes={"email": master_email, "role": "admin"})
            db.commit()
            
            DiscordService.send_alert(
                f"✅ **New Architecture Provisioned**\n"
                f"**Tenant:** {db_tenant.name}\n"
                f"**Slug:** {db_tenant.slug}\n"
                f"**Master Identity:** master@{db_tenant.slug}.com"
            )

            # Architectural Fix: Explicitly mapped 'created_at' and other fields
            return {
                "id": db_tenant.id,
                "name": db_tenant.name,
                "slug": db_tenant.slug,
                "stripe_customer_id": db_tenant.stripe_customer_id,
                "is_active": db_tenant.is_active,
                "created_at": db_tenant.created_at,
                "master_email": master_email,
                "temporary_password": temp_pwd,
                "expires_in": "15 minutes"
            }
            
        except Exception as e:
            db.rollback()
            raise ValueError(f"Failed to provision Tenant architecture: {str(e)}")