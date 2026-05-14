import sys
import os
from sqlalchemy import text

# Append project root to python path for module resolution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocal
from app.services.user import UserService
from app.schemas.user import UserCreate
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate
from app.services.tenant import TenantService

def create_master_user():
    """
    Bootstrap script to provision the initial administrative user.
    Uses 'public' schema context for global consistency.
    """
    db = SessionLocal()
    try:
        # Crucial: Enforce 'public' schema context for Global Entities
        db.execute(text('SET search_path TO "public"'))
        
        admin_email = "admin1@nexcore.com"
        
        # Check for existing admin to maintain idempotency
        if UserService.get_by_email(db, email=admin_email):
            print(f"Info: User {admin_email} already exists.")
            return

        # Fetch or Create the Master Tenant
        tenant = db.query(Tenant).first()
        
        if not tenant:
            print("Info: No Tenant found. Provisioning the default Master Tenant...")
            tenant_in = TenantCreate(name="NexCore Master", slug="nexcore-master")
            # TenantService.create handles both 'public' entry and 'dedicated' schema creation
            tenant = TenantService.create(db, tenant_in=tenant_in)
            print(f"Success: Master Tenant created with ID: {tenant.id}")

        # Re-verify 'public' context before User insertion
        db.execute(text('SET search_path TO "public"'))

        admin_in = UserCreate(
            tenant_id=tenant.id, # Valid UUID from public.tenants
            email=admin_email,
            password="SecurePassword123!",
            full_name="NexCore System Admin",
            role="admin" 
        )
        
        UserService.create(db, user_in=admin_in)
        print(f"Success: Admin user {admin_email} provisioned in public.users.")
        
    except Exception as e:
        print(f"Error during master user creation: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_master_user()