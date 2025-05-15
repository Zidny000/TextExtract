import logging
import json
import uuid
from flask import Blueprint, request, jsonify, g
from database.db import supabase
from database.models import User, SubscriptionPlan, PaymentTransaction
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
        
        # Get the plan details
        plan_type = user.get("plan_type", "free")
        plan = SubscriptionPlan.get_by_name(plan_type)
        
        if not plan:
            return jsonify({"error": f"Plan '{plan_type}' not found"}), 404
        
        # Calculate subscription status
        subscription_status = "active"
        subscription_end = user.get("subscription_end_date")
        
        if plan_type != "free" and subscription_end:
            end_date = datetime.datetime.fromisoformat(subscription_end.replace("Z", "+00:00"))
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
                "start_date": user.get("subscription_start_date"),
                "end_date": user.get("subscription_end_date"),
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
        
        # For free plan, just update the user directly
        if plan["price"] == 0:
            updated_user = User.update_subscription(
                g.user_id, 
                plan["name"],
                subscription_start=datetime.datetime.now().isoformat()
            )
            
            if updated_user:
                return jsonify({
                    "success": True,
                    "message": f"Successfully upgraded to {plan['name']} plan",
                    "plan": plan
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
    """Complete the payment process (dummy implementation)"""
    try:
        
        data = request.json
        if not data or "transaction_id" not in data:
            return jsonify({"error": "Transaction ID is required"}), 400
        
        transaction_id = data["transaction_id"]
        paypal_order_id = data.get("paypal_order_id", f"DUMMY-{uuid.uuid4()}")
        
        # Get the transaction
        response = supabase.table("payment_transactions").select("*").eq("id", transaction_id).execute()
        print("gasdgasdgasgdasdgasdgasdg")
        print(response)
        if len(response.data) == 0:
            return jsonify({"error": "Transaction not found"}), 404
            
        transaction = response.data[0]
        
        # Get the plan
        plan = SubscriptionPlan.get_by_id(transaction["plan_id"])
        print(plan)
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
        
        # Update user subscription
        subscription_start = datetime.datetime.now().isoformat()
        subscription_end = (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat()
        
        updated_user = User.update_subscription(
            g.user_id,
            plan["name"],
            subscription_id=paypal_order_id,
            subscription_start=subscription_start,
            subscription_end=subscription_end
        )
        
        if not updated_user:
            return jsonify({"error": "Failed to update subscription"}), 500
        
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
        user = g.user
        
        # Only process if user is on a paid plan
        if user.get("plan_type", "free") == "free":
            return jsonify({"error": "No active paid subscription to cancel"}), 400
        
        # Downgrade to free plan
        updated_user = User.update_subscription(
            g.user_id,
            "free",
            subscription_id=None,
            subscription_start=None,
            subscription_end=None
        )
        
        if not updated_user:
            return jsonify({"error": "Failed to cancel subscription"}), 500
        
        return jsonify({
            "success": True,
            "message": "Successfully cancelled subscription"
        }), 200
        
    except Exception as e:
        logger.error(f"Error cancelling subscription: {str(e)}")
        return jsonify({"error": "Failed to cancel subscription"}), 500 