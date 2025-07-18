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
        """Get the number of API requests made by a user for a specific calendar month"""
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
    def get_subscription_period_request_count(user_id, sub_details=None):
        """
        Get the number of API requests made by a user within their current subscription period.
        This solves the issue of counting requests based on subscription dates rather than calendar months.
        """
        try:
            # If sub_details not provided, get it
            if not sub_details:
                sub_details = Subscription.get_user_subscription_details(user_id)
            
            if not sub_details or not sub_details.get("subscription"):
                # Fall back to calendar month if no subscription details available
                return User.get_monthly_request_count(user_id)
            
            subscription = sub_details.get("subscription")

            if subscription.get("status") == "free_tier":
                # If free tier, count all requests in the current month
                return User.get_monthly_request_count(user_id)

            # Get subscription start date
            start_date = None
            if subscription.get("start_date"):
                start_date = datetime.datetime.fromisoformat(subscription["start_date"].replace("Z", "+00:00"))
                start_date = start_date.date()
            else:
                # Fall back to first day of current month if no start date
                today = datetime.date.today()
                start_date = datetime.date(today.year, today.month, 1)
            
            # Calculate the current period end date based on subscription start date
            today = datetime.date.today()
            current_day = today.day
            start_day = start_date.day
            
            # If we're before the subscription start day in the current month
            if current_day < start_day:
                # Period is from start_day of previous month to day before start_day of current month
                if today.month == 1:  # January
                    period_start = datetime.date(today.year - 1, 12, start_day)
                else:
                    period_start = datetime.date(today.year, today.month - 1, start_day)
                period_end = datetime.date(today.year, today.month, start_day) - datetime.timedelta(days=1)
            else:
                # Period is from start_day of current month to day before start_day of next month
                period_start = datetime.date(today.year, today.month, start_day)
                if today.month == 12:  # December
                    next_month_date = datetime.date(today.year + 1, 1, start_day)
                else:
                    next_month_date = datetime.date(today.year, today.month + 1, start_day)
                period_end = next_month_date - datetime.timedelta(days=1)
            
            # Handle edge cases for months with different numbers of days
            # If the start_day is beyond the last day of a month, use the last day of that month
            try:
                period_start = period_start
            except ValueError:
                # Get the last day of the month
                if period_start.month == 12:
                    period_start = datetime.date(period_start.year + 1, 1, 1) - datetime.timedelta(days=1)
                else:
                    period_start = datetime.date(period_start.year, period_start.month + 1, 1) - datetime.timedelta(days=1)
            
            # Query the database for the sum of requests in the subscription period date range
            response = supabase.table("usage_stats") \
                .select("requests_count") \
                .eq("user_id", user_id) \
                .gte("date", period_start.isoformat()) \
                .lte("date", period_end.isoformat()) \
                .execute()
            
            # Sum up all the requests for the subscription period
            total_requests = 0
            for record in response.data:
                total_requests += record.get("requests_count", 0)
                
            logger.info(f"User {user_id} has used {total_requests} requests in the current subscription period ({period_start} to {period_end})")
            return total_requests
        except Exception as e:
            logger.error(f"Error getting subscription period request count: {str(e)}")
            # Fall back to calendar month count in case of error
            return User.get_monthly_request_count(user_id)

    @staticmethod
    def can_make_request(user_id):
        """Check if user can make another request based on their plan limits and subscription status"""
        try:
            # Get user and their plan
            user = User.get_by_id(user_id)
            if not user:
                return False
            
            # Check if subscription is active and not expired
            sub_details = Subscription.get_user_subscription_details(user_id)
            if sub_details and sub_details.get("subscription"):
                subscription = sub_details.get("subscription")
                
                # Check if subscription is cancelled
                if subscription.get("status") == "cancelled":
                    return False
                    
                # Check if subscription has ended
                if subscription.get("end_date"):
                    end_date = datetime.datetime.fromisoformat(subscription["end_date"].replace("Z", "+00:00"))
                    if end_date < datetime.datetime.now(datetime.timezone.utc):
                        # Check if in grace period
                        if Subscription.is_in_grace_period(subscription):
                            # Allow requests during grace period
                            logger.info(f"User {user_id} is in grace period, allowing request")
                        else:
                            # Subscription expired and not in grace period
                            return False
            
            # Get max requests allowed per month
            max_requests = user.get("max_requests_per_month", 20)
            
            # Get current request count for the subscription period instead of calendar month
            current_count = User.get_subscription_period_request_count(user_id, sub_details)
            
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
    def create(user_id, plan_id, status="active", start_date=None, end_date=None, renewal_date=None, external_subscription_id=None, auto_renewal=False):
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
                "updated_at": now.isoformat(),
                "auto_renewal": auto_renewal
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
    
    @staticmethod
    def get_all_active_subscriptions():
        """Get all active subscriptions from the database"""
        try:
            response = supabase.table("subscriptions").select("*").eq("status", "active").execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting active subscriptions: {str(e)}")
            return []
    
    @staticmethod
    def update_status(subscription_id, status):
        """Update the status of a subscription"""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.datetime.now().isoformat()
            }
            
            response = supabase.table("subscriptions").update(update_data).eq("id", subscription_id).execute()
            
            if len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating subscription status: {str(e)}")
            return None
        
    @staticmethod
    def check_renewal(subscription_id):
        """
        Check if a subscription should be renewed. Returns True if renewal was successful,
        False if renewal failed or wasn't needed.
        """
        try:
            # Get subscription
            response = supabase.table("subscriptions").select("*").eq("id", subscription_id).execute()
            if len(response.data) == 0:
                logger.error(f"Subscription {subscription_id} not found")
                return False
                
            subscription = response.data[0]
            
            # Check if subscription has auto-renewal enabled
            if not subscription.get("auto_renewal", False):
                return False
                
            # Check if subscription needs renewal (1 day before expiry to ensure no service interruption)
            if not subscription.get("renewal_date"):
                return False
                
            renewal_date = datetime.datetime.fromisoformat(subscription["renewal_date"].replace("Z", "+00:00"))
            now = datetime.datetime.now(datetime.timezone.utc)
            
            # If renewal date is within 24 hours, try to renew
            if (renewal_date - now).total_seconds() <= 86400:  # 24 hours in seconds
                return Subscription.process_auto_renewal(subscription)
                
            return False
        except Exception as e:
            logger.error(f"Error checking subscription renewal: {str(e)}")
            return False
    
    @staticmethod
    def process_auto_renewal(subscription):
        """
        Process auto-renewal for a subscription using stored payment method.
        Returns True if renewal was successful, False otherwise.
        """
        try:
            from payment.stripe_client import StripeClient
            
            user_id = subscription["user_id"]
            plan_id = subscription["plan_id"]
            
            # Get plan details
            plan = SubscriptionPlan.get_by_id(plan_id)
            if not plan:
                logger.error(f"Plan {plan_id} not found for auto-renewal")
                return False
                
            # Get user's payment method
            payment_method = Subscription.get_user_payment_method(user_id)
            if not payment_method:
                logger.error(f"No payment method found for user {user_id}")
                # Mark subscription as payment_failed
                Subscription.update_status(subscription["id"], "payment_failed")
                Subscription.send_renewal_failure_notification(user_id, subscription["id"])
                return False
                
            # Process payment with Stripe
            stripe_client = StripeClient()
            payment_result = stripe_client.charge_subscription(
                user_id=user_id,
                payment_method_id=payment_method["id"],
                amount=plan["price"],
                currency=plan["currency"],
                description=f"Auto-renewal for {plan['name']} plan"
            )
            
            if not payment_result.get("success"):
                # Payment failed
                logger.error(f"Auto-renewal payment failed for user {user_id}: {payment_result.get('error')}")
                Subscription.update_status(subscription["id"], "payment_failed")
                Subscription.send_renewal_failure_notification(user_id, subscription["id"])
                return False
                
            # Payment successful, extend subscription
            now = datetime.datetime.now(datetime.timezone.utc)
            new_end_date = now + datetime.timedelta(days=30) # Default to 1 month
            
            if plan.get("interval") == "year":
                new_end_date = now + datetime.timedelta(days=365)
            
            # Update subscription
            update_data = {
                "status": "active",
                "start_date": now.isoformat(),
                "end_date": new_end_date.isoformat(),
                "renewal_date": new_end_date.isoformat(),
                "updated_at": now.isoformat(),
                "payment_status": "paid",
                "last_payment_date": now.isoformat()
            }
            
            supabase.table("subscriptions").update(update_data).eq("id", subscription["id"]).execute()
            
            # Create payment transaction record
            PaymentTransaction.create(
                user_id=user_id,
                plan_id=plan_id,
                amount=plan["price"],
                currency=plan["currency"],
                payment_provider="stripe",
                transaction_id=payment_result.get("transaction_id"),
                status="completed"
            )
            
            # Send renewal success notification
            Subscription.send_renewal_success_notification(user_id, subscription["id"])
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing auto-renewal: {str(e)}")
            return False
    
    @staticmethod
    def get_user_payment_method(user_id):
        """Get the user's default payment method"""
        try:
            response = supabase.table("payment_methods").select("*").eq("user_id", user_id).eq("is_default", True).execute()
            
            if len(response.data) > 0:
                return response.data[0]
            
            # If no default payment method, get any payment method
            response = supabase.table("payment_methods").select("*").eq("user_id", user_id).limit(1).execute()
            
            if len(response.data) > 0:
                return response.data[0]
                
            return None
        except Exception as e:
            logger.error(f"Error getting user payment method: {str(e)}")
            return None
    
    @staticmethod
    def send_renewal_success_notification(user_id, subscription_id):
        """Send notification about successful subscription renewal"""
        try:
            # In a real implementation, this would send an email
            # For now, just log it
            logger.info(f"Subscription {subscription_id} renewed successfully for user {user_id}")
            
            # TODO: Implement actual email notification
        except Exception as e:
            logger.error(f"Error sending renewal success notification: {str(e)}")
    
    @staticmethod
    def send_renewal_failure_notification(user_id, subscription_id):
        """Send notification about failed subscription renewal"""
        try:
            # In a real implementation, this would send an email
            # For now, just log it
            logger.error(f"Subscription {subscription_id} renewal failed for user {user_id}")
            
            # TODO: Implement actual email notification
        except Exception as e:
            logger.error(f"Error sending renewal failure notification: {str(e)}")
    
    @staticmethod
    def is_in_grace_period(subscription):
        """
        Check if a subscription is in grace period after expiration.
        Returns True if in grace period, False otherwise.
        """
        try:
            # If subscription is not expired or not in payment_failed status, there's no grace period
            if subscription.get("status") not in ["expired", "payment_failed"]:
                return False
                
            # Check if there's an end date
            if not subscription.get("end_date"):
                return False
                
            # Parse the end date
            end_date = datetime.datetime.fromisoformat(subscription["end_date"].replace("Z", "+00:00"))
            now = datetime.datetime.now(datetime.timezone.utc)
            
            # Grace period is 7 days after expiration
            grace_period_end = end_date + datetime.timedelta(days=3)
            
            # Check if current time is within grace period
            return now <= grace_period_end
        except Exception as e:
            logger.error(f"Error checking grace period: {str(e)}")
            return False
        

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