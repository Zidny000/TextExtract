import logging
from flask import Blueprint, request, jsonify, g
from auth import login_required
from database.db import supabase
from database.models import User, SubscriptionPlan, Subscription
from payment.stripe_client import create_checkout_session, verify_stripe_webhook, STRIPE_PUBLIC_KEY, get_subscription_details, cancel_stripe_subscription, create_buy_credit_checkout_session
import datetime
import stripe
import os
import uuid
from datetime import datetime, timezone

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

        if not data or "stripe_price_id" not in data:
            return jsonify({"success": False, "error": "Stripe Price ID is required"}), 400

        stripe_price_id = data["stripe_price_id"]
        plan_id = data["plan_id"]

        # Get the plan
        plan = SubscriptionPlan.get_by_id(plan_id)
        if not plan:
            return jsonify({"success": False, "error": "Plan not found"}), 404

        # Get the user
        user = User.get_by_id(g.user_id)
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404


        # Create checkout session
        checkout_session = create_checkout_session(
            customer_email=user["email"],
            plan_id=plan["id"],
            price_id=stripe_price_id
        )
        
        return jsonify({
            "success": True,
            "checkout_url": checkout_session.url,
            "session_id": checkout_session.id
        })
        
    except Exception as e:
        logger.error(f"Error creating Stripe checkout: {str(e)}")
        return jsonify({"error": "Failed to create checkout session"}), 500

@stripe_routes.route('/create-buy-credit-checkout', methods=['POST'])
@login_required
def create_stripe_buy_credit_checkout():
    """Create a Stripe checkout session for buying credits"""
    try:
        data = request.json
        data["amount"] = int(data["amount"]) if "amount" in data else None
        data["price"] = float(data["price"]) if "price" in data else None

        if not data["amount"] or not data["price"]:
            return jsonify({"success": False, "error": "Invalid amount or price"}), 400

        if data["amount"] != 100 and data["amount"] != 200 and data["amount"] != 300:
            return jsonify({"success": False, "error": "Invalid amount. Allowed values are 100, 200, 300."}), 400

        amount = data["amount"]
        price = amount == 100 and 2.99 or amount == 200 and 5.99 or amount == 300 and 7.99

        # Get the user
        user = User.get_by_id(g.user_id)
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404

        # Create checkout session
        checkout_session = create_buy_credit_checkout_session(
            customer_email=user["email"],
            user_id=user["id"],
            amount=amount,
            price=price
        )

        return jsonify({
            "success": True,
            "checkout_url": checkout_session.url,
            "session_id": checkout_session.id
        })

    except Exception as e:
        logger.error(f"Error creating Stripe buy credit checkout: {str(e)}")
        return jsonify({"error": "Failed to create buy credit checkout session"}), 500

