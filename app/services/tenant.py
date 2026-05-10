from sqlalchemy.orm import Session
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate

class TenantService:
    """
    Handles all business logic and database operations for Tenants.
    """
    
    @staticmethod
    def get_by_slug(db: Session, slug: str) -> Tenant | None:
        return db.query(Tenant).filter(Tenant.slug == slug).first()

    @staticmethod
    def create(db: Session, tenant_in: TenantCreate) -> Tenant:
        db_tenant = Tenant(name=tenant_in.name, slug=tenant_in.slug)
        db.add(db_tenant)
        db.commit()
        db.refresh(db_tenant)
        return db_tenant