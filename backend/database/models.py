import json
import logging
import datetime
import uuid
from flask_bcrypt import Bcrypt
from .db import supabase

logger = logging.getLogger(__name__)
bcrypt = Bcrypt()

class User:
    """User model for authentication and management"""
    
    @staticmethod
    def create(email, password, full_name=None, plan_type="free"):
        """Create a new user"""
        try:
            # Hash password
            password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
            
            # Get plan details
            plan = SubscriptionPlan.get_by_name(plan_type)
            max_requests = 20  # Default free tier value
            device_limit = 2   # Default free tier value
            
            if plan:
                max_requests = plan.get("max_requests_per_month", 20)
                device_limit = plan.get("device_limit", 2)
              # Create user in Supabase
            response = supabase.table("users").insert({
                "email": email,
                "password_hash": password_hash,
                "full_name": full_name,
                "plan_type": plan_type,
                "max_requests_per_month": max_requests,
                "device_limit": device_limit,
                "email_verified": True,  # User is verified when created
                "created_at": datetime.datetime.now().isoformat(),
                "updated_at": datetime.datetime.now().isoformat()
            }).execute()
            
            if len(response.data) > 0:
                user = response.data[0]
                
                # Create free subscription entry if successful
                if plan:
                    Subscription.create(
                        user_id=user["id"],
                        plan_id=plan["id"],
                        status="active",
                        start_date=datetime.datetime.now().isoformat()
                    )
                
                return user
            return None
            
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise
    
    @staticmethod
    def get_by_email(email):
        """Get user by email"""
        try:
            response = supabase.table("users").select("*").eq("email", email).execute()
            if len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting user by email: {str(e)}")
            return None
    
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID"""
        try:
            response = supabase.table("users").select("*").eq("id", user_id).execute()
            if len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting user by ID: {str(e)}")
            return None
    
    @staticmethod
    def update_last_login(user_id):
        """Update user's last login timestamp"""
        try:
            supabase.table("users").update({
                "last_login": datetime.datetime.now().isoformat()
            }).eq("id", user_id).execute()
        except Exception as e:
            logger.error(f"Error updating last login: {str(e)}")
    
    @staticmethod
    def verify_password(user, password):
        """Verify password against stored hash"""
        try:
            if user and "password_hash" in user:
                return bcrypt.check_password_hash(user["password_hash"], password)
            return False
        except Exception as e:
            logger.error(f"Error verifying password: {str(e)}")
            return False
        
    @staticmethod
    def get_monthly_request_count(user_id, month=None, year=None):
        """Get the number of API requests made by a user for a specific month"""
        if month is None or year is None:
            today = datetime.date.today()
            month = today.month
            year = today.year
        
        try:
            # Get the first and last day of the month
            first_day = datetime.date(year, month, 1)
            
            # Get the last day by finding the first day of next month and subtracting one day
            if month == 12:
                last_day = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
            else:
                last_day = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
            
            # Query the database for the sum of requests in the date range
            response = supabase.table("usage_stats") \
                .select("requests_count") \
                .eq("user_id", user_id) \
                .gte("date", first_day.isoformat()) \
                .lte("date", last_day.isoformat()) \
                .execute()
            
            # Sum up all the requests for the month
            total_requests = 0
            for record in response.data:
                total_requests += record.get("requests_count", 0)
                
            return total_requests
        except Exception as e:
            logger.error(f"Error getting monthly request count: {str(e)}")
            return 0

    @staticmethod
    def can_make_request(user_id):
        """Check if user can make another request based on their plan limits"""
        try:
            # Get user and their plan
            user = User.get_by_id(user_id)
            if not user:
                return False
            
            # Get max requests allowed per month
            max_requests = user.get("max_requests_per_month", 20)
            
            # Get current request count for this month
            current_count = User.get_monthly_request_count(user_id)
            
            # Check if user is within limits
            return current_count < max_requests
        except Exception as e:
            logger.error(f"Error checking if user can make request: {str(e)}")
            return False

    @staticmethod
    def update_subscription(user_id, plan_type, subscription_id=None, subscription_start=None, subscription_end=None):
        """Update user subscription information"""
        try:
            # Get plan details
            plan = SubscriptionPlan.get_by_name(plan_type)
            if not plan:
                logger.error(f"Plan type {plan_type} not found")
                return False
                
            # Set defaults if not provided
            if subscription_start is None:
                subscription_start = datetime.datetime.now().isoformat()
                
            if subscription_end is None and plan_type != "free":
                # Default to 1 month subscription
                end_date = datetime.datetime.now() + datetime.timedelta(days=30)
                subscription_end = end_date.isoformat()
            
            # First update the user's plan_type and related fields
            update_data = {
                "plan_type": plan_type,
                "max_requests_per_month": plan.get("max_requests_per_month", 20),
                "device_limit": plan.get("device_limit", 2),
                "updated_at": datetime.datetime.now().isoformat()
            }
            
            response = supabase.table("users").update(update_data).eq("id", user_id).execute()
            
            if len(response.data) == 0:
                logger.error(f"User with ID {user_id} not found")
                return None
            
            # Create or update subscription entry
            subscription = Subscription.create(
                user_id=user_id,
                plan_id=plan["id"],
                status="active" if plan_type != "free" else "free_tier",
                start_date=subscription_start,
                end_date=subscription_end if subscription_end else None,
                renewal_date=subscription_end if subscription_end else None,
                external_subscription_id=subscription_id if subscription_id else None
            )
            
            if subscription:
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error updating user subscription: {str(e)}")
            return None
    
    @staticmethod
    def get_device_count(user_id):
        """Get the number of devices registered for a user"""
        try:
            response = supabase.table("devices").select("id", count="exact").eq("user_id", user_id).eq("status", "active").execute()
            return response.count
        except Exception as e:
            logger.error(f"Error getting device count: {str(e)}")
            return 0

    @staticmethod
    def can_register_device(user_id):
        """Check if user can register a new device based on their plan limits"""
        try:
            # Get user and their plan
            user = User.get_by_id(user_id)
            if not user:
                return False
            
            # Get device limit
            device_limit = user.get("device_limit", 2)
            
            # Get current device count
            device_count = User.get_device_count(user_id)
            
            # Check if user is within limits
            return device_count < device_limit
        except Exception as e:
            logger.error(f"Error checking if user can register device: {str(e)}")
            return False


