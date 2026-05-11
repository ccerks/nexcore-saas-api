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