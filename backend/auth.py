import os
import jwt
import logging
import datetime
import uuid
from functools import wraps
from flask import request, jsonify, g
from database.models import User

logger = logging.getLogger(__name__)

# JWT configuration
JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    logger.warning("JWT_SECRET not set. Using default secret - NOT SECURE FOR PRODUCTION!")
    JWT_SECRET = "dev-secret-do-not-use-in-production"

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = 24 * 60 * 60  # 24 hours in seconds

def generate_token(user_id, email):
    """Generate a JWT token for the user"""
    try:
        payload = {
            "sub": str(user_id),
            "email": email,
            "iat": datetime.datetime.utcnow(),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_EXPIRATION),
            "jti": str(uuid.uuid4())
        }
        
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return token
    
    except Exception as e:
        logger.error(f"Error generating token: {str(e)}")
        return None

def validate_token(token):
    """Validate a JWT token and return user_id if valid"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload["sub"]  # User ID
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error validating token: {str(e)}")
        return None

def login_required(f):
    """Decorator to require authentication for an endpoint"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for token in the Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "No authorization token provided"}), 401
        
        # Extract the token
        try:
            token_type, token = auth_header.split(" ")
            if token_type.lower() != "bearer":
                return jsonify({"error": "Invalid token type"}), 401
        except ValueError:
            return jsonify({"error": "Invalid authorization header format"}), 401
        
        # Validate the token
        user_id = validate_token(token)
        if not user_id:
            return jsonify({"error": "Invalid or expired token"}), 401
        
        # Fetch the user
        user = User.get_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 401
        
        # Check if user is active
        if user.get("status") != "active":
            return jsonify({"error": "Account is inactive"}), 403
        
        # Store user in the global context for the request
        g.user = user
        g.user_id = user_id
        
        # Continue with the original function
        return f(*args, **kwargs)
    
    return decorated_function

def extract_device_info(request):
    """Extract device information from request"""
    user_agent_string = request.headers.get("User-Agent", "")
    device_info = {}
    
    try:
        # Try to parse with user_agents library
        from user_agents import parse
        user_agent = parse(user_agent_string)
        
        device_info = {
            "device_type": "desktop" if user_agent.is_pc else ("mobile" if user_agent.is_mobile else "tablet" if user_agent.is_tablet else "other"),
            "os_name": user_agent.os.family,
            "os_version": user_agent.os.version_string,
            "browser": user_agent.browser.family,
            "browser_version": user_agent.browser.version_string
        }
    except Exception:
        # Fallback to basic information
        device_info = {
            "user_agent": user_agent_string
        }
        
    # Add app version if provided in headers
    app_version = request.headers.get("X-App-Version")
    if app_version:
        device_info["app_version"] = app_version
        
    # Add device identifier if provided
    device_id = request.headers.get("X-Device-ID")
    if device_id:
        device_info["device_identifier"] = device_id
        
    return device_info 