class ApiRequest:
    """Model for tracking API requests"""
    
    @staticmethod
    def create(user_id, request_type, ip_address=None, user_agent=None, device_info=None):
        """Create a new API request record"""
        try:
            # Convert device_info to JSON if it's a dictionary
            if isinstance(device_info, dict):
                device_info = json.dumps(device_info)
            
            request_data = {
                "user_id": user_id,
                "request_type": request_type,
                "created_at": datetime.datetime.now().isoformat(),
                "status": "pending",
                "ip_address": ip_address,
                "user_agent": user_agent,
                "device_info": device_info
            }
            
            response = supabase.table("api_requests").insert(request_data).execute()
            
            if len(response.data) > 0:
                # Update usage stats
                ApiRequest.update_usage_stats(user_id)
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error creating API request: {str(e)}")
            return None
    
    @staticmethod
    def update_status(request_id, status, response_time_ms=None, error_message=None, 
                     request_size_bytes=None, response_size_bytes=None):
        """Update status and metrics for an API request"""
        try:
            update_data = {
                "status": status
            }
            
            if response_time_ms is not None:
                update_data["response_time_ms"] = response_time_ms
            
            if error_message is not None:
                update_data["error_message"] = error_message
            
            if request_size_bytes is not None:
                update_data["request_size_bytes"] = request_size_bytes
                
            if response_size_bytes is not None:
                update_data["response_size_bytes"] = response_size_bytes
            
            supabase.table("api_requests").update(update_data).eq("id", request_id).execute()
        except Exception as e:
            logger.error(f"Error updating API request: {str(e)}")
    
    @staticmethod
    def update_usage_stats(user_id):
        """Update usage statistics for a user"""
        try:
            today = datetime.date.today().isoformat()
            
            # Check if we have a record for today
            response = supabase.table("usage_stats").select("*").eq("user_id", user_id).eq("date", today).execute()
            
            if len(response.data) > 0:
                # Update existing record
                current_stats = response.data[0]
                
                supabase.table("usage_stats").update({
                    "requests_count": current_stats["requests_count"] + 1,
                    "billable_requests_count": current_stats["billable_requests_count"] + 1
                }).eq("id", current_stats["id"]).execute()
            else:
                # Create new record for today
                supabase.table("usage_stats").insert({
                    "user_id": user_id,
                    "date": today,
                    "requests_count": 1,
                    "billable_requests_count": 1,
                    "total_response_time_ms": 0,
                    "average_response_time_ms": 0,
                    "error_count": 0
                }).execute()
        except Exception as e:
            logger.error(f"Error updating usage stats: {str(e)}")


