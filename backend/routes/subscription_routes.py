import logging
import json
import uuid
from flask import Blueprint, request, jsonify, g
from database.db import supabase
from database.models import User, SubscriptionPlan, PaymentTransaction, Subscription
from auth import login_required
import datetime

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
        if not subscription:
            subscription_status = "free" if plan["name"] == "free" else "inactive"
        elif subscription.get("status") == "cancelled":
            subscription_status = "cancelled"
        elif subscription.get("end_date"):
            end_date = datetime.datetime.fromisoformat(subscription["end_date"].replace("Z", "+00:00"))
            if end_date < datetime.datetime.now(datetime.timezone.utc):
                subscription_status = "expired"
        
        # Get usage statistics
        today = datetime.date.today()
        month_count = User.get_monthly_request_count(user["id"])
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
                "start_date": subscription.get("start_date") if subscription else None,
                "end_date": subscription.get("end_date") if subscription else None,
                "renewal_date": subscription.get("renewal_date") if subscription else None,
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
        plan = SubscriptionPlan.get_by_id(plan_id)
        
        if not plan:
            return jsonify({"error": f"Plan with ID '{plan_id}' not found"}), 404
        
        # For free plan, just create the subscription directly
        if plan["price"] == 0:
            subscription = Subscription.create(
                user_id=g.user_id,
                plan_id=plan_id,
                status="free_tier",
                start_date=datetime.datetime.now().isoformat()
            )
            
            if subscription:
                # Update the user record too
                updated_user = User.update_subscription(
                    g.user_id, 
                    plan["name"]
                )
                
                return jsonify({
                    "success": True,
                    "message": f"Successfully upgraded to {plan['name']} plan",
                    "plan": plan,
                    "subscription": subscription
                }), 200
            else:
                return jsonify({"error": "Failed to update subscription"}), 500
        
        # For paid plans, create a payment transaction
        transaction = PaymentTransaction.create(
            user_id=g.user_id,
            plan_id=plan_id,
            amount=plan["price"],
            currency=plan["currency"],
            status="pending"
        )
        
        if not transaction:
            return jsonify({"error": "Failed to create payment transaction"}), 500
        
        # For now, return the transaction ID for the frontend to use with PayPal
        return jsonify({
            "success": True,
            "transaction_id": transaction["id"],
            "plan": plan,
            "amount": plan["price"],
            "currency": plan["currency"]
        }), 200
        
    except Exception as e:
        logger.error(f"Error initiating subscription upgrade: {str(e)}")
        return jsonify({"error": "Failed to initiate subscription upgrade"}), 500

@subscription_routes.route('/complete-payment', methods=['POST'])
@login_required
def complete_payment():
    """Complete the payment process"""
    try:
        data = request.json
        if not data or "transaction_id" not in data:
            return jsonify({"error": "Transaction ID is required"}), 400
        
        transaction_id = data["transaction_id"]
        paypal_order_id = data.get("paypal_order_id", f"DUMMY-{uuid.uuid4()}")
        
        # Get the transaction
        response = supabase.table("payment_transactions").select("*").eq("id", transaction_id).execute()
        if len(response.data) == 0:
            return jsonify({"error": "Transaction not found"}), 404
            
        transaction = response.data[0]
        
        # Get the plan
        plan = SubscriptionPlan.get_by_id(transaction["plan_id"])
        if not plan:
            return jsonify({"error": "Plan not found"}), 404
        
        # Update transaction status
        updated_transaction = PaymentTransaction.update_status(
            transaction_id,
            "completed",
            transaction_external_id=paypal_order_id
        )
        
        if not updated_transaction:
            return jsonify({"error": "Failed to update transaction status"}), 500
        
        # Calculate subscription dates
        subscription_start = datetime.datetime.now().isoformat()
        subscription_end = (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat()
        
        # Create or update subscription
        subscription = Subscription.create(
            user_id=g.user_id,
            plan_id=plan["id"],
            status="active",
            start_date=subscription_start,
            end_date=subscription_end,
            renewal_date=subscription_end,
            external_subscription_id=paypal_order_id
        )
        
        if not subscription:
            return jsonify({"error": "Failed to create or update subscription"}), 500
        
        # Update user record with new plan type
        updated_user = User.update_subscription(
            g.user_id,
            plan["name"]
        )
        
        if not updated_user:
            return jsonify({"error": "Failed to update user record"}), 500
        
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
        logger.error(f"Error completing payment: {str(e)}")
        return jsonify({"error": "Failed to complete payment"}), 500

@subscription_routes.route('/transactions', methods=['GET'])
@login_required
def get_transactions():
    """Get user's payment transactions"""
    try:
        # Get query parameters
        limit = request.args.get('limit', 10)
        offset = request.args.get('offset', 0)
        
        try:
            limit = int(limit)
            offset = int(offset)
            
            if limit < 1 or limit > 100:
                limit = 10
        except ValueError:
            return jsonify({"error": "Invalid limit or offset value"}), 400
        
        # Get transactions
        transactions = PaymentTransaction.get_user_transactions(g.user_id, limit, offset)
        
        return jsonify(transactions), 200
    except Exception as e:
        logger.error(f"Error getting payment transactions: {str(e)}")
        return jsonify({"error": "Failed to get payment transactions"}), 500

@subscription_routes.route('/cancel', methods=['POST'])
@login_required
def cancel_subscription():
    """Cancel the current subscription"""
    try:
        # Get the active subscription
        subscription = Subscription.get_active_subscription(g.user_id)
        
        if not subscription or subscription.get("status") == "free_tier":
            return jsonify({"error": "No active paid subscription to cancel"}), 400
        
        # Cancel the subscription
        cancelled_sub = Subscription.cancel_subscription(subscription["id"])

        print(f"Cancelled subscription: {cancelled_sub}")
        
        if not cancelled_sub:
            return jsonify({"error": "Failed to cancel subscription"}), 500
        
        # Downgrade to free plan
        plan = SubscriptionPlan.get_by_name("free")
        if not plan:
            return jsonify({"error": "Free plan not found"}), 500
        
        # Update user record to free plan
        updated_user = User.update_subscription(
            g.user_id,
            "free"
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