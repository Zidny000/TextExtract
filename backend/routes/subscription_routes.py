import logging
import json
import uuid
from flask import Blueprint, request, jsonify, g
from database.db import supabase
from database.models import User, SubscriptionPlan, PaymentTransaction, Subscription
from auth import login_required
import datetime
from payment.stripe_client import cancel_stripe_subscription

logger = logging.getLogger(__name__)
subscription_routes = Blueprint('subscription', __name__, url_prefix='/subscription')

@subscription_routes.route('/plans', methods=['GET'])
def get_subscription_plans():
    """Get all available subscription plans"""
    try:
        plans = SubscriptionPlan.get_all_active()
        return jsonify(plans), 200
    except Exception as e:
        logger.error(f"Error getting subscription plans: {str(e)}")
        return jsonify({"error": "Failed to get subscription plans"}), 500

@subscription_routes.route('/user-plan', methods=['GET'])
@login_required
def get_user_plan():
    """Get the current user's subscription plan details"""
    try:
        user = g.user
        
        # Get subscription details including plan
        sub_details = Subscription.get_user_subscription_details(user["id"])
        if not sub_details or not sub_details.get("plan"):
            return jsonify({"error": "Subscription details not found"}), 404
            
        plan = sub_details["plan"]
        subscription = sub_details["subscription"]
        
        # Calculate subscription status
        subscription_status = "active"
        in_grace_period = False
        
        if not subscription:
            subscription_status = "free" if plan["name"] == "free" else "inactive"
        elif subscription.get("status") == "cancelled":
            subscription_status = "cancelled"
        elif subscription.get("status") == "payment_failed":
            subscription_status = "payment_failed"
        elif subscription.get("end_date"):
            end_date = datetime.datetime.fromisoformat(subscription["end_date"].replace("Z", "+00:00"))
            if end_date < datetime.datetime.now(datetime.timezone.utc):
                subscription_status = "expired"
                # Check if in grace period
                in_grace_period = Subscription.is_in_grace_period(subscription)
        
        # Get usage statistics
        today = datetime.date.today()
        month_count = User.get_subscription_period_request_count(user["id"])
        max_requests = user.get("max_requests_per_month", 20)
        
        # Get device usage
        device_count = User.get_device_count(user["id"])
        device_limit = user.get("device_limit", 2)
        
        # Format month string for display
        month_name = today.strftime("%B")
        
        return jsonify({
            "plan": plan,
            "usage": {
                "status": subscription_status,
                "subscription_id": subscription.get("id") if subscription else None,
                "start_date": subscription.get("start_date") if subscription else None,
                "end_date": subscription.get("end_date") if subscription else None,
                "renewal_date": subscription.get("renewal_date") if subscription else None,
                "auto_renewal": subscription.get("auto_renewal", False) if subscription else False,
                "in_grace_period": in_grace_period,
                "current_month": month_name,
                "month_requests": month_count,
                "max_requests": max_requests,
                "remaining_requests": max_requests - month_count,
                "device_count": device_count,
                "device_limit": device_limit
            }
        }), 200
    except Exception as e:
        logger.error(f"Error getting user subscription: {str(e)}")
        return jsonify({"error": "Failed to get subscription details"}), 500

@subscription_routes.route('/upgrade', methods=['POST'])
@login_required
def initiate_upgrade():
    """Initiate the subscription upgrade process"""
    try:
        data = request.json
        if not data or "plan_id" not in data:
            return jsonify({"error": "Plan ID is required"}), 400
        
        # Get the plan
        plan_id = data["plan_id"]
        subscription_id = data["subscription_id"]
        plan = SubscriptionPlan.get_by_id(plan_id)
        
        if not plan:
            return jsonify({"error": f"Plan with ID '{plan_id}' not found"}), 404
        
        subscription = Subscription.get_by_id(subscription_id)

        # For free plan, just create the subscription directly
        if subscription and subscription.get("status") == "active":
                stripe_sub_cancelled = cancel_stripe_subscription(subscription["external_subscription_id"])
                if not stripe_sub_cancelled:
                    return jsonify({"error": "Failed to upgrade Stripe subscription"}), 500
     
        subscription = Subscription.update(
            subscription_id,
            user_id=g.user_id,
            plan_id=plan_id,
            status="free_tier",
            start_date=datetime.datetime.now().isoformat()
        )

        if subscription:
            print(f"Updated subscription:")
            # Update the user record too
            updated_user = User.update_subscription(
                g.user_id, 
                plan["id"]
            )

            print(f"Updated user: {updated_user}")
            
            return jsonify({
                "success": True,
                "message": f"Successfully upgraded to {plan['name']} plan",
                "plan": plan,
                "subscription": subscription
            }), 200
        else:
            return jsonify({"error": "Failed to update subscription"}), 500
 
    except Exception as e:
        logger.error(f"Error initiating subscription upgrade: {str(e)}")
        return jsonify({"error": "Failed to initiate subscription upgrade"}), 500


@subscription_routes.route('/cancel', methods=['POST'])
@login_required
def cancel_subscription():
    """Cancel the current subscription"""
    try:
        # Get the active subscription
        subscription = Subscription.get_active_subscription(g.user_id)
        
        if not subscription or subscription.get("status") == "free_tier":
            return jsonify({"error": "No active paid subscription to cancel"}), 400

        stripe_sub_cancelled = cancel_stripe_subscription(subscription["external_subscription_id"])

        if not stripe_sub_cancelled:
            return jsonify({"error": "Failed to cancel Stripe subscription"}), 500

        # Cancel the subscription
        cancelled_sub = Subscription.cancel_subscription(subscription["id"])
        
        if not cancelled_sub:
            return jsonify({"error": "Failed to cancel subscription"}), 500
        
        # Downgrade to free plan
        plan = SubscriptionPlan.get_by_name("free")
        if not plan:
            return jsonify({"error": "Free plan not found"}), 500
        
        # Update user record to free plan
        updated_user = User.update_subscription(
            g.user_id,
            plan["id"]
        )
        
        if not updated_user:
            return jsonify({"error": "Failed to update user record"}), 500
        
        return jsonify({
            "success": True,
            "message": "Successfully cancelled subscription"
        }), 200
        
    except Exception as e:
        logger.error(f"Error cancelling subscription: {str(e)}")
        return jsonify({"error": "Failed to cancel subscription"}), 500

@subscription_routes.route('/update-payment-method', methods=['POST'])
@login_required
def update_payment_method():
    """Initialize the payment method update process"""
    try:
        # Get the payment provider from request, default to Stripe
     
        response = {
            "success": True,
            "checkout_url": "/stripe/setup"  # The frontend will redirect to this URL
        }
        
        return jsonify(response), 200
    
            
    except Exception as e:
        logger.error(f"Error updating payment method: {str(e)}")
        return jsonify({"error": "Failed to initialize payment method update"}), 500
