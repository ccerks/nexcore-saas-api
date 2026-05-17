import sys
import os
import uuid
from sqlalchemy import text

# PATH INJECTION: Must occur before any 'app' imports to resolve ModuleNotFoundError
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocal
from app.schemas.tenant import TenantCreate
from app.services.tenant import TenantService

def provision_isolated_tenant() -> None:
    """
    Lightweight CLI trigger.
    Full orchestration (Schema, Admin, Auth, Audits) is delegated to TenantService.
    Parses the returned dictionary to display generated master credentials and identifiers.
    """
    db = SessionLocal()
    try:
        db.execute(text('SET search_path TO "public"'))
        
        u_hash = uuid.uuid4().hex[:6]
        store_name = f"NexCore Store {u_hash}"
        slug = f"store-{u_hash}"

        print(f"[*] Delegating full orchestration to TenantService for: {store_name}...")
        tenant_in = TenantCreate(name=store_name, slug=slug)
        
        result = TenantService.create(db, tenant_in=tenant_in)
        
        # Architectural UX Fix: Predictably derive and display the mandatory username
        master_username = f"master_{result['slug'].replace('-', '_')}"

        print("\n[+] Architecture Provisioned Successfully!")
        print(f"    Tenant Schema   : tenant_{result['slug']}")
        print(f"    Master Username : {master_username}")
        print(f"    Master Login    : {result['master_email']}")
        print(f"    Password        : {result['temporary_password']}")
        print(f"    Security Lock   : Expires in {result['expires_in']}\n")

    except Exception as e:
        print(f"[!] Critical failure during provisioning: {e}")
        db.rollback()
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    provision_isolated_tenant()