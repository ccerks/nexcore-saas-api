import stripe
from app.core.config import settings

# Initialize the Stripe SDK with the secure environment key
stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeService:
    
    @staticmethod
    def create_customer(email: str, name: str, tenant_id: str) -> str:
        """
        Provisions a new Customer entity within the Stripe ecosystem.
        Stores the internal tenant_id in Stripe's metadata for cross-referencing and auditing.
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={
                    "tenant_id": str(tenant_id)
                }
            )
            return customer.id
            
        except stripe.error.StripeError as e:
            # In a production environment, this should log to a monitoring service (e.g., Sentry)
            raise ValueError(f"Stripe Integration Error: {str(e)}")
        
    @staticmethod
    def create_checkout_session(tenant_id: str, price_id: str, success_url: str, cancel_url: str) -> str:
        """
        Creates a Stripe Checkout Session for a tenant subscription.
        """
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=tenant_id, # Crucial: Maps the payment back to our Tenant
                metadata={"tenant_id": tenant_id}
            )
            return session.url
        except Exception as e:
            raise ValueError(f"Stripe Session Error: {str(e)}")