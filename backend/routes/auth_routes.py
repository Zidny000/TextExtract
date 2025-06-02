import logging
from flask import Blueprint, request, jsonify, g, redirect, render_template, Response, session
from database.models import User, Device
from auth import generate_token, login_required, extract_device_info, validate_token
import secrets
import string
import os
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from dotenv import load_dotenv
import traceback
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

logger = logging.getLogger(__name__)
auth_routes = Blueprint('auth', __name__, url_prefix='/auth')

# Set up rate limiter
limiter = Limiter(
    get_remote_address,
    default_limits=["200 per day"]
)

# Email configuration
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "noreply@textextract.com")
APP_URL = os.environ.get("APP_URL", "http://localhost:3000")
AUTH_CALLBACK_PORT = os.environ.get("AUTH_CALLBACK_PORT", "9845")

# Backend API URL for direct API access (for verification links, etc.)
BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://localhost:5000")
logger.info(f"Frontend URL: {APP_URL}")
logger.info(f"Backend API URL: {BACKEND_API_URL}")

# Store verification and reset tokens temporarily (in production, these should be in a database)
verification_tokens = {}  # {token: {'email': email, 'expires': datetime}}
reset_tokens = {}  # {token: {'user_id': user_id, 'email': email, 'expires': datetime}}

# Add failed login tracking for IP-based throttling
login_failures = {}  # {ip_address: {'count': 0, 'last_attempt': datetime}}
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_DURATION = 15  # minutes

def validate_password_strength(password):
    """
    Validates that a password meets security requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit
    - Contains at least one special character
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    # Check for at least one special character
    special_chars = "!@#$%^&*()-_=+[]{}|;:'\",.<>/?"
    if not any(c in special_chars for c in password):
        return False, "Password must contain at least one special character"
    
    return True, "Password meets strength requirements"

def validate_email_format(email):
    """Validate email format"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None

def check_login_rate_limit(ip_address):
    """Check if IP address has exceeded login attempts and is locked out"""
    now = datetime.now()
    
    if ip_address in login_failures:
        failures = login_failures[ip_address]
        
        # If we're in lockout period, check if it's expired
        if failures['count'] >= MAX_LOGIN_ATTEMPTS:
            lockout_time = failures['last_attempt'] + timedelta(minutes=LOGIN_LOCKOUT_DURATION)
            
            if now < lockout_time:
                # Still in lockout period
                remaining_seconds = int((lockout_time - now).total_seconds())
                return False, f"Too many failed login attempts. Please try again in {remaining_seconds} seconds."
            else:
                # Lockout period expired, reset counter
                failures['count'] = 0
    
    return True, ""

def record_failed_login(ip_address):
    """Record a failed login attempt"""
    now = datetime.now()
    
    if ip_address in login_failures:
        login_failures[ip_address]['count'] += 1
        login_failures[ip_address]['last_attempt'] = now
    else:
        login_failures[ip_address] = {
            'count': 1,
            'last_attempt': now
        }

def send_email(to_email, subject, html_content):
    """Send an email using SMTP"""
    if not all([SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD]):
        logger.warning("Email configuration incomplete. Email not sent.")
        return False
    
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = SENDER_EMAIL
        message["To"] = to_email
        
        # Create HTML version of message
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)
        
        # Connect to SMTP server and send email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, message.as_string())
        server.quit()
        
        return True
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False

def generate_verification_token():
    """Generate a secure verification token"""
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(64))



@auth_routes.route('/register', methods=['POST'])
@limiter.limit("10 per hour")
def register():
    """Register a new user"""
    try:
        data = request.json
        
        # Validate required fields
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({"error": "Email and password are required"}), 400
        
        # Validate email format
        if not validate_email_format(data['email']):
            return jsonify({"error": "Invalid email format"}), 400
            
        # Validate password strength
        is_valid, error_message = validate_password_strength(data['password'])
        if not is_valid:
            return jsonify({"error": error_message}), 400
        
        # Check if email is already taken
        existing_user = User.get_by_email(data['email'])
        if existing_user:
            # Do not reveal if email exists for security (reduces user enumeration risk)
            # Add random delay to prevent timing attacks
            import time
            import random
            time.sleep(random.uniform(0.5, 1.5))
            return jsonify({"error": "Invalid email or password"}), 401
        
        # Store registration info in verification tokens instead of creating user
        verification_token = generate_verification_token()
        registration_data = {
            'email': data['email'],
            'password': data['password'],
            'full_name': data.get('full_name'),
            'plan_type': data.get('plan_type', 'free'),
            'device_id': request.headers.get("X-Device-ID"),
            'device_info': extract_device_info(request),
            'expires': datetime.now() + timedelta(hours=24)
        }
        
        verification_tokens[verification_token] = registration_data
        
        # Send verification email to backend API endpoint
        backend_api_url = os.environ.get("BACKEND_API_URL", "http://localhost:5000")
        verification_url = f"{backend_api_url}/auth/verify-email/{verification_token}"
        email_content = f"""
        <html>
            <body>
                <h2>Welcome to TextExtract!</h2>
                <p>Thank you for your interest in registering. Please click the link below to verify your email address and complete your registration:</p>
                <p><a href="{verification_url}">Verify Email Address</a></p>
                <p>If you didn't register for TextExtract, you can ignore this email.</p>
            </body>
        </html>
        """
        
        email_sent = send_email(
            data['email'],
            "Verify Your TextExtract Email Address",
            email_content
        )
        
        if not email_sent:
            return jsonify({"error": "Failed to send verification email"}), 500
        
        # Return success without actual user data
        return jsonify({
            "message": "Verification email sent. Please check your inbox to complete registration.",
            "verification_sent": True
        }), 200
        
    except Exception as e:
        logger.error(f"Error in register route: {str(e)}")
        return jsonify({"error": "An error occurred during registration process"}), 500

