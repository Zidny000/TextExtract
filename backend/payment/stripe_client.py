import os
import logging
import stripe

logger = logging.getLogger(__name__)

# Initialize Stripe client
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

def create_checkout_session(customer_email, plan_id, price_id):
    """Create a Stripe checkout session for subscription payment"""
    try:
        # Create or get Stripe customer
        customers = stripe.Customer.list(email=customer_email, limit=1)
        if customers.data:
            customer = customers.data[0]
        else:
            customer = stripe.Customer.create(email=customer_email)
            
        # Create a checkout session
        success_url = f"{FRONTEND_URL}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{FRONTEND_URL}/subscription/cancel"
        
        checkout_session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'plan_id': plan_id,
            }
        )
        
        return checkout_session
        
    except Exception as e:
        logger.error(f"Error creating Stripe checkout session: {str(e)}")
        raise
    
def get_subscription_details(sub_id):
    """Retrieve subscription details from Stripe"""
    try:
        subscription = stripe.Subscription.retrieve(sub_id)
        return subscription
    except Exception as e:
        logger.error(f"Error retrieving subscription details: {str(e)}")
        return None

def verify_stripe_webhook(payload, signature):
    """Verify a Stripe webhook signature"""
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, STRIPE_WEBHOOK_SECRET
        )
        return event
    except ValueError as e:
        logger.error(f"Invalid payload: {str(e)}")
        return None
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {str(e)}")
        return None

class StripeClient:
    """Client for handling Stripe operations"""
    
    def __init__(self):
        self.api_key = os.environ.get('STRIPE_SECRET_KEY')
        stripe.api_key = self.api_key
        
    def create_setup_intent(self, user_email):
        """Create a setup intent for saving payment method"""
        try:
            # Create or get Stripe customer
            customers = stripe.Customer.list(email=user_email, limit=1)
            if customers.data:
                customer = customers.data[0]
            else:
                customer = stripe.Customer.create(email=user_email)
            
            # Create setup intent
            setup_intent = stripe.SetupIntent.create(
                customer=customer.id,
                payment_method_types=['card'],
                usage='off_session'
            )
            
            return {
                'success': True,
                'setup_intent_id': setup_intent.id,
                'client_secret': setup_intent.client_secret
            }
            
        except Exception as e:
            logger.error(f"Error creating setup intent: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
            
    def charge_subscription(self, user_id, payment_method_id, amount, currency, description):
        """Charge a payment method for subscription renewal"""
        try:
            # In a real implementation, this would use the payment method to charge
            # For now, we'll simulate a successful payment
            
            # A real implementation would look something like:
            # payment_intent = stripe.PaymentIntent.create(
            #    amount=int(amount * 100),  # Stripe uses cents
            #    currency=currency,
            #    payment_method=payment_method_id,
            #    confirm=True,
            #    off_session=True,
            #    description=description
            # )
            
            # For demo, always return success
            return {
                'success': True,
                'transaction_id': f'sim_{os.urandom(8).hex()}',
                'status': 'succeeded'
            }
            
        except Exception as e:
            logger.error(f"Error charging subscription: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
