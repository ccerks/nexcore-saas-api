from fastapi import APIRouter, Request, HTTPException, Header, Depends
from sqlalchemy.orm import Session
import stripe

from app.core.config import settings
from app.db.session import get_db
from app.services.tenant import TenantService

router = APIRouter()

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db)
):
    """
    Stripe Webhook endpoint.
    Validates signature and processes asynchronous billing events to update Tenant status.
    """
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature header")

    payload = await request.body()
    
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid cryptographic signature")
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload format")

    event_type = event['type']
    
    if event_type == 'customer.created':
        customer = event['data']['object']
        print(f"✅ [WEBHOOK] Customer {customer['id']} provisioned successfully.")
        
    elif event_type == 'customer.deleted' or event_type == 'customer.subscription.deleted':
        # The object varies slightly depending on the event, but both contain the customer ID
        obj = event['data']['object']
        stripe_customer_id = obj.get('customer') if event_type == 'customer.subscription.deleted' else obj.get('id')
        
        tenant = TenantService.get_by_stripe_id(db, stripe_customer_id)
        
        if tenant:
            TenantService.set_active_status(db, tenant, is_active=False)
            print(f"❌ [WEBHOOK] Tenant '{tenant.name}' deactivated due to billing cancellation.")
        else:
            print(f"⚠️ [WEBHOOK] Stripe Customer {stripe_customer_id} not found in database.")
            
    else:
        print(f"⚠️ [WEBHOOK] Unhandled event type: {event_type}")

    return {"status": "success"}