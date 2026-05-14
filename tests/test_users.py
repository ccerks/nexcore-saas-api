from fastapi import status
from faker import Faker
import uuid
from sqlalchemy import text

from app.models.tenant import Tenant
from app.db.session import engine, Base

fake = Faker()

def create_dummy_tenant(db):
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

    return tenant

def test_create_user_success(client, db):
    tenant = create_dummy_tenant(db)
    test_email = fake.email()
    test_password = fake.password(length=12, special_chars=True, digits=True, upper_case=True, lower_case=True)
    
    response = client.post(
        "/api/v1/users/",
        json={"tenant_id": str(tenant.id), "email": test_email, "password": test_password}
    )
    assert response.status_code == status.HTTP_201_CREATED

def test_create_user_rate_limit(client, db):
    tenant = create_dummy_tenant(db)

    for _ in range(5):
        payload = {
            "tenant_id": str(tenant.id),
            "email": fake.email(), 
            "password": fake.password(length=12, special_chars=True, digits=True, upper_case=True, lower_case=True)
        }
        client.post("/api/v1/users/", json=payload)
        
    final_payload = {
        "tenant_id": str(tenant.id),
        "email": fake.email(), 
        "password": fake.password(length=12, special_chars=True, digits=True, upper_case=True, lower_case=True)
    }
    response = client.post("/api/v1/users/", json=final_payload)
    
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS