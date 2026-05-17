from fastapi import status
from faker import Faker
import uuid
from sqlalchemy import text

from app.models.tenant import Tenant
from app.models.user import User
from app.core.security import get_password_hash
from app.db.session import engine, Base

fake = Faker()

def setup_verified_user(db):
    """
    Provisions a complete Tenant and User within the same test transaction.
    Constructs the isolated schema explicitly for the test environment.
    """
    tenant = Tenant(id=uuid.uuid4(), name=fake.company(), slug=fake.slug())
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    schema_name = f"tenant_{tenant.slug}"
    db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
    
    conn = db.connection()
    conn.execute(text(f'SET search_path TO "{schema_name}"'))
    Base.metadata.create_all(bind=conn)
    conn.execute(text('SET search_path TO "public"'))

    raw_password = "SecurePassword123!"
    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        username=fake.user_name(), # Architectural Fix: Injected mandatory identifier
        email=fake.email(),
        hashed_password=get_password_hash(raw_password),
        role="admin",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"email": user.email, "password": raw_password, "tenant_id": tenant.id}

def test_login_success_returns_jwt(client, db):
    credentials = setup_verified_user(db)
    response = client.post(
        "/api/v1/auth/login",
        data={"username": credentials["email"], "password": credentials["password"]}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data

def test_login_failure_wrong_password(client, db):
    credentials = setup_verified_user(db)
    response = client.post(
        "/api/v1/auth/login",
        data={"username": credentials["email"], "password": "WrongPassword456!"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED