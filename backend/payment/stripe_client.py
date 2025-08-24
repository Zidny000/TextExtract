import os
import logging
import stripe

logger = logging.getLogger(__name__)

# Initialize Stripe client
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

def create_checkout_session(customer_name, customer_email, plan_id, price_id):
    """Create a Stripe checkout session for subscription payment"""
    try:
        # Create or get Stripe customer
        customers = stripe.Customer.list(email=customer_email, limit=1)
        if customers.data:
            customer = customers.data[0]
        else:
            customer = stripe.Customer.create(email=customer_email,name=customer_name)

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
            },
            # automatic_tax={
            #   'enabled': True
            # },

        )
        
        return checkout_session
        
    except Exception as e:
        logger.error(f"Error creating Stripe checkout session: {str(e)}")
        raise

def create_buy_credit_checkout_session(customer_name, customer_email, user_id, amount, price):
    """Create a Stripe checkout session for buying credits"""
    try:
        # Create or get Stripe customer
        customers = stripe.Customer.list(email=customer_email, limit=1)
        if customers.data:
            customer = customers.data[0]
        else:
            customer = stripe.Customer.create(email=customer_email,name=customer_name)

        # Create a checkout session
        success_url = f"{FRONTEND_URL}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{FRONTEND_URL}/subscription/cancel"
        
        checkout_session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': "usd",
                    'product_data': {
                        'name': f'TextExtract {amount} OCR Requests',
                        'description': f'Purchase {amount} TextExtract OCR Requests'
                    },
                    'unit_amount': int(price * 100),  # Stripe uses cents
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'user_id': user_id,
                'amount': amount,
            },
            # automatic_tax={
            #   'enabled': True
            # },

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
    
def cancel_stripe_subscription(sub_id):
    """Cancel a subscription in Stripe"""
    try:
        stripe.Subscription.cancel(sub_id)
        return True
    except Exception as e:
        logger.error(f"Error canceling subscription: {str(e)}")
        return False

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

def create_billing_portal(customer_email):
    """Create a Stripe billing portal session"""
    try:
        # Create or get Stripe customer
        customers = stripe.Customer.list(email=customer_email, limit=1)
        if customers.data:
            customer = customers.data[0]
        else:
            logger.error(f"Error creating billing portal session: {str(e)}")
            return {
                'success': False,
                'error': 'Customer not found'
            }

        # Create a billing portal session
        session = stripe.billing_portal.Session.create(
            customer=customer.id,
            return_url=f"{FRONTEND_URL}/subscription"
        )

        return {
            'success': True,
            'url': session.url
        }

    except Exception as e:
        logger.error(f"Error creating billing portal session: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }