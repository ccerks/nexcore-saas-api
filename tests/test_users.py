import uuid
import jwt
from fastapi import status
from sqlalchemy import text
from faker import Faker

from app.models.tenant import Tenant
from app.models.user import User
from app.core.security import get_password_hash
from app.db.session import Base
from app.core.config import settings

fake = Faker()

def setup_admin_headers(client, db) -> dict:
    """
    Provisions a test Tenant, isolated Schema, and an Admin User.
    Architectural Fix: Bypasses the /login endpoint to avoid SlowAPI rate limits 
    during test execution by securely forging the JWT token using system keys.
    """
    # 1. Provision Tenant
    tenant = Tenant(id=uuid.uuid4(), name=fake.company(), slug=fake.slug())
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    # 2. Provision Isolated Schema
    schema_name = f"tenant_{tenant.slug}"
    db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
    conn = db.connection()
    conn.execute(text(f'SET search_path TO "{schema_name}"'))
    Base.metadata.create_all(bind=conn)
    conn.execute(text('SET search_path TO "public"'))

    # 3. Provision Global Admin
    raw_password = "SecurePassword123!"
    admin_email = fake.email()
    admin_user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email=admin_email,
        hashed_password=get_password_hash(raw_password),
        role="admin",
        is_active=True
    )
    db.add(admin_user)
    db.commit()

    # 4. Direct JWT Generation (Bypasses HTTP Rate Limits)
    token = jwt.encode(
        {"sub": admin_email}, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    
    return {"Authorization": f"Bearer {token}"}


def test_create_user_success(client, db):
    """
    Validates employee creation via the secure '/employee' route.
    """
    headers = setup_admin_headers(client, db)
    
    test_email = fake.email()
    test_password = "SecurePassword123!"
    
    response = client.post(
        "/api/v1/users/employee",
        json={"email": test_email, "password": test_password, "full_name": "Staff User"},
        headers=headers
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["email"] == test_email


def test_create_user_rate_limit(client, db):
    """
    Verifies Redis-based rate limiting on sensitive user creation endpoints.
    """
    headers = setup_admin_headers(client, db)
    payload = {"email": fake.email(), "password": "Password123!"}
    
    for _ in range(5):
        client.post("/api/v1/users/employee", json=payload, headers=headers)
        
    response = client.post("/api/v1/users/employee", json=payload, headers=headers)
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS