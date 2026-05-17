from fastapi import status
from faker import Faker
import uuid
import random
from sqlalchemy import text

from app.models.tenant import Tenant
from app.models.user import User
from app.core.security import get_password_hash
from app.db.session import engine, Base

fake = Faker()

def get_authenticated_headers(client, db):
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
        username=fake.user_name(), # Architectural Fix
        email=fake.email(),
        hashed_password=get_password_hash(raw_password),
        role="admin",
        is_active=True
    )
    db.add(user)
    db.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": user.email, "password": raw_password}
    )
    token = login_response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}, tenant.id

def generate_dynamic_product_payload():
    """Architectural Fix: Replaced legacy sku_pai with consolidated sku"""
    product_name = f"{fake.word().capitalize()} {fake.word().capitalize()}"
    return {
        "name": product_name,
        "sku": fake.unique.ean(length=8), 
        "price": round(random.uniform(10.0, 999.99), 2),
        "attributes": {
            "color": fake.color_name(), 
            "size": random.choice(['S', 'M', 'L', 'XL'])
        }
    }

def test_create_product_success(client, db):
    headers, tenant_id = get_authenticated_headers(client, db)
    payload = generate_dynamic_product_payload()
    response = client.post("/api/v1/products/", json=payload, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED

def test_bulk_create_products_success(client, db):
    headers, tenant_id = get_authenticated_headers(client, db)
    bulk_payload = [generate_dynamic_product_payload() for _ in range(5)]
    response = client.post("/api/v1/products/bulk", json=bulk_payload, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED