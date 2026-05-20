from fastapi import status
from faker import Faker
import uuid
import random
from sqlalchemy import text

from app.models.tenant import Tenant
from app.models.user import User
from app.models.product import Product
from app.core.security import get_password_hash
from app.db.session import Base
from tests.conftest import TEST_ADMIN_PASSWORD

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

    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        username=fake.user_name(),
        email=fake.email(),
        hashed_password=get_password_hash(TEST_ADMIN_PASSWORD),
        role="admin",
        is_active=True
    )
    db.add(user)
    db.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": user.email, "password": TEST_ADMIN_PASSWORD}
    )
    token = login_response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}, tenant.id

def generate_dynamic_product_payload():
    product_name = f"{fake.word().capitalize()} {fake.word().capitalize()}"
    return {
        "name": product_name,
        "sku": fake.unique.ean(length=8), 
        "price": round(random.uniform(10.0, 999.99), 2),
        "promotional_price": None,
        "stock": random.randint(10, 500),
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
    data = response.json()
    assert data["sku"] == payload["sku"]
    assert data["reserved_stock"] == 0
    assert data["is_active"] is True

def test_soft_delete_product_isolation(client, db):
    headers, tenant_id = get_authenticated_headers(client, db)
    payload = generate_dynamic_product_payload()
    
    create_resp = client.post("/api/v1/products/", json=payload, headers=headers)
    product_id = create_resp.json()["id"]
    
    del_resp = client.delete(f"/api/v1/products/{product_id}", headers=headers)
    assert del_resp.status_code == status.HTTP_204_NO_CONTENT
    
    list_resp = client.get("/api/v1/products/", headers=headers)
    assert list_resp.status_code == status.HTTP_200_OK
    items = list_resp.json()["items"]
    assert not any(p["id"] == product_id for p in items)
    
    tenant_slug = db.execute(text("SELECT slug FROM public.tenants WHERE id = :tid"), {"tid": str(tenant_id)}).scalar()
    
    # Architectural Fix: Re-introduced the mandatory 'tenant_' schema prefix 
    # inside the double quotes to properly target the isolated dimension.
    result = db.execute(
        text(f'SELECT deleted_at FROM "tenant_{tenant_slug}".products WHERE id = :pid'), 
        {"pid": product_id}
    ).fetchone()
    
    assert result is not None
    assert result[0] is not None

def test_upload_product_images(client, db):
    """
    Validates multipart form-data handling and active storage strategy integration.
    Includes cryptographic magic bytes validation to bypass anti-spoofing middleware.
    """
    headers, tenant_id = get_authenticated_headers(client, db)
    payload = generate_dynamic_product_payload()
    
    create_resp = client.post("/api/v1/products/", json=payload, headers=headers)
    product_id = create_resp.json()["id"]

    # Mock file upload via HTTP client with valid PNG magic bytes signature
    valid_png_magic_bytes = b"\x89PNG\r\n\x1a\n" + b"mock_data"
    files = [("files", ("test_image.png", valid_png_magic_bytes, "image/png"))]
    upload_resp = client.post(f"/api/v1/products/{product_id}/images", headers=headers, files=files)
    
    assert upload_resp.status_code == status.HTTP_200_OK
    data = upload_resp.json()
    
    assert "images" in data
    assert len(data["images"]) == 1
    assert data["images"][0]["is_main"] is True

def test_partial_update_product_preserves_state(client, db):
    """
    Validates orthogonal PATCH mutation semantics.
    Ensures that omitting fields in the DTO does not result in NULL overwrites
    for existing data, preserving the integrity of the database record.
    """
    headers, tenant_id = get_authenticated_headers(client, db)
    initial_payload = generate_dynamic_product_payload()
    
    # 1. Provision the initial state
    create_resp = client.post("/api/v1/products/", json=initial_payload, headers=headers)
    product_id = create_resp.json()["id"]
    original_sku = create_resp.json()["sku"]
    
    # 2. Execute partial mutation (Price and Stock only)
    mutation_payload = {
        "price": 99.99,
        "stock": 5000
    }
    patch_resp = client.patch(f"/api/v1/products/{product_id}", json=mutation_payload, headers=headers)
    
    assert patch_resp.status_code == status.HTTP_200_OK
    mutated_data = patch_resp.json()
    
    # 3. Assertions: Validate targeted changes
    assert mutated_data["price"] == 99.99
    assert mutated_data["stock"] == 5000
    
    # 4. Assertions: Validate preserved state (Amnesia Prevention)
    assert mutated_data["sku"] == original_sku
    assert mutated_data["name"] == initial_payload["name"]
    assert mutated_data["is_active"] is True

def get_regular_user_headers(client, db):
    """Provisions a standard 'user' role with read-only product privileges."""
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

    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        username=fake.user_name(),
        email=fake.email(),
        hashed_password=get_password_hash(TEST_ADMIN_PASSWORD),
        role="user", # Architectural Fix: Strictly standard role
        is_active=True
    )
    db.add(user)
    db.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": user.email, "password": TEST_ADMIN_PASSWORD}
    )
    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}, tenant.id

def test_regular_user_read_only_access(client, db):
    """
    Validates RBAC restrictions on orthogonal mutation endpoints.
    Ensures standard users can GET but cannot POST or DELETE products.
    """
    admin_headers, tenant_id = get_authenticated_headers(client, db)
    user_headers, user_tenant_id = get_regular_user_headers(client, db)
    
    # Assert GET is permitted
    get_resp = client.get("/api/v1/products/", headers=user_headers)
    assert get_resp.status_code == status.HTTP_200_OK
    
    # Assert POST is Forbidden
    payload = generate_dynamic_product_payload()
    post_resp = client.post("/api/v1/products/", json=payload, headers=user_headers)
    assert post_resp.status_code == status.HTTP_403_FORBIDDEN
    
    # Assert DELETE is Forbidden (using a product created by admin)
    create_resp = client.post("/api/v1/products/", json=payload, headers=admin_headers)
    product_id = create_resp.json()["id"]
    
    del_resp = client.delete(f"/api/v1/products/{product_id}", headers=user_headers)
    assert del_resp.status_code == status.HTTP_403_FORBIDDEN