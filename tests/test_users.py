from fastapi import status
from faker import Faker
import uuid

from app.models.tenant import Tenant

fake = Faker()

def create_dummy_tenant(db):
    """
    Helper function to provision a transient tenant in the test database.
    Required because users must be relationally linked to a valid tenant_id.
    """
    tenant = Tenant(
        id=uuid.uuid4(), 
        name=fake.company(), 
        slug=fake.slug()
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant

def test_create_user_success(client, db):
    """
    Verifies that a valid user can be created successfully with dynamic data.
    Ensures the user is correctly linked to an existing Tenant.
    """
    tenant = create_dummy_tenant(db)
    test_email = fake.email()
    test_password = fake.password(length=12, special_chars=True, digits=True, upper_case=True, lower_case=True)
    
    response = client.post(
        "/api/v1/users/",
        json={
            "tenant_id": str(tenant.id),
            "email": test_email, 
            "password": test_password
        }
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == test_email
    assert data["tenant_id"] == str(tenant.id)
    assert "id" in data

def test_create_user_rate_limit(client, db):
    """
    Verifies that the API blocks mass account creation (Rate Limiting).
    Provides all required Pydantic fields (tenant_id) to bypass 422 errors
    and strictly test the 429 Too Many Requests limit.
    """
    tenant = create_dummy_tenant(db)

    # Send 5 valid requests (filling the rate limit bucket)
    for _ in range(5):
        payload = {
            "tenant_id": str(tenant.id),
            "email": fake.email(), 
            "password": fake.password(length=12, special_chars=True, digits=True, upper_case=True, lower_case=True)
        }
        client.post("/api/v1/users/", json=payload)
        
    # The 6th request must be blocked by SlowAPI
    final_payload = {
        "tenant_id": str(tenant.id),
        "email": fake.email(), 
        "password": fake.password(length=12, special_chars=True, digits=True, upper_case=True, lower_case=True)
    }
    response = client.post("/api/v1/users/", json=final_payload)
    
    # Asserting the specific response format of slowapi
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "error" in response.json()
    assert "Rate limit exceeded" in response.json()["error"]