class Device:
    """Model for tracking user devices"""
    
    @staticmethod
    def register(user_id, device_identifier, device_info=None):
        """Register a device for a user"""
        try:
            # Check if device already exists
            response = supabase.table("devices").select("*").eq("user_id", user_id).eq("device_identifier", device_identifier).execute()
            
            if len(response.data) > 0:
                # Update existing device
                device_id = response.data[0]["id"]
                
                update_data = {
                    "last_active": datetime.datetime.now().isoformat()
                }
                
                # Update device info if provided
                if device_info:
                    if "device_name" in device_info:
                        update_data["device_name"] = device_info["device_name"]
                    if "device_type" in device_info:
                        update_data["device_type"] = device_info["device_type"]
                    if "os_name" in device_info:
                        update_data["os_name"] = device_info["os_name"]
                    if "os_version" in device_info:
                        update_data["os_version"] = device_info["os_version"]
                    if "app_version" in device_info:
                        update_data["app_version"] = device_info["app_version"]
                
                supabase.table("devices").update(update_data).eq("id", device_id).execute()
                return device_id
            else:
                # Check if user can register a new device
                if not User.can_register_device(user_id):
                    logger.warning(f"User {user_id} attempted to register a new device but has reached their device limit")
                    return None
                
                # Create new device
                device_data = {
                    "user_id": user_id,
                    "device_identifier": device_identifier,
                    "created_at": datetime.datetime.now().isoformat(),
                    "last_active": datetime.datetime.now().isoformat(),
                    "status": "active"
                }
                
                # Add device info if provided
                if device_info:
                    if "device_name" in device_info:
                        device_data["device_name"] = device_info["device_name"]
                    if "device_type" in device_info:
                        device_data["device_type"] = device_info["device_type"]
                    if "os_name" in device_info:
                        device_data["os_name"] = device_info["os_name"]
                    if "os_version" in device_info:
                        device_data["os_version"] = device_info["os_version"]
                    if "app_version" in device_info:
                        device_data["app_version"] = device_info["app_version"]
                
                response = supabase.table("devices").insert(device_data).execute()
                
                if len(response.data) > 0:
                    return response.data[0]["id"]
                return None
        except Exception as e:
            logger.error(f"Error registering device: {str(e)}")
            return None
    
    @staticmethod
    def get_user_devices(user_id):
        """Get all devices for a user"""
        try:
            response = supabase.table("devices").select("*").eq("user_id", user_id).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting user devices: {str(e)}")
            return [] 


class Subscription:
    """Model for user subscriptions"""
    
    @staticmethod
    def create(user_id, plan_id, status="active", start_date=None, end_date=None, renewal_date=None, external_subscription_id=None):
        """Create a new subscription record"""
        try:
            # Set defaults
            if start_date is None:
                start_date = datetime.datetime.now().isoformat()
            
            now = datetime.datetime.now()
            
            # For non-free plans, set default end and renewal dates if not provided
            is_free_plan = False
            plan = SubscriptionPlan.get_by_id(plan_id)
            if plan and plan.get("price", 0) == 0:
                is_free_plan = True
                
            if end_date is None and not is_free_plan:
                # Default to 1 month subscription
                end_date = (now + datetime.timedelta(days=30)).isoformat()
            
            if renewal_date is None and not is_free_plan:
                renewal_date = end_date
            
            # Check if there's an existing active subscription for this user
            current_sub = Subscription.get_active_subscription(user_id)
            if current_sub:
                # If upgrading to the same plan, just extend dates
                if current_sub["plan_id"] == plan_id and not is_free_plan:
                    update_data = {
                        "status": status,
                        "updated_at": now.isoformat()
                    }
                    
                    if end_date:
                        update_data["end_date"] = end_date
                    
                    if renewal_date:
                        update_data["renewal_date"] = renewal_date
                    
                    if external_subscription_id:
                        update_data["external_subscription_id"] = external_subscription_id
                    
                    response = supabase.table("subscriptions").update(update_data).eq("id", current_sub["id"]).execute()
                    if len(response.data) > 0:
                        return response.data[0]
                else:
                    # If switching plans, cancel the current subscription
                    Subscription.cancel_subscription(current_sub["id"])
            
            # Create a new subscription
            subscription_data = {
                "user_id": user_id,
                "plan_id": plan_id,
                "status": status,
                "start_date": start_date,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }
            
            if end_date:
                subscription_data["end_date"] = end_date
            
            if renewal_date:
                subscription_data["renewal_date"] = renewal_date
            
            if external_subscription_id:
                subscription_data["external_subscription_id"] = external_subscription_id
            
            response = supabase.table("subscriptions").insert(subscription_data).execute()
            
            if len(response.data) > 0:
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error creating subscription: {str(e)}")
            return None
    
    @staticmethod
    def get_active_subscription(user_id):
        """Get the active subscription for a user"""
        try:
            response = supabase.table("subscriptions").select("*").eq("user_id", user_id).eq("status", "active").execute()
            
            if len(response.data) > 0:
                return response.data[0]
            
            # Also check for free tier subscription
            response = supabase.table("subscriptions").select("*").eq("user_id", user_id).eq("status", "free_tier").execute()
            
            if len(response.data) > 0:
                return response.data[0]
                
            return None
        except Exception as e:
            logger.error(f"Error getting active subscription: {str(e)}")
            return None
    
    @staticmethod
    def cancel_subscription(subscription_id):
        """Cancel a subscription"""
        try:
            update_data = {
                "status": "cancelled",
                "updated_at": datetime.datetime.now().isoformat()
            }
            
            response = supabase.table("subscriptions").update(update_data).eq("id", subscription_id).execute()
            
            if len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error cancelling subscription: {str(e)}")
            return None
    
    @staticmethod
    def get_user_subscription_details(user_id):
        """Get detailed subscription information for a user including plan details"""
        try:
            # Get active subscription
            subscription = Subscription.get_active_subscription(user_id)
            
            if not subscription:
                # Default to free plan if no active subscription
                free_plan = SubscriptionPlan.get_by_name("free")
                return {
                    "subscription": None,
                    "plan": free_plan
                }
            
            # Get plan details
            plan = SubscriptionPlan.get_by_id(subscription["plan_id"])
            
            return {
                "subscription": subscription,
                "plan": plan
            }
        except Exception as e:
            logger.error(f"Error getting user subscription details: {str(e)}")
            return None


