import sys
import os
import getpass
from sqlalchemy import text

# PATH INJECTION: Must occur before any 'app' imports to resolve ModuleNotFoundError
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocal
from app.services.user import UserService
from app.schemas.user import UserCreate

def provision_superadmin() -> None:
    """
    Secure CLI tool for bootstrapping global Superadmin accounts.
    Enforces the mandatory unique username requirement.
    """
    print("\n" + "="*45)
    print(" 🛡️  NexCore Global Superadmin Bootstrap  🛡️")
    print("="*45 + "\n")
    
    username = input("Enter Unique Username: ").strip()
    email = input("Enter Superadmin Email: ").strip()

    password = getpass.getpass("Enter Strong Password (Hidden): ")
    confirm_password = getpass.getpass("Confirm Password (Hidden): ")

    if password != confirm_password:
        print("\n[!] Error: Passwords do not match. Aborting provisioning.")
        return

    db = SessionLocal()
    try:
        db.execute(text('SET search_path TO "public"'))

        if db.query(text("1")).from_statement(text("SELECT 1 FROM public.users WHERE username = :u")).params(u=username).scalar():
            print(f"\n[!] Error: The username '{username}' is already taken.")
            return

        existing_user = UserService.get_by_email(db, email=email)
        if existing_user:
            print(f"\n[!] Error: The identity '{email}' already exists in the system.")
            return

        print(f"\n[*] Provisioning global authority for: {username}...")

        superadmin_in = UserCreate(
            tenant_id=None,
            username=username,
            email=email,
            password=password,
            full_name="Global Super Administrator",
            role="superadmin"
        )

        user = UserService.create(db, user_in=superadmin_in)

        print("\n[+] Superadmin Provisioned Successfully!")
        print(f"    UUID     : {user.id}")
        print(f"    Username : {user.username}")
        print(f"    Email    : {user.email}\n")

    except ValueError as ve:
        print(f"\n[!] Validation Error: {ve}")
    except Exception as e:
        print(f"\n[!] Critical failure during provisioning: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    provision_superadmin()