from sqlalchemy.orm import Session
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate
from app.services.stripe_service import StripeService

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
    
    from sqlalchemy.orm import Session
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate
from app.services.stripe_service import StripeService

class TenantService:
    
    @staticmethod
    def create(db: Session, tenant_in: TenantCreate) -> Tenant:
        """
        Creates a new Tenant and provisions a Stripe Customer within a single transaction.
        Implements flush/rollback to ensure data consistency across distributed systems.
        """
        db_tenant = Tenant(**tenant_in.model_dump())
        db.add(db_tenant)
        
        # Flush sends the insert to the DB to generate the UUID, but keeps the transaction open
        db.flush() 

        try:
            # Provision customer in Stripe using the newly generated Tenant ID
            # Utilizing a placeholder email based on the slug for the sandbox environment
            billing_email = f"billing@{db_tenant.slug}.com"
            
            stripe_customer_id = StripeService.create_customer(
                email=billing_email,
                name=db_tenant.name,
                tenant_id=str(db_tenant.id)
            )
            
            # Attach the Stripe ID to our database model
            db_tenant.stripe_customer_id = stripe_customer_id
            
            # Commit only if both local DB and Stripe operations succeed
            db.commit()
            db.refresh(db_tenant)
            return db_tenant
            
        except Exception as e:
            # Revert the local DB insert if Stripe integration fails
            db.rollback()
            raise ValueError(f"Failed to provision Tenant billing: {str(e)}")

    @staticmethod
    def get(db: Session, tenant_id: str) -> Tenant | None:
        return db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    @staticmethod
    def get_by_slug(db: Session, slug: str) -> Tenant | None:
        """
        Retrieves a tenant by its unique slug to prevent duplication.
        """
        return db.query(Tenant).filter(Tenant.slug == slug).first()