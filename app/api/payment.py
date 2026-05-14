from fastapi import APIRouter, Request, HTTPException, Header, Depends
from sqlalchemy.orm import Session
import stripe

from app.core.config import settings
from app.db.session import get_db
from app.services.tenant import TenantService
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.payment import CheckoutSessionRequest, CheckoutSessionResponse
from app.services.stripe_service import StripeService

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
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid cryptographic signature")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload format")

    event_type = event.get('type')
    
    if event_type == 'customer.created':
        customer = event['data']['object']
        print(f"✅ [WEBHOOK] Customer {customer.get('id')} provisioned successfully.")
        
    elif event_type in ['customer.deleted', 'customer.subscription.deleted']:
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


@router.post("/checkout", response_model=CheckoutSessionResponse)
def create_checkout(
    request: CheckoutSessionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generates a secure Stripe Checkout URL for the current tenant.
    """
    try:
        checkout_url = StripeService.create_checkout_session(
            tenant_id=str(current_user.tenant_id),
            price_id=request.price_id,
            success_url=request.success_url,
            cancel_url=request.cancel_url
        )
        return CheckoutSessionResponse(checkout_url=checkout_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))