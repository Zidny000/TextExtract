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
            
            if plan:
                max_requests = plan.get("max_requests_per_month", 20)
              # Create user in Supabase
            response = supabase.table("users").insert({
                "email": email,
                "password_hash": password_hash,
                "full_name": full_name,
                "plan_type": plan_type,
                "max_requests_per_month": max_requests,
                "email_verified": True,  # User is verified when created
                "created_at": datetime.datetime.now().isoformat(),
                "updated_at": datetime.datetime.now().isoformat()
            }).execute()
            
            if len(response.data) > 0:
                user = response.data[0]

                subscription_start = datetime.datetime.now().isoformat()
                
        
                # Default to 1 month subscription
                end_date = datetime.datetime.now() + datetime.timedelta(days=30)
                subscription_end = end_date.isoformat()
                
                # Create free subscription entry if successful
                if plan:
                    Subscription.create(
                        user_id=user["id"],
                        plan_id=plan["id"],
                        status="active" if plan_type != "free" else "free_tier",
                        start_date=subscription_start,
                        end_date=subscription_end if subscription_end else None,
                        renewal_date=subscription_end if subscription_end else None,
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
    def update_credit_requests(user_id, amount):
        """Update the user's credit requests"""
        try:
            user = User.get_by_id(user_id)
            credit_requests = user.get("credit_requests", 0)
            user = supabase.table("users").update({
                "credit_requests": credit_requests + amount
            }).eq("id", user_id).execute()
            return user
        except Exception as e:
            logger.error(f"Error updating credit requests: {str(e)}")
            return None

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
                last_day = datetime.date(year + 1, 1, 1)
            else:
                last_day = datetime.date(year, month + 1, 1)
            
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
                period_end = datetime.date(today.year, today.month, start_day)
            else:
                # Period is from start_day of current month to day before start_day of next month
                period_start = datetime.date(today.year, today.month, start_day)
                if today.month == 12:  # December
                    next_month_date = datetime.date(today.year + 1, 1, start_day)
                else:
                    next_month_date = datetime.date(today.year, today.month + 1, start_day)
                period_end = next_month_date
            
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
                        return False
            
            # Get max requests allowed per month
            max_requests = user.get("max_requests_per_month", 20)
            credit_requests = user.get("credit_requests")
            
            # Get current request count for the subscription period instead of calendar month
            current_count = User.get_subscription_period_request_count(user_id, sub_details)
            
            if current_count < max_requests:
                return True
            elif credit_requests > 0:
                # Allow one-time request using credit
                return User.decrement_credit_requests(user_id)
            else:
                # No more credits available
                return False
               
        except Exception as e:
            logger.error(f"Error checking if user can make request: {str(e)}")
            return False
        
    @staticmethod
    def decrement_credit_requests(user_id):
        """Decrement the user's credit requests by 1"""
        try:
            user = User.get_by_id(user_id)
            if not user:
                return False

            credit_requests = user.get("credit_requests", 0)
            if credit_requests > 0:
                credit_requests = credit_requests - 1
                supabase.table("users").update({
                  "credit_requests": credit_requests
                }).eq("id", user_id).execute()
                return True
            return False
        except Exception as e:
            logger.error(f"Error decrementing credit requests: {str(e)}")
            return False

    @staticmethod
    def update_subscription(user_id, plan_id, subscription_id=None, subscription_start=None, subscription_end=None):
        """Update user subscription information"""
        try:
            # Get plan details
            plan = SubscriptionPlan.get_by_id(plan_id)
            if not plan:
                logger.error(f"Plan ID {plan_id} not found")
                return False

            # First update the user's plan_id and related fields
            update_data = {
                "plan_type": plan.get('name'),
                "max_requests_per_month": plan.get("max_requests_per_month", 20),
                "updated_at": datetime.datetime.now().isoformat()
            }
            
            response = supabase.table("users").update(update_data).eq("id", user_id).execute()

            print(response.data)
            
            if len(response.data) == 0:
                logger.error(f"User with ID {user_id} not found")
                return None
          
            return response.data[0]
            
        except Exception as e:
            logger.error(f"Error updating user subscription: {str(e)}")
            return None


class ApiRequest:
    """Model for tracking API requests"""
    
    @staticmethod
    def create(user_id, request_type, ip_address=None, user_agent=None):
        """Create a new API request record"""
        try:
           
            
            request_data = {
                "user_id": user_id,
                "request_type": request_type,
                "created_at": datetime.datetime.now().isoformat(),
                "status": "pending",
                "ip_address": ip_address,
                "user_agent": user_agent,
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


class Subscription:
    """Model for user subscriptions"""
    
    @staticmethod
    def get_by_id(subscription_id):
        """Get a subscription by ID"""
        try:
            response = supabase.table("subscriptions").select("*").eq("id", subscription_id).execute()
            if len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting subscription by ID {subscription_id}: {str(e)}")
            return None

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
    def update(subscription_id, user_id, plan_id, status="active", start_date=None, end_date=None, renewal_date=None, external_subscription_id=None, auto_renewal=False):
        """Update an existing subscription record"""
        try:
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
            if external_subscription_id is None:
                external_subscription_id = None
            update_data = {
                "user_id": user_id,
                "plan_id": plan_id,
                "status": status,
                "start_date": start_date,
                "auto_renewal": auto_renewal
            }
            if end_date:
                update_data["end_date"] = end_date
            
            if renewal_date:
                update_data["renewal_date"] = renewal_date
            
            if external_subscription_id:
                update_data["external_subscription_id"] = external_subscription_id

            response = supabase.table("subscriptions").update(update_data).eq("id", subscription_id).execute()
            if len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating subscription: {str(e)}")
            return None
        
    @staticmethod
    def renew_subscription(start_date=None, end_date=None, renewal_date=None, external_subscription_id=None, auto_renewal=False):
        """Update an existing subscription record"""
        try:

            if start_date is None or end_date is None or external_subscription_id is None:
                logger.error("Missing required fields for subscription update")
                return None

            update_data = {}
            if start_date:
                update_data["start_date"] = start_date

            if end_date:
                update_data["end_date"] = end_date
            
            if renewal_date:
                update_data["renewal_date"] = renewal_date

            response = supabase.table("subscriptions").update(update_data).eq("external_subscription_id", external_subscription_id).execute()
            if len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error updating subscription: {str(e)}")
            return None

    @staticmethod
    def get_active_subscription(user_id):
        """Get the active subscription for a user"""
        try:
            response = supabase.table("subscriptions").select("*").eq("user_id", user_id).execute()
            
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
            

            plan = SubscriptionPlan.get_by_name("free")

            subscription_start = datetime.datetime.now().isoformat()

            update_data = {
                "status": "free_tier",
                "plan_id": plan["id"],
                "updated_at": datetime.datetime.now().isoformat(),
                "start_date": subscription_start,
                "end_date": None,
                "renewal_date": None
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
    def get_subscription_by_external_sub_id(external_sub_id):
        try:
            response = supabase.table("subscriptions").select("*").eq("external_subscription_id", external_sub_id).execute()
            if len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting subscription by External Sub ID {external_sub_id}: {str(e)}")
            return None
    
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