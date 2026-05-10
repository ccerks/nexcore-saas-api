import sys
import os

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
    """
    db = SessionLocal()
    try:
        admin_email = "admin@nexcore.com"
        
        # Prevent duplicate admin provisioning
        if UserService.get_by_email(db, email=admin_email):
            print(f"Info: User {admin_email} already exists.")
            return

        # Fetch the default tenant, or create it if the DB is completely empty
        tenant = db.query(Tenant).first()
        
        if not tenant:
            print("Info: No Tenant found. Provisioning the default Master Tenant...")
            tenant_in = TenantCreate(name="NexCore Master", slug="nexcore-master")
            tenant = TenantService.create(db, tenant_in=tenant_in)
            print("Success: Master Tenant created.")

        # Provision the Admin User tied to the Tenant
        admin_in = UserCreate(
            tenant_id=tenant.id,
            email=admin_email,
            password="SecureAdminPassword123!",
            full_name="NexCore System Admin",
            role="admin" 
        )
        
        UserService.create(db, user_in=admin_in)
        print(f"Success: Admin user {admin_email} provisioned.")
        
    finally:
        db.close()

if __name__ == "__main__":
    create_master_user()