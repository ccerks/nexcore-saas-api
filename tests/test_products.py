from fastapi import status
from faker import Faker
import uuid
import random
from app.models.tenant import Tenant
from app.models.user import User
from app.core.security import get_password_hash

fake = Faker()

def get_authenticated_headers(client, db):
    """
    Provisions a complete Tenant and User, performs login, 
    and returns the Authorization headers and Tenant ID.
    """
    tenant = Tenant(id=uuid.uuid4(), name=fake.company(), slug=fake.slug())
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    raw_password = "SecurePassword123!"
    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
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
    """
    Factory function to generate completely random and unique product payloads.
    Uses standard Faker methods to ensure compatibility without extra plugins.
    """
    product_name = f"{fake.word().capitalize()} {fake.word().capitalize()}"
    return {
        "name": product_name,
        "sku_pai": fake.unique.ean(length=8),
        "price": round(random.uniform(10.0, 999.99), 2),
        "attributes": {
            "color": fake.color_name(), 
            "size": random.choice(['S', 'M', 'L', 'XL'])
        }
    }

def test_create_product_success(client, db):
    """Verifies single product creation with dynamic data."""
    headers, tenant_id = get_authenticated_headers(client, db)
    payload = generate_dynamic_product_payload()
    
    response = client.post("/api/v1/products/", json=payload, headers=headers)
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["sku_pai"] == payload["sku_pai"]

def test_bulk_create_products_success(client, db):
    """
    Verifies the bulk insertion endpoint (Horde Encounter).
    Ensures multiple products can be created in a single network request.
    """
    headers, tenant_id = get_authenticated_headers(client, db)
    
    # Generate a list of 5 random products
    bulk_payload = [generate_dynamic_product_payload() for _ in range(5)]
    
    response = client.post("/api/v1/products/bulk", json=bulk_payload, headers=headers)
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 5
    assert data[0]["tenant_id"] == str(tenant_id)