@auth_routes.route('/login', methods=['POST'])
@limiter.limit("15 per minute")
def login():
    """Login a user"""
    try:
        # Get client IP address
        ip_address = get_remote_address()
        
        # Check if IP is in lockout period
        allowed, error_message = check_login_rate_limit(ip_address)
        if not allowed:
            return jsonify({"error": error_message}), 429
        
        data = request.json
        
        # Validate required fields
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({"error": "Email and password are required"}), 400
        
        # Add small random delay to prevent timing attacks
        import time
        import random
        time.sleep(random.uniform(0.1, 0.5))
        
        # Find the user
        user = User.get_by_email(data['email'])
        if not user:
            # Record failed login but don't reveal that email doesn't exist
            record_failed_login(ip_address)
            logger.warning(f"Login attempt for non-existent email: {data['email']} from IP {ip_address}")
            return jsonify({"error": "Invalid email or password"}), 401
        
        # Verify password
        if not User.verify_password(user, data['password']):
            # Record failed login
            record_failed_login(ip_address)
            logger.warning(f"Failed login attempt for email: {data['email']} from IP {ip_address}")
            return jsonify({"error": "Invalid email or password"}), 401
        
        # Check if user is active
        if user.get('status') != 'active':
            logger.warning(f"Login attempt for inactive account: {data['email']} from IP {ip_address}")
            return jsonify({"error": "Account is inactive"}), 403
        
        # Reset failed login counter for this IP
        if ip_address in login_failures:
            login_failures[ip_address]['count'] = 0
        
        # Update last login time
        User.update_last_login(user['id'])
        
        # Extract device info
        device_info = extract_device_info(request)
        device_id = request.headers.get("X-Device-ID")
        
        # Log successful login with device info
        logger.info(f"Successful login for {data['email']} from IP {ip_address}, device: {device_info.get('device_type', 'unknown')}")
        
        # Generate tokens (access and refresh)
        from auth import generate_token
        access_token = generate_token(user['id'], user['email'], device_id)
        refresh_token = generate_token(user['id'], user['email'], device_id, is_refresh=True)
        
        # Register device if identifier provided
        if device_id:
            Device.register(user['id'], device_id, device_info)
        
        # Return user data and tokens (exclude password_hash)
        user.pop('password_hash', None)
        return jsonify({
            "user": user,
            "token": access_token,
            "refresh_token": refresh_token
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
def refresh_access_token():
    """Get a new access token using a refresh token"""
    try:
        data = request.json
        
        # Validate required fields
        if not data or not data.get('refresh_token'):
            return jsonify({"error": "Refresh token is required"}), 400
        
        refresh_token = data.get('refresh_token')
        
        # Decode the refresh token without verification first to get the user ID
        try:
            import jwt
            from auth import JWT_SECRET, JWT_ALGORITHM
            
            # Decode without verification to get token info
            unverified_payload = jwt.decode(
                refresh_token, 
                options={"verify_signature": False}
            )
            
            # Check token type
            if unverified_payload.get("type") != "refresh":
                return jsonify({"error": "Invalid token type"}), 401
            
            # Now verify the token fully
            payload = jwt.decode(
                refresh_token, 
                JWT_SECRET, 
                algorithms=[JWT_ALGORITHM]
            )
            
            user_id = payload["sub"]
            email = payload["email"]
            device_id = payload.get("device_id")
            
            # Check if user exists and is active
            user = User.get_by_id(user_id)
            if not user:
                return jsonify({"error": "User not found"}), 401
                
            if user.get("status") != "active":
                return jsonify({"error": "Account is inactive"}), 403
                
            # Generate new access token
            from auth import generate_token
            access_token = generate_token(user_id, email, device_id)
            
            return jsonify({
                "token": access_token,
                "user_id": user_id,
                "email": email
            }), 200
            
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Refresh token has expired"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"error": f"Invalid refresh token: {str(e)}"}), 401
        
    except Exception as e:
        logger.error(f"Error in refresh_access_token route: {str(e)}")
        return jsonify({"error": "An error occurred refreshing token"}), 500

@auth_routes.route('/request-password-reset', methods=['POST'])
def request_password_reset():
    """Request a password reset email"""
    try:
        data = request.json
        
        # Validate required fields
        if not data or not data.get('email'):
            return jsonify({"error": "Email is required"}), 400
        
        # Find the user
        user = User.get_by_email(data['email'])
        if not user:
            # Don't reveal if user exists or not for security
            return jsonify({"message": "If your email is registered, you will receive a password reset link"}), 200
        
        # Generate a password reset token
        reset_token = generate_verification_token()
        reset_tokens[reset_token] = {
            'user_id': user['id'],
            'email': user['email'],
            'expires': datetime.now() + timedelta(hours=1)
        }
        
        # Create reset URL (would point to a frontend page in production)
        reset_url = f"{APP_URL}/reset-password/{reset_token}"
        
        # Send reset email
        email_content = f"""
        <html>
            <body>
                <h2>TextExtract Password Reset</h2>
                <p>You requested a password reset. Click the link below to set a new password:</p>
                <p><a href="{reset_url}">Reset Password</a></p>
                <p>This link will expire in 1 hour.</p>
                <p>If you didn't request a password reset, you can ignore this email.</p>
            </body>
        </html>
        """
        
        send_email(
            user['email'],
            "TextExtract Password Reset",
            email_content
        )
        
        return jsonify({"message": "If your email is registered, you will receive a password reset link"}), 200
        
    except Exception as e:
        logger.error(f"Error in request_password_reset route: {str(e)}")
        return jsonify({"error": "An error occurred processing your request"}), 500

@auth_routes.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset a user's password using a reset token"""
    try:
        data = request.json
        
        # Validate required fields
        if not data or not data.get('token') or not data.get('new_password'):
            return jsonify({"error": "Token and new password are required"}), 400
        
        token = data['token']
        new_password = data['new_password']
        
        # Verify token exists and is valid
        if token not in reset_tokens:
            return jsonify({"error": "Invalid or expired token"}), 400
        
        token_data = reset_tokens[token]
        
        # Check if token is expired
        if datetime.now() > token_data['expires']:
            # Remove expired token
            reset_tokens.pop(token)
            return jsonify({"error": "Token has expired"}), 400
        
        # Update user's password
        user_id = token_data['user_id']
        user = User.get_by_id(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Update password in database
        from database.db import supabase
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        
        password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
        
        response = supabase.table("users").update({
            "password_hash": password_hash,
            "updated_at": datetime.now().isoformat()
        }).eq("id", user_id).execute()
        
        if len(response.data) == 0:
            return jsonify({"error": "Failed to update password"}), 500
        
        # Remove used token
        reset_tokens.pop(token)
        
        return jsonify({"message": "Password has been reset successfully"}), 200
        
    except Exception as e:
        logger.error(f"Error in reset_password route: {str(e)}")
        return jsonify({"error": "An error occurred resetting your password"}), 500

@auth_routes.route('/verify-email/<token>', methods=['GET'])
def verify_email(token):
    """Verify a user's email address and create user account"""
    try:
        logger.info(f"Email verification requested for token: {token[:10]}...")
        
        # Check available tokens for debugging
        available_tokens = list(verification_tokens.keys())
        token_preview = [t[:10] + '...' for t in available_tokens]
        logger.info(f"Available verification tokens: {token_preview}")
        
        # Verify token exists and is valid
        if token not in verification_tokens:
            logger.warning(f"Invalid verification token: {token[:10]}...")
            return """
            <html>
                <head>
                    <title>Invalid Verification Link</title>
                    <style>
                        body { font-family: Arial, sans-serif; text-align: center; padding-top: 50px; }
                        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                        h1 { color: #f44336; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Invalid or Expired Link</h1>
                        <p>This verification link is invalid or has expired. Please request a new one.</p>
                    </div>
                </body>
            </html>
            """
        
        registration_data = verification_tokens[token]
        logger.info(f"Found registration data for email: {registration_data.get('email')}")
        
        # Check if token is expired
        if datetime.now() > registration_data['expires']:
            logger.warning(f"Expired verification token for email: {registration_data.get('email')}")
            # Remove expired token
            verification_tokens.pop(token)
            return """
            <html>
                <head>
                    <title>Expired Verification Link</title>
                    <style>
                        body { font-family: Arial, sans-serif; text-align: center; padding-top: 50px; }
                        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                        h1 { color: #f44336; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Link Expired</h1>
                        <p>This verification link has expired. Please register again to receive a new link.</p>
                    </div>
                </body>
            </html>
            """
        
        # Check if the email already exists (another user might have registered with this email)
        existing_user = User.get_by_email(registration_data['email'])
        if existing_user:
            logger.warning(f"Email already registered during verification: {registration_data['email']}")
            verification_tokens.pop(token)
            return """
            <html>
                <head>
                    <title>Email Already Registered</title>
                    <style>
                        body { font-family: Arial, sans-serif; text-align: center; padding-top: 50px; }
                        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                        h1 { color: #f44336; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Email Already Registered</h1>
                        <p>This email address is already registered. Please log in or use a different email.</p>
                    </div>
                </body>
            </html>
            """
        
        # Create the user now that email is verified
        try:
            logger.info(f"Creating new user for verified email: {registration_data['email']}")
            new_user = User.create(
                email=registration_data['email'],
                password=registration_data['password'],
                full_name=registration_data.get('full_name'),
                plan_type=registration_data.get('plan_type', 'free')
            )
            
            if not new_user:
                logger.error(f"Failed to create user for email: {registration_data['email']}")
                return """
                <html>
                    <head>
                        <title>Registration Failed</title>
                        <style>
                            body { font-family: Arial, sans-serif; text-align: center; padding-top: 50px; }
                            .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                            h1 { color: #f44336; }
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h1>Registration Failed</h1>
                            <p>We couldn't complete your registration. Please try again later.</p>
                        </div>
                    </body>
                </html>
                """
                
            logger.info(f"User created successfully with ID: {new_user['id']}")
            
            # Register device if identifier provided
            device_id = registration_data.get('device_id')
            device_info = registration_data.get('device_info')
            if device_id:
                logger.info(f"Registering device {device_id} for user: {new_user['id']}")
                Device.register(new_user['id'], device_id, device_info)
            
            # Remove used token
            verification_tokens.pop(token)
            
            # Return success HTML page
            return """
            <html>
                <head>
                    <title>Registration Complete</title>
                    <style>
                        body { font-family: Arial, sans-serif; text-align: center; padding-top: 50px; }
                        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                        h1 { color: #2e7d32; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Registration Complete!</h1>
                        <p>Your email has been verified and your account has been created.</p>
                        <p>You can now log in to TextExtract using your email and password.</p>
                        <p><a href="http://localhost:3000/login">Go to Login</a></p>
                    </div>
                </body>
            </html>
            """
        except Exception as user_creation_error:
            logger.error(f"Error creating user: {str(user_creation_error)}")
            verification_tokens.pop(token)  # Remove the token to prevent reuse
            return """
            <html>
                <head>
                    <title>Registration Error</title>
                    <style>
                        body { font-family: Arial, sans-serif; text-align: center; padding-top: 50px; }
                        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                        h1 { color: #f44336; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Registration Error</h1>
                        <p>We encountered an error while creating your account. Please try registering again.</p>
                    </div>
                </body>
            </html>
            """
        
    except Exception as e:
        logger.error(f"Error in verify_email route: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return """
        <html>
            <head>
                <title>Verification Error</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding-top: 50px; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    h1 { color: #f44336; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Verification Error</h1>
                    <p>An error occurred during email verification. Please try registering again.</p>
                </div>
            </body>
        </html>
        """

@auth_routes.route('/request-email-verification', methods=['POST'])
@login_required
def request_email_verification():
    """Request a new email verification link"""
    try:
        # User is already authenticated, get email from global context
        email = g.user['email']
        
        # Check if email is already verified
        if g.user.get('email_verified'):
            return jsonify({"message": "Email is already verified"}), 200
        
        # Generate a verification token
        verification_token = generate_verification_token()
        verification_tokens[verification_token] = {
            'email': email,
            'expires': datetime.now() + timedelta(hours=24)
        }
        
        verification_url = f"{APP_URL}/verify-email/{verification_token}"
        email_content = f"""
        <html>
            <body>
                <h2>TextExtract Email Verification</h2>
                <p>Please click the link below to verify your email address:</p>
                <p><a href="{verification_url}">Verify Email Address</a></p>
                <p>If you didn't request this verification, you can ignore this email.</p>
            </body>
        </html>
        """
        
        send_email(
            email,
            "Verify Your TextExtract Email Address",
            email_content
        )
        
        return jsonify({"message": "Verification email has been sent"}), 200
        
    except Exception as e:
        logger.error(f"Error in request_email_verification route: {str(e)}")
        return jsonify({"error": "An error occurred sending verification email"}), 500

@auth_routes.route('/delete-account', methods=['DELETE'])
@login_required
def delete_account():
    """Delete a user's account"""
    try:
        # Verify password for extra security
        data = request.json
        
        if not data or not data.get('password'):
            return jsonify({"error": "Password is required to delete account"}), 400
        
        # Verify password
        if not User.verify_password(g.user, data['password']):
            return jsonify({"error": "Invalid password"}), 401
        
        user_id = g.user['id']
        
        # First delete all associated devices
        from database.db import supabase
        
        supabase.table("devices").delete().eq("user_id", user_id).execute()
        
        # Delete user's API requests
        supabase.table("api_requests").delete().eq("user_id", user_id).execute()
        
        # Delete user's usage stats
        supabase.table("usage_stats").delete().eq("user_id", user_id).execute()
        
        # Delete user's billing records
        supabase.table("billing").delete().eq("user_id", user_id).execute()
        
        # Finally delete the user
        supabase.table("users").delete().eq("id", user_id).execute()
        
        return jsonify({"message": "Account deleted successfully"}), 200
        
    except Exception as e:
        logger.error(f"Error in delete_account route: {str(e)}")
        return jsonify({"error": "An error occurred deleting your account"}), 500

@auth_routes.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change a user's password"""
    try:
        data = request.json
        
        # Validate required fields
        if not data or not data.get('current_password') or not data.get('new_password'):
            return jsonify({"error": "Current password and new password are required"}), 400
        
        # Verify current password
        if not User.verify_password(g.user, data['current_password']):
            return jsonify({"error": "Current password is incorrect"}), 401
        
        # Update password in database
        from database.db import supabase
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        
        password_hash = bcrypt.generate_password_hash(data['new_password']).decode('utf-8')
        
        response = supabase.table("users").update({
            "password_hash": password_hash,
            "updated_at": datetime.now().isoformat()
        }).eq("id", g.user['id']).execute()
        
        if len(response.data) == 0:
            return jsonify({"error": "Failed to update password"}), 500
        
        return jsonify({"message": "Password has been changed successfully"}), 200
        
    except Exception as e:
        logger.error(f"Error in change_password route: {str(e)}")
        return jsonify({"error": "An error occurred changing your password"}), 500

@auth_routes.route('/web-login', methods=['GET'])
def web_login():
    
    """Redirect to the web login page with query parameters for the desktop app callback"""
    # Get parameters from query string
    redirect_uri = request.args.get('redirect_uri', '')
    device_id = request.args.get('device_id', '')
    state = request.args.get('state', '')
    direct_auth_url = request.args.get('direct_auth_url', '')

    logger.info(f"Web login request received. Redirect URI: {redirect_uri}, Device ID: {device_id}, State: {state}")
    
    if not redirect_uri:
        logger.error("Missing redirect_uri parameter in web-login request")
        return jsonify({"error": "Missing redirect_uri parameter"}), 400
    
    # Build a login page URL that will include these parameters
    login_url = f"{APP_URL}/login?redirect_uri={redirect_uri}&device_id={device_id}&state={state}"
    
    # Log the redirect URL
    logger.info(f"Redirecting to: {login_url}")
    
    # Create an HTML response if the redirect doesn't work
    html_response = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>TextExtract Authentication</title>
        <meta http-equiv="refresh" content="1;url={login_url}">
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
            .container {{ max-width: 600px; margin: 0 auto; }}
            .button {{ 
                display: inline-block; 
                background-color: #007bff; 
                color: white; 
                padding: 10px 20px; 
                text-decoration: none; 
                border-radius: 4px; 
                margin-top: 20px; 
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>TextExtract Authentication</h1>
            <p>Redirecting to login page...</p>
            <p>If you are not automatically redirected, please click the button below:</p>
            <a href="{login_url}" class="button">Go to Login Page</a>
        </div>
    </body>
    </html>
    """
    
    # Return HTML response with redirect header
    response = Response(html_response, 200, {'Content-Type': 'text/html'})
    response.headers['Location'] = login_url
    return response

@auth_routes.route('/complete-web-login', methods=['POST'])
def complete_web_login():
    """Complete the web login process and redirect back to the desktop app"""
    try:
        data = request.json
        
        # Get parameters
        email = data.get('email')
        password = data.get('password')
        redirect_uri = data.get('redirect_uri')
        device_id = data.get('device_id')
        state = data.get('state')
        
        logger.info(f"Web login completion request. Email: {email}, Redirect URI: {redirect_uri}, Device ID: {device_id}")
        
        if not all([email, password, redirect_uri]):
            logger.error("Missing required parameters in complete-web-login request")
            return jsonify({"error": "Missing required parameters"}), 400
        
        # Get client IP address
        ip_address = get_remote_address()
        
        # Check if IP is in lockout period
        allowed, error_message = check_login_rate_limit(ip_address)
        if not allowed:
            return jsonify({"error": error_message}), 429
        
        # Authenticate the user
        user = User.get_by_email(email)
        if not user:
            # Record failed login
            record_failed_login(ip_address)
            logger.warning(f"Invalid email in login attempt: {email} from IP {ip_address}")
            return jsonify({"error": "Invalid email or password"}), 401
        
        # Verify password
        if not User.verify_password(user, password):
            # Record failed login
            record_failed_login(ip_address)
            logger.warning(f"Invalid password for user: {email} from IP {ip_address}")
            return jsonify({"error": "Invalid email or password"}), 401
        
        # Check if user is active
        if user.get('status') != 'active':
            logger.warning(f"Inactive account login attempt: {email}")
            return jsonify({"error": "Account is inactive"}), 403
        
        # Reset failed login counter for this IP
        if ip_address in login_failures:
            login_failures[ip_address]['count'] = 0
        
        # Extract device info
        device_info = extract_device_info(request)
        
        # Generate tokens (access and refresh)
        from auth import generate_token
        access_token = generate_token(user['id'], user['email'], device_id)
        refresh_token = generate_token(user['id'], user['email'], device_id, is_refresh=True)
        
        # Register device if identifier provided
        if device_id:
            Device.register(user['id'], device_id, device_info)
            logger.info(f"Registered device {device_id} for user {email}")
        
        # Construct the callback URL
        callback_url = f"{redirect_uri}?token={access_token}&refresh_token={refresh_token}&user_id={user['id']}&email={user['email']}&state={state}"
        
        # Log the callback URL (but mask the token)
        logger.info(f"Created callback URL for {email} to {redirect_uri} (token masked)")
        
        # Return success with callback URL
        return jsonify({
            "success": True,
            "callback_url": callback_url
        }), 200
    
    except Exception as e:
        logger.error(f"Error in complete_web_login route: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": "An error occurred during login"}), 500
    
@auth_routes.route('/direct-web-login', methods=['POST'])
@login_required
def direct_web_login():
    """Complete the web login process and redirect back to the desktop app"""
    try:
        data = request.json
        
        # Get parameters
        email = data.get('email')
        redirect_uri = data.get('redirect_uri')
        device_id = data.get('device_id')
        state = data.get('state')
        
        ip_address = get_remote_address()

        # Authenticate the user
        user = User.get_by_email(email)

        
        # Check if user is active
        # if user.get('status') != 'active':
        #     logger.warning(f"Inactive account login attempt: {email}")
        #     return jsonify({"error": "Account is inactive"}), 403
        
        # Reset failed login counter for this IP
        if ip_address in login_failures:
            login_failures[ip_address]['count'] = 0
        
        # Extract device info
        device_info = extract_device_info(request)
        
        # Generate tokens (access and refresh)
        from auth import generate_token
        access_token = generate_token(user['id'], user['email'], device_id)
        refresh_token = generate_token(user['id'], user['email'], device_id, is_refresh=True)
        
        # Register device if identifier provided
        if device_id:
            Device.register(user['id'], device_id, device_info)
            logger.info(f"Registered device {device_id} for user {email}")
        
        # Construct the callback URL
        callback_url = f"{redirect_uri}?token={access_token}&refresh_token={refresh_token}&user_id={user['id']}&email={user['email']}&state={state}"
        
        # Log the callback URL (but mask the token)
        logger.info(f"Created callback URL for {email} to {redirect_uri} (token masked)")
        
        # Return success with callback URL
        return jsonify({
            "success": True,
            "callback_url": callback_url
        }), 200
    
    except Exception as e:
        logger.error(f"Error in complete_web_login route: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": "An error occurred during login"}), 500



def maybe_redirect_authenticated_user(direct_auth_url, device_id, state):
    """Check if the user is already authenticated via token and redirect to direct_auth_url if so"""
   
    try:
        # For desktop applications, we can't directly access tokens from localStorage
        # If we're in a Flask session, we might be able to get user info
        user = None
        
        # Check if we have a session-based user (if Flask session is being used)
        if hasattr(g, 'user') and g.user:
            user = g.user
        
        # Check if we have a user in the session
        elif hasattr(session, 'user') and session.user:
            user = session.user
            
        # No authenticated user found
        if not user:
            logger.info("No authenticated user found, proceeding with standard login flow")
            return None

        logger.info(f"User {user.get('email', 'unknown')} already authenticated, redirecting to direct_auth_url")

        # Generate new tokens
        access_token = generate_token(user['id'], user['email'], device_id)
        refresh_token = generate_token(user['id'], user['email'], device_id, is_refresh=True)

        # Construct callback URL
        callback_url = f"{direct_auth_url}?token={access_token}&refresh_token={refresh_token}" \
                       f"&user_id={user['id']}&email={user['email']}&state={state}"

        return redirect(callback_url)

    except Exception as e:
        logger.error(f"Error checking existing authentication: {str(e)}")
        return None

@auth_routes.route('/logout', methods=['POST'])
@login_required
def logout():
    """Log out a user by revoking their token"""
    try:
        # Get the current token from flask global context (set by login_required decorator)
        token = g.current_token
        
        # Revoke the token
        from auth import revoke_token
        success = revoke_token(token)
        
        if not success:
            return jsonify({"error": "Failed to revoke token"}), 500
        
        # Revoke refresh token if provided
        refresh_token = request.json.get('refresh_token')
        if refresh_token:
            revoke_token(refresh_token)
        
        return jsonify({"message": "Successfully logged out"}), 200
        
    except Exception as e:
        logger.error(f"Error in logout route: {str(e)}")
        return jsonify({"error": "An error occurred during logout"}), 500 