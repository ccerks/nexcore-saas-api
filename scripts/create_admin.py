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
    If no Tenant exists, it automatically provisions a master tenant first.
    Ensures execution context is safely set to the 'public' schema.
    """
    db = SessionLocal()
    try:
        # Force the execution context to 'public' for global entities
        db.execute(text('SET search_path TO "public"'))
        
        admin_email = "admin@nexcore.com" # Change to your desired admin email
        
        # Prevent duplicate admin provisioning
        if UserService.get_by_email(db, email=admin_email):
            print(f"Info: User {admin_email} already exists.")
            return

        # Fetch the default tenant, or create it if the DB is completely empty
        tenant = db.query(Tenant).first()
        
        if not tenant:
            print("Info: No Tenant found. Provisioning the default Master Tenant...")
            tenant_in = TenantCreate(name="NexCore Master", slug="nexcore-master")
            # This triggers Stripe integration and Dedicated Schema creation (DDL)
            tenant = TenantService.create(db, tenant_in=tenant_in)
            print("Success: Master Tenant created with Dedicated Schema.")

        # Re-ensure 'public' schema just in case TenantService altered the session state
        db.execute(text('SET search_path TO "public"'))

        # Provision the Admin User tied to the Tenant
        admin_in = UserCreate(
            tenant_id=tenant.id,
            email=admin_email,
            password="SecurePassword123!", # Change this before production
            full_name="NexCore System Admin",
            role="admin" 
        )
        
        UserService.create(db, user_in=admin_in)
        print(f"Success: Admin user {admin_email} provisioned.")
        
    except Exception as e:
        print(f"Error during master user creation: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_master_user()