class SubscriptionPlan:
    """Model for subscription plans"""
    
    @staticmethod
    def get_all_active():
        """Get all active subscription plans"""
        try:
            response = supabase.table("subscription_plans").select("*").eq("status", "active").execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting subscription plans: {str(e)}")
            return []
    
    @staticmethod
    def get_by_id(plan_id):
        """Get subscription plan by ID"""
        try:
            response = supabase.table("subscription_plans").select("*").eq("id", plan_id).execute()
            if len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting subscription plan by ID: {str(e)}")
            return None
    
    @staticmethod
    def get_by_name(plan_name):
        """Get subscription plan by name"""
        try:
            response = supabase.table("subscription_plans").select("*").eq("name", plan_name).execute()
            if len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting subscription plan by name: {str(e)}")
            return None


class PaymentTransaction:
    """Model for payment transactions"""
    
    @staticmethod
    def create(user_id, plan_id, amount, currency="USD", payment_provider="paypal", transaction_id=None, status="pending", payload=None):
        """Create a new payment transaction"""
        try:
            transaction_data = {
                "user_id": user_id,
                "plan_id": plan_id,
                "amount": amount,
                "currency": currency,
                "payment_provider": payment_provider,
                "status": status,
                "created_at": datetime.datetime.now().isoformat(),
                "updated_at": datetime.datetime.now().isoformat()
            }
            
            if transaction_id:
                transaction_data["transaction_id"] = transaction_id
                
            if payload:
                if isinstance(payload, dict):
                    transaction_data["payload"] = payload
                else:
                    transaction_data["payload"] = json.loads(payload)
            
            response = supabase.table("payment_transactions").insert(transaction_data).execute()
            
            if len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error creating payment transaction: {str(e)}")
            return None
    @staticmethod
    def update_status(transaction_id, status, transaction_external_id=None, payment_provider=None):
        """Update status of a payment transaction"""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.datetime.now().isoformat()
            }
            
            if transaction_external_id:
                update_data["transaction_id"] = transaction_external_id
                
            if payment_provider:
                update_data["payment_provider"] = payment_provider
                
            response = supabase.table("payment_transactions").update(update_data).eq("id", transaction_id).execute()
            
            if len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating payment transaction: {str(e)}")
            return None
    @staticmethod
    def get_user_transactions(user_id, limit=10, offset=0):
        """Get user's payment transactions"""
        try:
            response = supabase.table("payment_transactions").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).offset(offset).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting user payment transactions: {str(e)}")
            return []
            
            
class UserReview:
    """User Review model for managing user feedback"""
    
    @staticmethod
    def create(user_id, rating, review_text):
        """Create a new user review"""
        try:
            response = supabase.table("user_reviews").insert({
                "user_id": user_id,
                "rating": rating,
                "review_text": review_text,
                "created_at": datetime.datetime.now().isoformat(),
                "updated_at": datetime.datetime.now().isoformat()
            }).execute()
            
            if len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error creating user review: {str(e)}")
            return None
    
    @staticmethod
    def get_by_user_id(user_id):
        """Get reviews by user ID"""
        try:
            response = supabase.table("user_reviews").select("*").eq("user_id", user_id).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting reviews by user ID: {str(e)}")
            return []
    
    @staticmethod
    def update_review(review_id, rating, review_text):
        """Update an existing review"""
        try:
            response = supabase.table("user_reviews").update({
                "rating": rating,
                "review_text": review_text,
                "updated_at": datetime.datetime.now().isoformat()
            }).eq("id", review_id).execute()
            
            if len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating user review: {str(e)}")
            return None