import logging
from flask import Blueprint, request, jsonify, g
from auth import login_required
from database.db import supabase
from database.models import User, SubscriptionPlan, PaymentTransaction, Subscription
from payment.stripe_client import create_checkout_session, verify_stripe_webhook, STRIPE_PUBLIC_KEY
import datetime
import stripe
import os
import uuid

logger = logging.getLogger(__name__)
stripe_routes = Blueprint('stripe', __name__, url_prefix='/stripe')

@stripe_routes.route('/public-key', methods=['GET'])
def get_public_key():
    """Get Stripe public key for frontend integration"""
    return jsonify({"publicKey": STRIPE_PUBLIC_KEY})

@stripe_routes.route('/create-checkout', methods=['POST'])
@login_required
def create_stripe_checkout():
    """Create a Stripe checkout session for subscription payment"""
    try:
        data = request.json
        
        if not data or "transaction_id" not in data:
            return jsonify({"error": "Transaction ID is required"}), 400
            
        transaction_id = data["transaction_id"]
        
        # Get the transaction
        response = supabase.table("payment_transactions").select("*").eq("id", transaction_id).execute()
        if len(response.data) == 0:
            return jsonify({"error": "Transaction not found"}), 404
            
        transaction = response.data[0]
        
        # Get the plan
        plan = SubscriptionPlan.get_by_id(transaction["plan_id"])
        if not plan:
            return jsonify({"error": "Plan not found"}), 404
            
        # Get the user
        user = User.get_by_id(g.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        # Update transaction provider to stripe
        PaymentTransaction.update_status(
            transaction_id,
            "pending",
            payment_provider="stripe"
        )
        
        # Create checkout session
        checkout_session = create_checkout_session(
            customer_email=user["email"],
            plan_name=plan["name"],
            plan_id=plan["id"],
            price_amount=float(transaction["amount"]),
            currency=transaction["currency"].lower(),
            transaction_id=transaction_id
        )
        
        return jsonify({
            "success": True,
            "checkout_url": checkout_session.url,
            "session_id": checkout_session.id
        })
        
    except Exception as e:
        logger.error(f"Error creating Stripe checkout: {str(e)}")
        return jsonify({"error": "Failed to create checkout session"}), 500

@stripe_routes.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    try:
        payload = request.data
        signature = request.headers.get('Stripe-Signature')

        print(f"Received Stripe webhook with signature: {signature}")
        
        event = verify_stripe_webhook(payload, signature)
        
        if not event:
            return jsonify({"error": "Invalid Stripe signature"}), 400
            
        # Handle the event based on its type
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            
            # Extract metadata
            plan_id = session.get('metadata', {}).get('plan_id')
            
            # Get the plan
            plan = SubscriptionPlan.get_by_id(plan_id)
            if not plan:
                logger.error(f"Plan {plan_id} not found")
                return jsonify({"error": "Plan not found"}), 404
            
            # Calculate subscription dates
            subscription_start = datetime.datetime.now().isoformat()
            subscription_end = (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat()
            
            # Create or update subscription
            subscription = Subscription.create(
                user_id=g.user.id,
                plan_id=plan_id,
                status="active",
                start_date=subscription_start,
                end_date=subscription_end,
                renewal_date=subscription_end,
            )
            
            if not subscription:
                logger.error(f"Failed to create subscription for user {g.user.id}")
                return jsonify({"error": "Failed to create subscription"}), 500
            
            # Update user record with new plan type
            updated_user = User.update_subscription(
                g.user.id,
                plan["name"]
            )
            
            if not updated_user:
                logger.error(f"Failed to update user {g.user.id}")
                return jsonify({"error": "Failed to update user record"}), 500
            
            return jsonify({"success": True}), 200
        
        # Return a 200 for other event types we're not handling
        return jsonify({"success": True}), 200
    
    except Exception as e:
        logger.error(f"Error processing Stripe webhook: {str(e)}")
        return jsonify({"error": "Error processing webhook"}), 500

@stripe_routes.route('/success', methods=['GET'])
@login_required
def stripe_success():
    """Handle successful Stripe payment"""
    try:
        plan_id = request.args.get('plan_id')

        # Get the plan
        plan = SubscriptionPlan.get_by_id(plan_id)
        if not plan:
            return jsonify({"error": "Plan not found"}), 404
        
        # Calculate subscription dates
        subscription_start = datetime.datetime.now().isoformat()
        subscription_end = (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat()
        
        
        return jsonify({
            "success": True,
            "message": f"Successfully upgraded to {plan['name']} plan",
            "plan": plan,
            "subscription": {
                "status": "active",
                "start_date": subscription_start,
                "end_date": subscription_end
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error handling Stripe success: {str(e)}")
        return jsonify({"error": "Failed to process successful payment"}), 500

@stripe_routes.route('/create-setup-intent', methods=['POST'])
@login_required
def create_setup_intent():
    """Create a setup intent for saving payment method"""
    try:
        user = User.get_by_id(g.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        # Create a setup intent with Stripe
        # First ensure Stripe has our customer
        customers = stripe.Customer.list(email=user["email"], limit=1)
        if customers.data:
            customer = customers.data[0]
        else:
            customer = stripe.Customer.create(email=user["email"])
        
        # Create a setup intent for future payments
        setup_intent = stripe.SetupIntent.create(
            customer=customer.id,
            payment_method_types=['card'],
            usage='off_session',
            metadata={
                'user_id': g.user_id
            }
        )
        
        # Generate a frontend URL that will handle the setup process
        setup_url = f"{os.environ.get('FRONTEND_URL', 'http://localhost:3000')}/stripe/setup?setup_intent_client_secret={setup_intent.client_secret}"
        
        return jsonify({
            "success": True,
            "checkout_url": setup_url,
            "setup_intent_id": setup_intent.id,
            "client_secret": setup_intent.client_secret
        }), 200
        
    except Exception as e:
        logger.error(f"Error creating setup intent: {str(e)}")
        return jsonify({"error": "Failed to create setup intent"}), 500

@stripe_routes.route('/verify-setup-intent', methods=['POST'])
@login_required
def verify_setup_intent():
    """Verify a setup intent and save the payment method"""
    try:
        data = request.json
        
        if not data or "setup_intent_id" not in data:
            return jsonify({"error": "Setup intent ID is required"}), 400
            
        setup_intent_id = data["setup_intent_id"]
        
        # Get the setup intent from Stripe
        setup_intent = stripe.SetupIntent.retrieve(setup_intent_id)
        
        # Only verify setup intents that have been successfully completed
        # The frontend should only call this endpoint after the setup_intent has succeeded
        if setup_intent.status != 'succeeded':
            logger.warning(f"Setup intent verification attempted with status: {setup_intent.status}")
            return jsonify({
                "success": False,
                "error": f"Setup intent not completed. Please complete the payment form."
            }), 400
            
        # Save the payment method to the database
        payment_method = stripe.PaymentMethod.retrieve(setup_intent.payment_method)
        card = payment_method.card
        
        # Check if payment method already exists
        response = supabase.table("payment_methods").select("*").eq("provider_payment_id", payment_method.id).execute()
        
        # Set all existing payment methods for this user to not default
        supabase.table("payment_methods").update({"is_default": False}).eq("user_id", g.user_id).execute()
        
        if len(response.data) > 0:
            # Update existing payment method
            payment_method_data = {
                "updated_at": datetime.datetime.now().isoformat(),
                "card_last4": card.last4,
                "card_brand": card.brand,
                "card_exp_month": card.exp_month,
                "card_exp_year": card.exp_year,
                "is_default": True
            }
            
            supabase.table("payment_methods").update(payment_method_data).eq("provider_payment_id", payment_method.id).execute()
        else:
            # Create new payment method
            payment_method_data = {
                "id": str(uuid.uuid4()),
                "user_id": g.user_id,
                "provider": "stripe",
                "provider_payment_id": payment_method.id,
                "card_last4": card.last4,
                "card_brand": card.brand,
                "card_exp_month": card.exp_month,
                "card_exp_year": card.exp_year,
                "is_default": True,
                "created_at": datetime.datetime.now().isoformat(),
                "updated_at": datetime.datetime.now().isoformat()
            }
            
            supabase.table("payment_methods").insert(payment_method_data).execute()
        
        return jsonify({
            "success": True,
            "message": "Payment method saved successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"Error verifying setup intent: {str(e)}")
        return jsonify({"error": f"Failed to verify setup intent: {str(e)}"}), 500
