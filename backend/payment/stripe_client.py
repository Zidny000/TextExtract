import os
import logging
import stripe

logger = logging.getLogger(__name__)

# Initialize Stripe client
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

def create_checkout_session(customer_email, plan_name, plan_id, price_amount, currency="usd", transaction_id=None):
    """Create a Stripe checkout session for subscription payment"""
    try:
        # Create or get Stripe customer
        customers = stripe.Customer.list(email=customer_email, limit=1)
        if customers.data:
            customer = customers.data[0]
        else:
            customer = stripe.Customer.create(email=customer_email)
            
        # Create a checkout session
        success_url = f"{FRONTEND_URL}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}&transaction_id={transaction_id}"
        cancel_url = f"{FRONTEND_URL}/subscription/cancel"
        
        checkout_session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': currency,
                    'product_data': {
                        'name': f'TextExtract {plan_name} Plan',
                        'description': f'Subscription to TextExtract {plan_name} Plan'
                    },
                    'unit_amount': int(price_amount * 100),  # Stripe uses cents
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'plan_id': plan_id,
                'transaction_id': transaction_id
            }
        )
        
        return checkout_session
        
    except Exception as e:
        logger.error(f"Error creating Stripe checkout session: {str(e)}")
        raise

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
