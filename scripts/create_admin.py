import sys
import os
import uuid
from sqlalchemy import text

# Append project root to python path for module resolution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocal, Base
# IMPORTANT: Ensure your models are imported here so SQLAlchemy registers them in Base.metadata
# from app.models.product import Product
# from app.models.audit_log import AuditLog

from app.services.user import UserService
from app.schemas.user import UserCreate
from app.schemas.tenant import TenantCreate
from app.services.tenant import TenantService

def provision_isolated_tenant_and_admin() -> None:
    """
    Generates a unique Tenant, materializes isolated tables, 
    and creates an exclusive Admin user per execution.
    """
    db = SessionLocal()
    try:
        db.execute(text('SET search_path TO "public"'))
        
        # Generate unique identifiers to ensure absolute isolation per run
        unique_hash = uuid.uuid4().hex[:6]
        store_name = f"NexCore Store {unique_hash}"
        slug = f"store-{unique_hash}"
        
        # Identity constraints
        admin_email = f"admin_{unique_hash}@nexcore.com"
        raw_password = "SecurePassword123!"

        print(f"[*] Provisioning isolated dimension for: {store_name}...")
        tenant_in = TenantCreate(name=store_name, slug=slug)
        tenant = TenantService.create(db, tenant_in=tenant_in)
        
        schema_name = f"tenant_{slug}"
        
        # --- ARCHITECTURAL ADDITION: DYNAMIC TABLE MATERIALIZATION ---
        print(f"[*] Materializing transactional tables inside {schema_name}...")
        
        # 1. Route SQLAlchemy engine to the newly created schema
        db.execute(text(f'SET search_path TO "{schema_name}"'))
        
        # 2. Filter metadata to prevent leaking global tables (like users/tenants) into the tenant schema
        tenant_tables = [
            Base.metadata.tables.get('products'),
            Base.metadata.tables.get('audit_logs')
        ]
        
        # Clean up any None values if imports are missing
        valid_tables = [t for t in tenant_tables if t is not None]
        
        if valid_tables:
            Base.metadata.create_all(bind=db.get_bind(), tables=valid_tables)
        else:
            print("[!] Warning: Missing models. Ensure Product and AuditLog are imported.")
        # -------------------------------------------------------------

        # Re-enforce global context before injecting the user
        db.execute(text('SET search_path TO "public"'))

        print(f"[*] Provisioning Admin Anchor: {admin_email}...")
        admin_in = UserCreate(
            tenant_id=tenant.id,
            email=admin_email,
            password=raw_password,
            full_name=f"Admin {unique_hash}",
            role="admin"
        )
        
        UserService.create(db, user_in=admin_in)
        
        # Final persistence checkpoint
        db.commit()
        
        # Post-execution logs
        print("\n[+] Architecture Provisioned Successfully!")
        print(f"    Tenant Schema : {schema_name}")
        print(f"    Admin Login   : {admin_email}")
        print(f"    Password      : {raw_password}\n")
        
    except Exception as e:
        print(f"[!] Critical failure during provisioning: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    provision_isolated_tenant_and_admin()