from fastapi import status
from faker import Faker
import uuid
from unittest.mock import patch
import stripe
from sqlalchemy import text

from app.models.tenant import Tenant
from app.db.session import engine, Base

fake = Faker()

def test_webhook_missing_signature(client):
    response = client.post("/api/v1/payments/webhook", json={"dummy": "data"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST

@patch("stripe.Webhook.construct_event")
def test_webhook_invalid_signature(mock_construct_event, client):
    mock_construct_event.side_effect = stripe.error.SignatureVerificationError("Invalid signature", "sig")
    response = client.post("/api/v1/payments/webhook", headers={"Stripe-Signature": "forged_signature_123"}, json={})
    assert response.status_code == status.HTTP_400_BAD_REQUEST

@patch("stripe.Webhook.construct_event")
def test_webhook_customer_deleted_suspends_tenant(mock_construct_event, client, db):
    fake_stripe_id = f"cus_{uuid.uuid4().hex[:14]}"
    tenant = Tenant(id=uuid.uuid4(), name=fake.company(), slug=fake.slug(), stripe_customer_id=fake_stripe_id, is_active=True)
    db.add(tenant)
    db.commit()

    schema_name = f"tenant_{tenant.slug}"
    db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
    
    conn = db.connection()
    conn.execute(text(f'SET search_path TO "{schema_name}"'))
    Base.metadata.create_all(bind=conn)
    conn.execute(text('SET search_path TO "public"'))

    mock_event = {"type": "customer.subscription.deleted", "data": {"object": {"customer": fake_stripe_id}}}
    mock_construct_event.return_value = mock_event

    response = client.post("/api/v1/payments/webhook", headers={"Stripe-Signature": "dummy_valid_signature"}, json={})

    assert response.status_code == status.HTTP_200_OK
    db.refresh(tenant)
    assert tenant.is_active is False