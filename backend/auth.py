import os
import jwt
import logging
import datetime
import uuid
from functools import wraps
from flask import request, jsonify, g, abort
from database.models import User

logger = logging.getLogger(__name__)

# JWT configuration
JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    logger.warning("JWT_SECRET not set. Using default secret - NOT SECURE FOR PRODUCTION!")
    JWT_SECRET = "dev-secret-do-not-use-in-production"

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = 24 * 60 * 60  # 24 hours in seconds
JWT_REFRESH_EXPIRATION = 30 * 24 * 60 * 60  # 30 days for refresh tokens

# CSRF Protection
CSRF_EXEMPT_ROUTES = [
    '/auth/login',
    '/auth/register',
    '/auth/refresh',
    '/auth/request-password-reset',
    '/auth/reset-password',
    '/auth/verify-email'
]

# Store revoked tokens (in production, this should be in Redis or a database)
revoked_tokens = set()

def generate_token(user_id, email, device_id=None, is_refresh=False):
    """Generate a JWT token for the user"""
    try:
        expiration = JWT_REFRESH_EXPIRATION if is_refresh else JWT_EXPIRATION
        token_type = "refresh" if is_refresh else "access"
        
        # Generate a unique token ID
        token_id = str(uuid.uuid4())
        
        payload = {
            "sub": str(user_id),
            "email": email,
            "iat": datetime.datetime.utcnow(),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=expiration),
            "jti": token_id,
            "type": token_type
        }
        
        # Add device ID if provided
        if device_id:
            payload["device_id"] = device_id
        
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return token
    
    except Exception as e:
        logger.error(f"Error generating token: {str(e)}")
        return None

def validate_token(token):
    """Validate a JWT token and return user_id if valid"""
    try:
        # Check if token is in the revoked list
        if token in revoked_tokens:
            logger.warning("Token has been revoked")
            return None
            
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        # Validate token type (must be "access" for API access)
        if payload.get("type") != "access" and not payload.get("type") is None:
            logger.warning("Invalid token type for access")
            return None
            
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

def revoke_token(token):
    """Add a token to the revoked token list"""
    try:
        # In a production environment, store this in Redis or a database
        revoked_tokens.add(token)
        
        # Try to extract the token expiration to clean it up later
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], options={"verify_signature": True})
            exp_time = payload.get("exp")
            
            # TODO: Implement a cleanup mechanism for expired tokens in the blacklist
        except:
            pass
            
        return True
    except Exception as e:
        logger.error(f"Error revoking token: {str(e)}")
        return False

def csrf_protect():
    """Validate that CSRF protection is in place for sensitive requests"""
    # Skip CSRF check for exempt routes
    if request.path in CSRF_EXEMPT_ROUTES:
        return True
        
    # Check for X-CSRF-TOKEN header
    csrf_token = request.headers.get('X-CSRF-TOKEN')
    if not csrf_token:
        logger.warning(f"CSRF token missing for {request.path}")
        return False
        
    # Check Origin/Referer headers to prevent CSRF
    origin = request.headers.get('Origin')
    referer = request.headers.get('Referer')
    
    # In production, validate these against your allowed domains
    # For now, we'll just check that they exist
    if not origin and not referer:
        logger.warning(f"Both Origin and Referer headers missing for {request.path}")
        return False
        
    return True

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
        
        # For non-exempt routes, validate CSRF protection
        if request.method != 'GET' and not request.path.startswith('/auth/'):
            if not csrf_protect():
                logger.warning(f"CSRF validation failed for {request.path}")
                return jsonify({"error": "CSRF validation failed"}), 403
        
        # Store user in the global context for the request
        g.user = user
        g.user_id = user_id
        g.current_token = token
        
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
        
    # Add IP address
    if request.remote_addr:
        device_info["ip_address"] = request.remote_addr
        
    return device_info 