from fastapi import status
from faker import Faker
import uuid
from app.models.tenant import Tenant
from app.models.user import User
from app.core.security import get_password_hash

fake = Faker()

def setup_verified_user(db):
    """
    Provisions a complete Tenant and an active User with a known password.
    Returns the user credentials needed to perform login requests.
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
    db.refresh(user)

    return {"email": user.email, "password": raw_password, "tenant_id": tenant.id}

def test_login_success_returns_jwt(client, db):
    """
    Verifies that a valid user can authenticate and receive a JWT token.
    """
    credentials = setup_verified_user(db)
    
    response = client.post(
        "/api/v1/auth/login",
        data={"username": credentials["email"], "password": credentials["password"]}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_failure_wrong_password(client, db):
    """
    Verifies that authentication fails gracefully with invalid credentials.
    """
    credentials = setup_verified_user(db)
    
    response = client.post(
        "/api/v1/auth/login",
        data={"username": credentials["email"], "password": "WrongPassword456!"}
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Incorrect email or password"