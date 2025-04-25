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
            
            # Create user in Supabase
            response = supabase.table("users").insert({
                "email": email,
                "password_hash": password_hash,
                "full_name": full_name,
                "plan_type": plan_type,
                "created_at": datetime.datetime.now().isoformat(),
                "updated_at": datetime.datetime.now().isoformat()
            }).execute()
            
            if len(response.data) > 0:
                return response.data[0]
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
    def get_daily_request_count(user_id, date=None):
        """Get the number of API requests made by a user on a specific date"""
        if date is None:
            date = datetime.date.today()
        
        try:
            date_str = date.isoformat()
            response = supabase.table("usage_stats").select("requests_count").eq("user_id", user_id).eq("date", date_str).execute()
            
            if len(response.data) > 0:
                return response.data[0]["requests_count"]
            return 0
        except Exception as e:
            logger.error(f"Error getting daily request count: {str(e)}")
            return 0
    
    @staticmethod
    def can_make_request(user_id):
        """Check if user can make another request based on their plan limits"""
        try:
            # Get user and their plan
            user = User.get_by_id(user_id)
            if not user:
                return False
            
            # Get max requests allowed per day
            max_requests = user.get("max_requests_per_day", 50)
            
            # Get current request count
            current_count = User.get_daily_request_count(user_id)
            
            # Check if user is within limits
            return current_count < max_requests
        except Exception as e:
            logger.error(f"Error checking if user can make request: {str(e)}")
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
                # Create new device
                device_data = {
                    "user_id": user_id,
                    "device_identifier": device_identifier,
                    "created_at": datetime.datetime.now().isoformat(),
                    "last_active": datetime.datetime.now().isoformat()
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