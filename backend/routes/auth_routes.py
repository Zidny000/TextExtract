import logging
from flask import Blueprint, request, jsonify, g
from database.models import User, Device
from auth import generate_token, login_required, extract_device_info

logger = logging.getLogger(__name__)
auth_routes = Blueprint('auth', __name__, url_prefix='/auth')

@auth_routes.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.json
        print(data)
        # Validate required fields
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({"error": "Email and password are required"}), 400
        
        # Check if email is already taken
        existing_user = User.get_by_email(data['email'])
        if existing_user:
            return jsonify({"error": "Email already registered"}), 409
        
        # Create the user
        new_user = User.create(
            email=data['email'],
            password=data['password'],
            full_name=data.get('full_name'),
            plan_type=data.get('plan_type', 'free')
        )
        
        if not new_user:
            return jsonify({"error": "Failed to create user"}), 500
        
        # Generate token
        token = generate_token(new_user['id'], new_user['email'])
        
        # Register device if identifier provided
        device_info = extract_device_info(request)
        device_id = request.headers.get("X-Device-ID")
        if device_id:
            Device.register(new_user['id'], device_id, device_info)
        
        # Return user data and token (exclude password_hash)
        new_user.pop('password_hash', None)
        return jsonify({
            "user": new_user,
            "token": token
        }), 201
        
    except Exception as e:
        logger.error(f"Error in register route: {str(e)}")
        return jsonify({"error": "An error occurred during registration"}), 500

@auth_routes.route('/login', methods=['POST'])
def login():
    """Login a user"""
    try:
        data = request.json
        
        # Validate required fields
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({"error": "Email and password are required"}), 400
        
        # Find the user
        user = User.get_by_email(data['email'])
        if not user:
            return jsonify({"error": "Invalid email or password"}), 401
        
        # Verify password
        if not User.verify_password(user, data['password']):
            return jsonify({"error": "Invalid email or password"}), 401
        
        # Check if user is active
        if user.get('status') != 'active':
            return jsonify({"error": "Account is inactive"}), 403
        
        # Update last login time
        User.update_last_login(user['id'])
        
        # Generate token
        token = generate_token(user['id'], user['email'])
        
        # Register device if identifier provided
        device_info = extract_device_info(request)
        device_id = request.headers.get("X-Device-ID")
        if device_id:
            Device.register(user['id'], device_id, device_info)
        
        # Return user data and token (exclude password_hash)
        user.pop('password_hash', None)
        return jsonify({
            "user": user,
            "token": token
        }), 200
        
    except Exception as e:
        logger.error(f"Error in login route: {str(e)}")
        return jsonify({"error": "An error occurred during login"}), 500

@auth_routes.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current authenticated user"""
    try:
        # g.user is set by the login_required decorator
        user = g.user.copy()
        
        # Remove sensitive data
        user.pop('password_hash', None)
        
        return jsonify(user), 200
        
    except Exception as e:
        logger.error(f"Error in get_current_user route: {str(e)}")
        return jsonify({"error": "An error occurred fetching user data"}), 500

@auth_routes.route('/refresh', methods=['POST'])
@login_required
def refresh_token():
    """Refresh the authentication token"""
    try:
        # Generate a new token
        token = generate_token(g.user['id'], g.user['email'])
        
        if not token:
            return jsonify({"error": "Failed to generate token"}), 500
        
        return jsonify({"token": token}), 200
        
    except Exception as e:
        logger.error(f"Error in refresh_token route: {str(e)}")
        return jsonify({"error": "An error occurred refreshing token"}), 500 