@stripe_routes.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    try:
        payload = request.data
        signature = request.headers.get('Stripe-Signature')
        
        event = verify_stripe_webhook(payload, signature)
        
        if not event:
            return jsonify({"error": "Invalid Stripe signature"}), 400
            
        # Handle the event based on its type
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            if session.get("mode")=="subscription":
                # Extract metadata
                plan_id = session.get('metadata', {}).get('plan_id')
                user_email = session.get('customer_details', {}).get('email')

                # Get the plan
                plan = SubscriptionPlan.get_by_id(plan_id)
                if not plan:
                    logger.error(f"Plan {plan_id} not found")
                    return jsonify({"error": "Plan not found"}), 404

                # Calculate subscription dates
                subscription = get_subscription_details(session.get('subscription'))
              
                subscription_start = datetime.fromtimestamp(subscription['items']['data'][0]['current_period_start'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f%z')
                subscription_end = datetime.fromtimestamp(subscription['items']['data'][0]['current_period_end'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f%z')
      
                user = User.get_by_email(user_email)

                # Get subscription details including plan
                sub_details = Subscription.get_user_subscription_details(user["id"])
          
                if not sub_details or not sub_details.get("plan"):
                    return jsonify({"error": "Subscription details not found"}), 404
                
                    
                plan = sub_details["plan"]
                subscription = sub_details["subscription"]

                if subscription and subscription.get("status") == "active":
                    stripe_sub_cancelled = cancel_stripe_subscription(subscription["external_subscription_id"])
                    if not stripe_sub_cancelled:
                        return jsonify({"error": "Failed to cancel Stripe subscription"}), 500

                if subscription:
                    # Update existing subscription
                    Subscription.update(
                        subscription_id=subscription["id"],
                        user_id=user["id"],
                        plan_id=plan_id,
                        status="active",
                        start_date=subscription_start,
                        end_date=subscription_end,
                        renewal_date=subscription_end,
                        external_subscription_id=session.get('subscription')
                    )

                if not subscription:
                    logger.error(f"Failed to update subscription for user {user['id']} with plan {plan_id}")
                    return jsonify({"error": "Failed to update subscription"}), 500
                
                # Update user record with new plan type
                updated_user = User.update_subscription(
                    user['id'],
                    plan_id
                )
                
                if not updated_user:
                    logger.error(f"Failed to update user {user.id} with plan {plan_id}")
                    return jsonify({"error": "Failed to update user record"}), 500
                
                return jsonify({"success": True}), 200
            if session.get("mode")=="payment":
                user_id = session.get('metadata', {}).get('user_id')
               
                user = User.get_by_id(user_id)
                amount = session.get('metadata', {}).get('amount')
                amount = int(amount) if amount else 0
                user = User.update_credit_requests(user_id, amount)

                if not user:
                    logger.error(f"Failed to update credit requests for user {user_id}")
                    return jsonify({"error": "Failed to update credit requests"}), 500

                return jsonify({"success": True}), 200
            
        if event['type'] == 'customer.subscription.updated':
            session = event['data']['object']
            
            stripe_sub_id = session.get('id')
            subscription_start = datetime.fromtimestamp(session.get("current_period_start"), tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f%z')
            subscription_end = datetime.fromtimestamp(session.get("current_period_end"), tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f%z')

        
            Subscription.update_status(subscription['id'],session.get("status"))
      
            # Update existing subscription
            subscription = Subscription.renew_subscription(
                start_date=subscription_start,
                end_date=subscription_end,
                renewal_date=subscription_end,
                external_subscription_id=stripe_sub_id
            )

            if not subscription:
                logger.error(f"Failed to renew subscription for user {user['id']} with plan {plan_id}")
                return jsonify({"error": "Failed to renew subscription"}), 500
            
            return jsonify({"success": True}), 200

        if event['type'] == 'customer.subscription.deleted' :
            session = event['data']['object']
            stripe_sub_id = session.get('id')

            if not stripe_sub_id:
                logger.error(f"Stripe subscription ID not found")
                return jsonify({"error": "Stripe subscription ID not found"}), 404
            
            # Get subscription details including plan
            subscription = Subscription.get_subscription_by_external_sub_id(stripe_sub_id)

            if not subscription:
                return jsonify({"error": "Subscription details not found"}), 404

            Subscription.cancel_subscription(subscription['id'])

            return jsonify({"success": True}), 200

        # if event['type'] == 'checkout.session.async_payment_failed' or event['type'] == 'checkout.session.expired' or event['type'] == 'payment_intent.payment_failed':
        #     session = event['data']['object']
        #     user_email = session.get('customer_details', {}).get('email')
        #     user = User.get_by_email(user_email)

        #     # Get subscription details including plan
        #     sub_details = Subscription.get_user_subscription_details(user["id"])
      
        #     if not sub_details:
        #         return jsonify({"error": "Subscription details not found"}), 404

        #     subscription = sub_details["subscription"]
        #     Subscription.update_status(subscription['id'],'payment_failed')

        # Return a 200 for other event types we're not handling
        # return jsonify({"success": True}), 200
    
    except Exception as e:
        logger.error(f"Error processing Stripe webhook: {str(e)}")
        return jsonify({"error": "Error processing webhook"}), 500

@stripe_routes.route('/success', methods=['GET'])
@login_required
def stripe_success():
    """Handle successful Stripe payment"""
    try:
       
        
        return jsonify({
            "success": True,
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
        
        return jsonify({
            "success": True,
            "message": "Payment method saved successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"Error verifying setup intent: {str(e)}")
        return jsonify({"error": f"Failed to verify setup intent: {str(e)}"}), 500
