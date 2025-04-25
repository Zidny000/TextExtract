import logging
from flask import Blueprint, request, jsonify, g
from database.models import User, Device
from auth import generate_token, login_required, extract_device_info
import secrets
import string
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
auth_routes = Blueprint('auth', __name__, url_prefix='/auth')

# Email configuration
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "noreply@textextract.com")
APP_URL = os.environ.get("APP_URL", "http://localhost:5000")

# Store verification and reset tokens temporarily (in production, these should be in a database)
verification_tokens = {}  # {token: {'email': email, 'expires': datetime}}
reset_tokens = {}  # {token: {'user_id': user_id, 'email': email, 'expires': datetime}}

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
        
        # Send verification email
        verification_token = generate_verification_token()
        verification_tokens[verification_token] = {
            'email': new_user['email'],
            'expires': datetime.now() + timedelta(hours=24)
        }
        
        verification_url = f"{APP_URL}/auth/verify-email/{verification_token}"
        email_content = f"""
        <html>
            <body>
                <h2>Welcome to TextExtract!</h2>
                <p>Thank you for registering. Please click the link below to verify your email address:</p>
                <p><a href="{verification_url}">Verify Email Address</a></p>
                <p>If you didn't register for TextExtract, you can ignore this email.</p>
            </body>
        </html>
        """
        
        send_email(
            new_user['email'],
            "Verify Your TextExtract Email Address",
            email_content
        )
        
        # Return user data and token (exclude password_hash)
        new_user.pop('password_hash', None)
        return jsonify({
            "user": new_user,
            "token": token,
            "verification_sent": True
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
        reset_url = f"{APP_URL}/auth/reset-password/{reset_token}"
        
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
    """Verify a user's email address"""
    try:
        # Verify token exists and is valid
        if token not in verification_tokens:
            return jsonify({"error": "Invalid or expired verification link"}), 400
        
        token_data = verification_tokens[token]
        
        # Check if token is expired
        if datetime.now() > token_data['expires']:
            # Remove expired token
            verification_tokens.pop(token)
            return jsonify({"error": "Verification link has expired"}), 400
        
        email = token_data['email']
        
        # Update user's verification status in database
        from database.db import supabase
        
        # Get user by email
        user_response = supabase.table("users").select("*").eq("email", email).execute()
        
        if len(user_response.data) == 0:
            return jsonify({"error": "User not found"}), 404
        
        user_id = user_response.data[0]['id']
        
        # Update verification status
        response = supabase.table("users").update({
            "email_verified": True,
            "updated_at": datetime.now().isoformat()
        }).eq("id", user_id).execute()
        
        if len(response.data) == 0:
            return jsonify({"error": "Failed to verify email"}), 500
        
        # Remove used token
        verification_tokens.pop(token)
        
        # Return success HTML page
        return """
        <html>
            <head>
                <title>Email Verified</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding-top: 50px; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    h1 { color: #2e7d32; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Email Verified Successfully!</h1>
                    <p>Your email has been verified. You can now close this window and continue using TextExtract.</p>
                </div>
            </body>
        </html>
        """
        
    except Exception as e:
        logger.error(f"Error in verify_email route: {str(e)}")
        return jsonify({"error": "An error occurred verifying your email"}), 500

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
        
        verification_url = f"{APP_URL}/auth/verify-email/{verification_token}"
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