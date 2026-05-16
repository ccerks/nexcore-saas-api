import sys
import os
import uuid
from sqlalchemy import text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocal
from app.services.user import UserService
from app.schemas.user import UserCreate
from app.schemas.tenant import TenantCreate
from app.services.tenant import TenantService

def provision_isolated_tenant_and_admin() -> None:
    """
    Automates the provisioning sequence by delegating creation to TenantService,
    then seeds the primary administrative user into the public registry.
    """
    db = SessionLocal()
    try:
        db.execute(text('SET search_path TO "public"'))
        
        u_hash = uuid.uuid4().hex[:6]
        store_name = f"NexCore Store {u_hash}"
        slug = f"store-{u_hash}"
        admin_email = f"admin_{u_hash}@nexcore.com"
        raw_password = "SecurePassword123!"

        print(f"[*] Delegating orchestration to TenantService for: {store_name}...")
        tenant_in = TenantCreate(name=store_name, slug=slug)
        # TenantService internally manages schema creation and table DDL materialization
        tenant = TenantService.create(db, tenant_in=tenant_in)

        db.execute(text('SET search_path TO "public"'))
        print(f"[*] Provisioning Admin Anchor: {admin_email}...")
        
        admin_in = UserCreate(
            tenant_id=tenant.id,
            email=admin_email,
            password=raw_password,
            full_name=f"Admin {u_hash}",
            role="admin"
        )
        
        UserService.create(db, user_in=admin_in)
        db.commit()

        print("\n[+] Architecture Provisioned Successfully!")
        print(f"    Tenant Schema : tenant_{slug}")
        print(f"    Admin Login   : {admin_email}")
        print(f"    Password      : {raw_password}\n")

    except Exception as e:
        print(f"[!] Critical failure during provisioning: {e}")
        db.rollback()
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    provision_isolated_tenant_and_admin()