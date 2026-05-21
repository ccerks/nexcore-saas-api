from fastapi import APIRouter, Request, HTTPException, Header, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import stripe

from app.core.config import settings
from app.db.session import get_db
from app.services.tenant import TenantService
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.payment import CheckoutSessionRequest, CheckoutSessionResponse
from app.services.stripe_service import StripeService
from app.services.discord import DiscordService

router = APIRouter()


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db)
):
    """
    Stripe Webhook endpoint — Full billing lifecycle handler.

    Architectural justification: This endpoint intentionally bypasses the standard
    JWT authentication dependency. Stripe authenticates via cryptographic HMAC signature
    verification (Stripe-Signature header), which is a stronger trust model for
    machine-to-machine communication than user-issued tokens.

    The handler operates exclusively on the 'public' schema (global tenant map),
    never touching tenant-scoped schemas. All mutations are atomic ORM updates
    to guarantee consistency under duplicate webhook delivery (idempotency).
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

    event_type = event.get("type")

    # Architectural Shield: Force the session to the global schema before
    # any service method executes, preventing stale search_path leakage
    # from a previous request in the same connection pool slot.
    db.execute(text('SET search_path TO "public"'))

    # -------------------------------------------------------------------------
    # checkout.session.completed
    # Fired when a customer successfully completes a Stripe Checkout payment.
    # This is the primary activation trigger for new subscriptions.
    # -------------------------------------------------------------------------
    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        tenant_id = session.get("client_reference_id")
        stripe_subscription_id = session.get("subscription")

        if not tenant_id:
            # Defensive guard: if client_reference_id was not set during checkout
            # creation, we cannot resolve the tenant. Log and return 200 to prevent
            # Stripe from retrying an unresolvable event.
            DiscordService.send_alert(
                "⚠️ **Webhook Warning** `checkout.session.completed`\n"
                "Missing `client_reference_id` — tenant could not be resolved."
            )
            return {"status": "ignored", "reason": "missing client_reference_id"}

        tenant = TenantService.activate_subscription(
            db=db,
            tenant_id=tenant_id,
            stripe_subscription_id=stripe_subscription_id
        )

        if tenant:
            DiscordService.send_alert(
                f"💳 **Subscription Activated**\n"
                f"**Tenant:** {tenant.name} (`{tenant.slug}`)\n"
                f"**Subscription ID:** `{stripe_subscription_id}`"
            )
        else:
            DiscordService.send_alert(
                f"⚠️ **Webhook Warning** `checkout.session.completed`\n"
                f"Tenant ID `{tenant_id}` not found in database."
            )

    # -------------------------------------------------------------------------
    # invoice.payment_succeeded
    # Fired on every successful renewal charge.
    # Restores access if the tenant was previously suspended by a failed payment.
    # -------------------------------------------------------------------------
    elif event_type == "invoice.payment_succeeded":
        invoice = event["data"]["object"]
        stripe_customer_id = invoice.get("customer")

        tenant = TenantService.reactivate(db=db, stripe_customer_id=stripe_customer_id)

        if tenant:
            DiscordService.send_alert(
                f"✅ **Payment Succeeded — Tenant Reactivated**\n"
                f"**Tenant:** {tenant.name} (`{tenant.slug}`)\n"
                f"**Amount:** ${invoice.get('amount_paid', 0) / 100:.2f} {invoice.get('currency', 'usd').upper()}"
            )

    # -------------------------------------------------------------------------
    # invoice.payment_failed
    # Fired when Stripe cannot charge the customer's payment method.
    # Suspends tenant access until payment is resolved or subscription is cancelled.
    # -------------------------------------------------------------------------
    elif event_type == "invoice.payment_failed":
        invoice = event["data"]["object"]
        stripe_customer_id = invoice.get("customer")

        tenant = TenantService.suspend(db=db, stripe_customer_id=stripe_customer_id)

        if tenant:
            DiscordService.send_alert(
                f"❌ **Payment Failed — Tenant Suspended**\n"
                f"**Tenant:** {tenant.name} (`{tenant.slug}`)\n"
                f"**Next retry:** Stripe will automatically retry the charge.\n"
                f"**Action required:** Customer must update payment method."
            )
        else:
            DiscordService.send_alert(
                f"⚠️ **Webhook Warning** `invoice.payment_failed`\n"
                f"Stripe Customer `{stripe_customer_id}` not found in database."
            )

    # -------------------------------------------------------------------------
    # customer.subscription.updated
    # Fired on plan changes and status transitions (active → past_due, etc.).
    # We react only to status changes, not price/quantity changes (out of scope).
    # -------------------------------------------------------------------------
    elif event_type == "customer.subscription.updated":
        subscription = event["data"]["object"]
        stripe_customer_id = subscription.get("customer")
        new_status = subscription.get("status")

        if new_status in ("past_due", "unpaid", "paused"):
            tenant = TenantService.suspend(db=db, stripe_customer_id=stripe_customer_id)
            if tenant:
                DiscordService.send_alert(
                    f"⚠️ **Subscription Status Change**\n"
                    f"**Tenant:** {tenant.name} (`{tenant.slug}`)\n"
                    f"**New Status:** `{new_status}` — access suspended."
                )
        elif new_status == "active":
            tenant = TenantService.reactivate(db=db, stripe_customer_id=stripe_customer_id)
            if tenant:
                DiscordService.send_alert(
                    f"✅ **Subscription Reactivated**\n"
                    f"**Tenant:** {tenant.name} (`{tenant.slug}`)\n"
                    f"**Status:** `{new_status}`"
                )

    # -------------------------------------------------------------------------
    # customer.subscription.deleted
    # Fired when a subscription is fully cancelled (not just paused/past_due).
    # Terminal state: deactivates tenant and clears the subscription reference.
    # -------------------------------------------------------------------------
    elif event_type in ("customer.subscription.deleted", "customer.deleted"):
        obj = event["data"]["object"]
        stripe_customer_id = (
            obj.get("customer")
            if event_type == "customer.subscription.deleted"
            else obj.get("id")
        )

        tenant = TenantService.clear_subscription(db=db, stripe_customer_id=stripe_customer_id)

        if tenant:
            DiscordService.send_alert(
                f"🚫 **Subscription Cancelled — Tenant Deactivated**\n"
                f"**Tenant:** {tenant.name} (`{tenant.slug}`)\n"
                f"**Event:** `{event_type}`"
            )

    else:
        # Non-critical events (e.g., customer.updated, payment_method.attached)
        # are silently acknowledged to avoid Stripe retry storms.
        print(f"[WEBHOOK] Unhandled event type acknowledged: {event_type}")

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
