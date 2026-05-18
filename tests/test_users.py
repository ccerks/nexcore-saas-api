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
# Architectural Fix: DRY compliance via centralized test credentials
from tests.conftest import TEST_ADMIN_PASSWORD

fake = Faker()

def setup_admin_headers(client, db) -> dict:
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

    admin_email = fake.email()
    admin_user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        username=fake.user_name(), 
        email=admin_email,
        hashed_password=get_password_hash(TEST_ADMIN_PASSWORD),
        role="admin",
        is_active=True
    )
    db.add(admin_user)
    db.commit()

    token = jwt.encode(
        {"sub": admin_email}, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    
    return {"Authorization": f"Bearer {token}"}

def test_create_user_success(client, db):
    headers = setup_admin_headers(client, db)
    
    test_username = fake.user_name()
    test_email = fake.email()
    
    response = client.post(
        "/api/v1/users/employee",
        json={"username": test_username, "email": test_email, "password": TEST_ADMIN_PASSWORD, "full_name": "Staff User"},
        headers=headers
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["username"] == test_username

def test_create_user_rate_limit(client, db):
    headers = setup_admin_headers(client, db)
    payload = {"username": fake.user_name(), "email": fake.email(), "password": TEST_ADMIN_PASSWORD}
    
    for _ in range(5):
        client.post("/api/v1/users/employee", json=payload, headers=headers)
        
    response = client.post("/api/v1/users/employee", json=payload, headers=headers)
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS