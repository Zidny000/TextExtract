import os
import json
import requests
import uuid
import logging
import sys
import traceback
import tkinter as tk
from tkinter import messagebox, simpledialog
from PIL import Image, ImageTk
import threading
import webbrowser
import socket
import http.server
import socketserver
import urllib.parse
from threading import Thread
import time
import re

# Set up basic logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("auth")

print("Initializing auth module...")

# API Base URL - change this to your production URL when deploying
API_BASE_URL = "http://localhost:5000"
print(f"Using API endpoint: {API_BASE_URL}")

# Auth callback server settings
AUTH_CALLBACK_PORT = 9845  # Choose an available port
AUTH_REDIRECT_URL = f"http://localhost:{AUTH_CALLBACK_PORT}/callback"

# Key for storing auth token in keyring
SERVICE_NAME = "TextExtract"
ACCOUNT_NAME = "textextract_user"
TOKEN_KEY = "auth_token"
REFRESH_TOKEN_KEY = "refresh_token"
USER_ID_KEY = "user_id"
EMAIL_KEY = "email"

# Fallback storage if keyring fails
_fallback_storage = {}

# Try to import keyring with better error handling
try:
    print("Attempting to import keyring module...")
    import keyring
    print(f"Keyring module imported successfully: {keyring.__version__ if hasattr(keyring, '__version__') else 'unknown version'}")
    
    # Test if keyring is working properly
    try:
        test_value = "test_value"
        keyring.set_password(SERVICE_NAME, "test_key", test_value)
        retrieved = keyring.get_password(SERVICE_NAME, "test_key")
        if retrieved != test_value:
            print(f"WARNING: Keyring test failed. Expected '{test_value}', got '{retrieved}'")
            raise Exception("Keyring test failed")
        print("Keyring tested successfully")
        _USE_KEYRING = True
    except Exception as e:
        print(f"WARNING: Keyring test failed: {e}")
        print("Falling back to insecure memory storage")
        _USE_KEYRING = False
except ImportError as e:
    print(f"ERROR: Could not import keyring module: {e}")
    _USE_KEYRING = False
except Exception as e:
    print(f"ERROR: Unexpected error with keyring: {e}")
    print(traceback.format_exc())
    _USE_KEYRING = False

# Generate a unique device identifier for this installation
def get_device_id():
    """Get a unique device identifier or create a new one if it doesn't exist"""
    try:
        if _USE_KEYRING:
            device_id = keyring.get_password(SERVICE_NAME, "device_id")
        else:
            device_id = _fallback_storage.get("device_id")
        
        if not device_id:
            # Generate a new device ID
            device_id = str(uuid.uuid4())
            if _USE_KEYRING:
                keyring.set_password(SERVICE_NAME, "device_id", device_id)
            else:
                _fallback_storage["device_id"] = device_id
            print(f"Generated new device ID: {device_id}")
        
        return device_id
    except Exception as e:
        print(f"Error in get_device_id: {e}")
        # Fallback to a temporary device ID
        return str(uuid.uuid4())

def save_auth_data(token, user_id, email, refresh_token=None):
    """Save authentication data securely using keyring or fallback storage"""
    print(f"Saving auth data for email: {email}")
    try:
        if _USE_KEYRING:
            keyring.set_password(SERVICE_NAME, TOKEN_KEY, token)
            keyring.set_password(SERVICE_NAME, USER_ID_KEY, user_id)
            keyring.set_password(SERVICE_NAME, EMAIL_KEY, email)
            if refresh_token:
                keyring.set_password(SERVICE_NAME, REFRESH_TOKEN_KEY, refresh_token)
        else:
            _fallback_storage[TOKEN_KEY] = token
            _fallback_storage[USER_ID_KEY] = user_id
            _fallback_storage[EMAIL_KEY] = email
            if refresh_token:
                _fallback_storage[REFRESH_TOKEN_KEY] = refresh_token
        return True
    except Exception as e:
        print(f"Error saving auth data: {e}")
        print(traceback.format_exc())
        return False

def get_auth_token():
    """Get the authentication token"""
    try:
        if _USE_KEYRING:
            return keyring.get_password(SERVICE_NAME, TOKEN_KEY)
        else:
            return _fallback_storage.get(TOKEN_KEY)
    except Exception as e:
        print(f"Error getting auth token: {e}")
        return None

def get_refresh_token():
    """Get the refresh token"""
    try:
        if _USE_KEYRING:
            return keyring.get_password(SERVICE_NAME, REFRESH_TOKEN_KEY)
        else:
            return _fallback_storage.get(REFRESH_TOKEN_KEY)
    except Exception as e:
        print(f"Error getting refresh token: {e}")
        return None

def get_user_email():
    """Get the user's email"""
    try:
        if _USE_KEYRING:
            return keyring.get_password(SERVICE_NAME, EMAIL_KEY)
        else:
            return _fallback_storage.get(EMAIL_KEY)
    except Exception as e:
        print(f"Error getting user email: {e}")
        return None

def get_user_id():
    """Get the user's ID"""
    try:
        if _USE_KEYRING:
            return keyring.get_password(SERVICE_NAME, USER_ID_KEY)
        else:
            return _fallback_storage.get(USER_ID_KEY)
    except Exception as e:
        print(f"Error getting user ID: {e}")
        return None

# Handler for the authorization callback
class AuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    """Handler for authorization callback"""
    def __init__(self, *args, auth_callback=None, **kwargs):
        print("Initializing AuthCallbackHandler")
        self.auth_callback = auth_callback
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        # Enable logging for better visibility
        print(f"AuthCallbackHandler: {format % args}")
    
    def do_GET(self):
        """Handle GET request"""
        print(f"Received callback request: {self.path}")
        try:
            # Parse the path
            parsed_path = urllib.parse.urlparse(self.path)
            
            # Check if this is the callback route (use startswith to handle variations)
            if parsed_path.path.startswith("/callback"):
                # Extract the token from query parameters
                query = urllib.parse.parse_qs(parsed_path.query)
                token = query.get("token", [""])[0]
                refresh_token = query.get("refresh_token", [""])[0]
                user_id = query.get("user_id", [""])[0]
                email = query.get("email", [""])[0]
                
                print(f"Received token: {token[:10] if token else 'None'}... (truncated)")
                print(f"Received refresh token: {refresh_token[:10] if refresh_token else 'None'}... (truncated)")
                print(f"Received user_id: {user_id}")
                print(f"Received email: {email}")
                
                # Process the token
                if token and user_id and email:
                    # Save the authentication data
                    print("Saving authentication data...")
                    success = save_auth_data(token, user_id, email, refresh_token)
                    if success:
                        message = "Authentication successful! You can now close this window and return to the app."
                    else:
                        message = "Authentication succeeded, but there was an error saving your credentials. Please try again."
                        success = False
                else:
                    success = False
                    missing = []
                    if not token:
                        missing.append("token")
                    if not user_id:
                        missing.append("user ID")
                    if not email:
                        missing.append("email")
                    message = f"Authentication failed. Missing information: {', '.join(missing)}. Please try again."
                
                # Send response to browser
                print(f"Sending response to browser: success={success}")
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                # Create a simple HTML response
                response = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>TextExtract Authentication</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                        .container {{ max-width: 600px; margin: 0 auto; }}
                        .success {{ color: green; }}
                        .error {{ color: red; }}
                        .message {{ margin: 20px 0; font-size: 18px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>TextExtract</h1>
                        <div class="message {'success' if success else 'error'}">
                            {message}
                        </div>
                        <p>You can now close this window.</p>
                    </div>
                    <script>
                        // Log authentication status for debugging
                        console.log("Authentication status: {success}");
                        
                        // Close the window automatically after 5 seconds
                        setTimeout(function() {{
                            window.close();
                        }}, 5000);
                    </script>
                </body>
                </html>
                """
                
                self.wfile.write(response.encode())
                
                # Call the auth callback if provided
                if self.auth_callback:
                    print("Calling auth callback function...")
                    try:
                        self.auth_callback(success, token, user_id, email, refresh_token)
                        print("Auth callback completed successfully")
                    except Exception as e:
                        print(f"Error in auth callback: {e}")
                        print(traceback.format_exc())
                else:
                    print("No auth callback function provided")
                
                return
            # Handle direct token requests for already logged in users
            elif parsed_path.path.startswith("/direct_auth"):
                print("Received direct auth request for already logged in user")
                query = urllib.parse.parse_qs(parsed_path.query)
                
                # Check if this is an auto direct auth (from redirect)
                auto_mode = "auto" in query and query["auto"][0] == "true"
                success = False
                
                # Try both methods to determine if user is authenticated
                # 1. Check if we're already authenticated locally
                if is_authenticated():
                    print("Already authenticated locally - using existing credentials")
                    token = get_auth_token()
                    user_id = get_user_id()
                    email = get_user_email()
                    refresh_token = get_refresh_token()
                    success = True
                # 2. If auto mode, try to extract tokens from query params
                elif auto_mode:
                    # Try to extract from query params if they exist
                    token = query.get("token", [""])[0]
                    refresh_token = query.get("refresh_token", [""])[0]
                    user_id = query.get("user_id", [""])[0]
                    email = query.get("email", [""])[0]
                    
                    if token and user_id and email:
                        print("Auto direct auth - found token data in query")
                        success = True
                    else:
                        print("Auto direct auth - no token data in query, remaining unauthenticated")
                # 3. Normal direct auth flow (explicit params)
                else:
                    token = query.get("token", [""])[0]
                    refresh_token = query.get("refresh_token", [""])[0]
                    user_id = query.get("user_id", [""])[0]
                    email = query.get("email", [""])[0]
                
                    print(f"Direct auth - token present: {bool(token)}")
                    print(f"Direct auth - user_id present: {bool(user_id)}")
                
                # Save auth data if we have it and aren't already authenticated
                if success and token and user_id and email and not is_authenticated():
                    print("Saving direct auth data...")
                    save_result = save_auth_data(token, user_id, email, refresh_token)
                    print(f"Save result: {save_result}")
                    success = save_result
                elif not token or not user_id or not email:
                    print(f"Missing required data - token: {bool(token)}, user_id: {bool(user_id)}, email: {bool(email)}")
                
                # Return a success/failure message with clear HTML
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                status = "success" if success else "failure"
                status_message = "successful!" if status == "success" else "failed"
                
                html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>TextExtract Authentication</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                        .container {{ max-width: 600px; margin: 0 auto; }}
                        .success {{ color: green; font-weight: bold; }}
                        .failure {{ color: red; font-weight: bold; }}
                    </style>
                    <script>
                        // Report status to console for debugging
                        console.log("Authentication status: {status}");
                        
                        // Signal status to any parent window that might be listening
                        if (window.opener) {{
                            try {{
                                window.opener.postMessage({{ status: "{status}" }}, "*");
                            }} catch(e) {{
                                console.error("Error posting message to opener:", e);
                            }}
                        }}
                        
                        // Auto-close after 3 seconds
                        setTimeout(function() {{
                            window.close();
                        }}, 3000);
                    </script>
                </head>
                <body>
                    <div class="container">
                        <h2>TextExtract Authentication</h2>
                        <p class="{status}">Authentication {status_message}</p>
                        <p>This window will close automatically in 3 seconds.</p>
                        <p>Status: AUTH_RESULT={status}</p>
                    </div>
                </body>
                </html>
                """
                self.wfile.write(html.encode())
                
                # Call the auth callback
                if self.auth_callback:
                    print("Calling auth callback for direct auth...")
                    try:
                        self.auth_callback(success, token, user_id, email, refresh_token)
                        print("Direct auth callback completed successfully")
                    except Exception as e:
                        print(f"Error in direct auth callback: {e}")
                        print(traceback.format_exc())
                else:
                    print("No auth callback provided for direct auth")
                
                return
            # Basic pages and redirects for already logged-in users
            elif parsed_path.path == "/" or parsed_path.path.startswith("/profile"):
                print(f"Received navigation to basic page: {parsed_path.path}")
                
                # This usually happens when user is already logged in - redirect to our direct auth handler
                # First check if we're already authenticated on the desktop app
                if is_authenticated():
                    print("Already authenticated in desktop app - handling as direct auth success")
                    token = get_auth_token()
                    user_id = get_user_id()
                    email = get_user_email()
                    refresh_token = get_refresh_token()
                    success = True
                    
                    # Create success HTML that will auto-close
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    
                    html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>TextExtract Authentication</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                            .container {{ max-width: 600px; margin: 0 auto; }}
                            .success {{ color: green; font-weight: bold; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h2>TextExtract Authentication</h2>
                            <p class="success">Successfully authenticated!</p>
                            <p>This window will close automatically in 3 seconds.</p>
                        </div>
                        <script>
                            console.log("Authentication successful, auto-closing window");
                            setTimeout(function() {{ window.close(); }}, 3000);
                        </script>
                    </body>
                    </html>
                    """
                    self.wfile.write(html.encode())
                    
                    # Call the auth callback
                    if self.auth_callback:
                        print("Calling auth callback for already authenticated session...")
                        try:
                            self.auth_callback(success, token, user_id, email, refresh_token)
                            print("Auth callback completed successfully for already authenticated session")
                        except Exception as e:
                            print(f"Error in already authenticated callback: {e}")
                            print(traceback.format_exc())
                    
                    return
                else:
                    # Redirect to direct auth with auto param
                    self.send_response(302) # Found/Redirect
                    self.send_header('Location', f"/direct_auth?auto=true")
                    self.end_headers()
                    return
            
            # For other routes, return 404
            print(f"Path not recognized: {parsed_path.path}")
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Not found. Use /callback endpoint for authentication.")
        except Exception as e:
            print(f"Error in callback handler: {e}")
            print(traceback.format_exc())
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            error_message = f"Server error: {str(e)}\n\nTraceback: {traceback.format_exc()}"
            self.wfile.write(error_message.encode())

def is_port_in_use(port):
    """Check if the given port is already in use"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    except Exception as e:
        print(f"Error checking if port is in use: {e}")
        return False  # Assume port is not in use to allow process to continue

def start_auth_callback_server(auth_callback):
    """Start the authentication callback server"""
    # Declare globals at the beginning of the function
    global AUTH_CALLBACK_PORT
    global AUTH_REDIRECT_URL
    
    # First check if the port is already in use
    if is_port_in_use(AUTH_CALLBACK_PORT):
        print(f"Port {AUTH_CALLBACK_PORT} is already in use. Attempting to close any existing server.")
        try:
            # Try to create a socket and connect to the port to see if it's our server
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(1)  # Short timeout
            test_socket.connect(('localhost', AUTH_CALLBACK_PORT))
            test_socket.close()
            
            # If we got this far, there's something already listening on this port
            # Let's try a different port
            alt_port = AUTH_CALLBACK_PORT + 1
            if not is_port_in_use(alt_port):
                print(f"Using alternative port {alt_port} for callback server")
                AUTH_CALLBACK_PORT = alt_port
                AUTH_REDIRECT_URL = f"http://localhost:{AUTH_CALLBACK_PORT}/callback"
            else:
                print(f"Both primary and alternative ports are in use. Cannot start callback server.")
                return None
                
        except (socket.timeout, ConnectionRefusedError):
            # If connection fails, the port might be in a TIME_WAIT state
            print("Port appears to be in TIME_WAIT state, trying to proceed anyway")
        except Exception as e:
            print(f"Error while checking port: {e}")
            return None
    
    try:
        # Create a handler with our callback
        handler = lambda *args, **kwargs: AuthCallbackHandler(*args, auth_callback=auth_callback, **kwargs)
        
        # Create and start the server with a timeout to handle socket errors
        server = socketserver.TCPServer(("", AUTH_CALLBACK_PORT), handler)
        server.timeout = 0.5  # Set a timeout to prevent blocking
        
        # Run the server in a background thread
        server_thread = Thread(target=server.serve_forever)
        server_thread.daemon = True  # Don't keep process alive because of this thread
        server_thread.start()
        
        print(f"Auth callback server started on port {AUTH_CALLBACK_PORT}")
        return server
    except Exception as e:
        print(f"Failed to start callback server: {e}")
        print(traceback.format_exc())
        return None

def stop_auth_callback_server(server):
    """Stop the authentication callback server"""
    if server:
        server.shutdown()
        logger.info("Auth callback server stopped")

def is_authenticated():
    """Check if user is authenticated"""
    token = get_auth_token()
    return token is not None and token != ""

def auth_callback(success, token, user_id, email, refresh_token=None, callback=None, auth_result=None, auth_completed=None):
    """Handle the callback from the authentication server"""
    print(f"Auth callback called with success={success}")
    if token:
        print(f"Received token: {token[:10]}... (truncated)")
    
    # Update auth_result if provided
    if auth_result is not None:
        auth_result["success"] = success
        if success:
            auth_result["message"] = "Authentication successful"
        else:
            auth_result["message"] = "Authentication failed"
    
    # If successful, ensure we save the data
    if success and token and user_id and email:
        print("Saving authentication data in callback...")
        save_result = save_auth_data(token, user_id, email, refresh_token)
        if not save_result:
            print("Warning: Failed to save auth data in callback")
            
        # Additional debug to ensure token is saved properly
        stored_token = get_auth_token()
        if stored_token:
            print(f"Verified token was saved: {stored_token[:10]}... (truncated)")
        else:
            print("Warning: Token not found after saving!")
            
    # Call the user-provided callback if available and successful
    if success and callback:
        try:
            print("Calling user-provided callback with successful auth")
            callback()
        except Exception as e:
            print(f"Error in user provided callback: {e}")
            print(traceback.format_exc())
        
    # Signal that authentication is complete if threading event provided
    if auth_completed is not None:
        auth_completed.set()
        
    return success

def web_authenticate(callback=None):
    """Start the web-based authentication flow"""
    print("Starting web-based authentication flow...")
    
    # First check if the user is already authenticated
    if is_authenticated():
        print("User is already authenticated, skipping web auth flow")
        # Call the callback if provided
        if callback:
            try:
                print("User already authenticated, calling success callback...")
                callback()
            except Exception as e:
                print(f"Error in auth success callback: {e}")
                print(traceback.format_exc())
        # Return success immediately
        return True, "Already authenticated"
    
    auth_result = {"success": False, "message": ""}
    auth_completed = threading.Event()
    
    # Function to directly check profile in case the callback method fails
    def check_profile_auth_status():
        try:
            print("Directly checking if user is authenticated on website...")
            # Try to fetch user profile from the API
            headers = {
                "X-Device-ID": get_device_id(),
                "X-Direct-Check": "true"
            }
            response = requests.get(f"{API_BASE_URL}/users/profile/check", 
                                   headers=headers,
                                   timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("authenticated"):
                    print("Profile check confirms user is authenticated!")
                    # Extract token data
                    token = data.get("token")
                    user_id = data.get("user_id")
                    email = data.get("email") 
                    refresh_token = data.get("refresh_token")
                    
                    if token and user_id and email:
                        print("Saving auth data from profile check...")
                        save_auth_data(token, user_id, email, refresh_token)
                        return True
            return False
        except Exception as e:
            print(f"Error in profile check: {e}")
            return False
    
    # Define the callback function that will be called when authentication completes
    def inner_auth_callback(success, token, user_id, email, refresh_token=None):
        print(f"Inner auth callback called with success={success}")
        if token:
            print(f"Received token: {token[:10]}... (truncated)")
        auth_result["success"] = success
        
        # Save the auth data
        if success and token and user_id and email:
            print("Saving auth data in inner callback...")
            save_auth_data(token, user_id, email, refresh_token)
            
        if success:
            auth_result["message"] = "Authentication successful"
            # Call user callback
            if callback:
                try:
                    print("Calling user callback from inner callback")
                    callback()
                except Exception as e:
                    print(f"Error in user callback from inner: {e}")
                    print(traceback.format_exc())
        else:
            auth_result["message"] = "Authentication failed"
            
        auth_completed.set()
    
    # Start the callback server
    print("Starting auth callback server...")
    server = start_auth_callback_server(lambda success, token, user_id, email, refresh_token=None: 
        inner_auth_callback(success, token, user_id, email, refresh_token))
    if not server:
        print("Failed to start authentication callback server")
        return False, "Failed to start authentication server. Another instance might be running."
    
    # Get device ID for authentication
    device_id = get_device_id()
    print(f"Using device ID: {device_id}")
    
    # Generate a state parameter for security
    state = str(uuid.uuid4())
    
    # Create a direct auth URL for already logged-in users
    direct_auth_url = urllib.parse.quote(f"http://localhost:{AUTH_CALLBACK_PORT}/direct_auth")
    
    # Construct the authentication URL
    auth_url = f"{API_BASE_URL}/auth/web-login?redirect_uri={urllib.parse.quote(AUTH_REDIRECT_URL)}&device_id={device_id}&state={state}&auto_login=true&direct_auth_url={direct_auth_url}"
    print(f"Authentication URL: {auth_url}")
    
    # Define a function to open the browser in a separate thread
    def open_browser_thread():
        # Open the authentication URL in the default browser
        try:
            print("Opening browser for authentication...")
            # Try different browser opening methods if one fails
            browser_opened = False
            
            # First try with the default browser
            if webbrowser.open(auth_url):
                print("Browser opened successfully using default method")
                browser_opened = True
            else:
                # Try with new=2 to force a new browser window
                print("First browser open attempt failed, trying with new=2...")
                if webbrowser.open(auth_url, new=2):
                    print("Browser opened successfully using new=2")
                    browser_opened = True
                else:
                    # Try with specific browsers
                    print("Second browser open attempt failed, trying specific browsers...")
                    for browser in ['chrome', 'firefox', 'safari', 'edge']:
                        try:
                            browser_controller = webbrowser.get(browser)
                            if browser_controller.open(auth_url):
                                print(f"Browser opened successfully using {browser}")
                                browser_opened = True
                                break
                        except Exception as e:
                            print(f"Failed to open {browser}: {e}")
                            continue
            
            # If all browser attempts failed, try OS-specific methods
            if not browser_opened:
                if os.name == 'nt':
                    print("Trying os.startfile as last resort...")
                    os.startfile(auth_url)
                    browser_opened = True
                elif sys.platform == 'darwin':  # macOS
                    print("Trying subprocess with 'open' command (macOS)...")
                    import subprocess
                    subprocess.call(['open', auth_url])
                    browser_opened = True
                elif os.environ.get('DISPLAY'):  # Linux with display
                    print("Trying subprocess with 'xdg-open' command (Linux)...")
                    import subprocess
                    subprocess.call(['xdg-open', auth_url])
                    browser_opened = True
            
            if not browser_opened:
                print("All browser opening attempts failed")
                auth_result["success"] = False
                auth_result["message"] = "Failed to open browser"
                auth_completed.set()
        
        except Exception as e:
            print(f"Error opening browser: {e}")
            print(traceback.format_exc())
            auth_result["success"] = False
            auth_result["message"] = f"Error opening browser: {str(e)}"
            auth_completed.set()
    
    # Start the browser opening in a separate thread
    browser_thread = Thread(target=open_browser_thread)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Wait for authentication to complete (with timeout)
    print(f"Waiting up to 5 minutes for authentication to complete...")
    timeout = 300  # 5 minutes timeout
    authentication_complete = auth_completed.wait(timeout)
    
    # If normal authentication flow didn't complete, check if user is already authenticated
    if not authentication_complete:
        print("Authentication event not received, checking if user is already authenticated...")
        
        # Try to check profile directly
        if check_profile_auth_status():
            print("Profile check indicates user is authenticated!")
            auth_result["success"] = True
            auth_result["message"] = "Authentication detected through profile check"
            
            # Call the callback
            if callback:
                try:
                    print("Calling success callback after profile check...")
                    callback()
                except Exception as e:
                    print(f"Error in auth success callback: {e}")
                    print(traceback.format_exc())
        else:
            print("Authentication timed out")
            auth_result["success"] = False
            auth_result["message"] = "Authentication timed out after 5 minutes"
    
    # Stop the callback server
    print("Authentication completed, stopping callback server...")
    stop_auth_callback_server(server)
    
    # Even if event not set but we might have auth data now
    if not auth_result["success"] and is_authenticated():
        print("Event not received but user is now authenticated!")
        auth_result["success"] = True
        auth_result["message"] = "Authentication succeeded through alternative channel"
        
        # Call the user-provided callback if authentication was successful
        if callback:
            try:
                print("Authentication successful (alt check), calling callback...")
                callback()
            except Exception as e:
                print(f"Error in auth success callback: {e}")
                print(traceback.format_exc())
    
    # Call the user-provided callback if authentication was successful and not already called
    elif auth_result["success"] and callback:
        try:
            print("Authentication successful, calling callback function...")
            callback()
        except Exception as e:
            print(f"Error in auth success callback: {e}")
            print(traceback.format_exc())
    
    print(f"Web authentication completed with result: {auth_result['success']}")
    return auth_result["success"], auth_result["message"]

def clear_auth_data():
    """Clear all authentication data"""
    print("Clearing all authentication data")
    try:
        if _USE_KEYRING:
            try:
                keyring.delete_password(SERVICE_NAME, TOKEN_KEY)
            except Exception:
                pass
            try:
                keyring.delete_password(SERVICE_NAME, REFRESH_TOKEN_KEY)
            except Exception:
                pass
            try:
                keyring.delete_password(SERVICE_NAME, USER_ID_KEY)
            except Exception:
                pass
            try:
                keyring.delete_password(SERVICE_NAME, EMAIL_KEY)
            except Exception:
                pass
        else:
            _fallback_storage.pop(TOKEN_KEY, None)
            _fallback_storage.pop(REFRESH_TOKEN_KEY, None)
            _fallback_storage.pop(USER_ID_KEY, None)
            _fallback_storage.pop(EMAIL_KEY, None)
        return True
    except Exception as e:
        print(f"Error clearing auth data: {e}")
        print(traceback.format_exc())
        return False

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

def register(email, password, full_name=""):
    """Register a new user"""
    print(f"Registering new user: {email}")
    
    # Validate email format
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return False, "Invalid email format"
    
    # Validate password strength
    is_valid, error_message = validate_password_strength(password)
    if not is_valid:
        return False, error_message
    
    try:
        device_id = get_device_id()
        
        # Prepare the request
        headers = {
            "Content-Type": "application/json",
            "X-Device-ID": device_id
        }
        
        data = {
            "email": email,
            "password": password,
            "full_name": full_name
        }
        
        # Make the request
        response = requests.post(
            f"{API_BASE_URL}/auth/register",
            headers=headers,
            json=data,
            timeout=10
        )
        
        # Check if successful
        if response.status_code == 201:
            response_data = response.json()
            
            # Extract token and user info
            token = response_data.get("token")
            refresh_token = response_data.get("refresh_token")
            user = response_data.get("user", {})
            user_id = user.get("id")
            
            if token and user_id:
                # Save the authentication data
                result = save_auth_data(token, user_id, email, refresh_token)
                if result:
                    return True, "Registration successful"
                else:
                    return False, "Failed to save authentication data"
            else:
                return False, "Invalid response data from registration"
        else:
            # Extract error message if available
            error_msg = "Unknown error"
            try:
                error_data = response.json()
                error_msg = error_data.get("error", "Unknown error")
            except:
                pass
                
            return False, f"Registration failed: {error_msg}"
            
    except Exception as e:
        print(f"Error during registration: {e}")
        print(traceback.format_exc())
        return False, f"Registration error: {str(e)}"

def login(email, password):
    """Login with email and password"""
    print(f"Attempting to login user: {email}")
    try:
        device_id = get_device_id()
        
        headers = {
            "Content-Type": "application/json",
            "X-Device-ID": device_id,
            "X-App-Version": os.getenv("APP_VERSION", "1.0.0")
        }
        
        payload = {
            "email": email,
            "password": password
        }
        
        # Set a reasonable timeout
        print(f"Sending login request to {API_BASE_URL}/auth/login")
        response = requests.post(
            f"{API_BASE_URL}/auth/login", 
            headers=headers,
            json=payload,
            timeout=10  # 10 seconds timeout
        )
        
        print(f"Login response status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            save_auth_data(data["token"], data["user"]["id"], email)
            return True, "Login successful"
        else:
            try:
                error_msg = response.json().get("error", "Unknown error")
            except:
                error_msg = f"HTTP {response.status_code}"
            return False, f"Login failed: {error_msg}"
            
    except requests.exceptions.ConnectionError:
        print("Connection error during login")
        return False, "Connection error: Could not connect to the authentication server"
    except requests.exceptions.Timeout:
        print("Timeout during login")
        return False, "Connection timed out. Please try again later"
    except requests.exceptions.RequestException as e:
        print(f"Request error during login: {e}")
        return False, f"Network error: {str(e)}"
    except Exception as e:
        print(f"General error during login: {e}")
        print(traceback.format_exc())
        return False, f"Login error: {str(e)}"

def logout():
    """Log out the user"""
    print("Logging out user...")
    
    # Get current tokens
    token = get_auth_token()
    refresh_token = get_refresh_token()
    
    if not token:
        print("No auth token available, user already logged out")
        clear_auth_data()
        return True, "Already logged out"
    
    try:
        # Prepare the request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "X-Device-ID": get_device_id()
        }
        
        data = {}
        if refresh_token:
            data["refresh_token"] = refresh_token
        
        # Make the request to revoke tokens on server
        response = requests.post(
            f"{API_BASE_URL}/auth/logout",
            headers=headers,
            json=data,
            timeout=10
        )
        
        # Clear local auth data regardless of server response
        clear_auth_data()
        
        # Check if successful on server side
        if response.status_code == 200:
            print("Successfully logged out on server")
            return True, "Successfully logged out"
        else:
            print(f"Server logout failed: {response.status_code}, but local data cleared")
            return True, "Local logout successful, but server logout failed"
            
    except Exception as e:
        print(f"Error during logout: {e}")
        print(traceback.format_exc())
        
        # Still clear local auth data even if server request fails
        clear_auth_data()
        return True, "Local logout successful, but server communication failed"

def refresh_token():
    """Refresh the authentication token using the refresh token"""
    print("Attempting to refresh authentication token...")
    
    # Get refresh token
    refresh_token = get_refresh_token()
    if not refresh_token:
        print("No refresh token available")
        return False, "No refresh token available"
    
    try:
        # Prepare the request
        headers = {
            "Content-Type": "application/json",
            "X-Device-ID": get_device_id()
        }
        
        data = {
            "refresh_token": refresh_token
        }
        
        # Make the request
        response = requests.post(
            f"{API_BASE_URL}/auth/refresh",
            headers=headers,
            json=data,
            timeout=10
        )
        
        # Check if successful
        if response.status_code == 200:
            response_data = response.json()
            
            # Extract token and user info
            token = response_data.get("token")
            user_id = response_data.get("user_id")
            email = response_data.get("email")
            
            if token and user_id and email:
                # Save only the new access token (keep existing refresh token)
                result = save_auth_data(token, user_id, email, refresh_token)
                return result, "Token refreshed successfully"
            else:
                print("Invalid response data from refresh token endpoint")
                return False, "Invalid response data from refresh token endpoint"
        else:
            # If refresh token is rejected or expired, clear all auth data
            if response.status_code == 401:
                print("Refresh token is invalid or expired. Clearing auth data.")
                clear_auth_data()
            
            error_msg = "Unknown error"
            try:
                error_data = response.json()
                error_msg = error_data.get("error", "Unknown error")
            except:
                pass
                
            print(f"Failed to refresh token: {response.status_code} - {error_msg}")
            return False, f"Failed to refresh token: {error_msg}"
            
    except Exception as e:
        print(f"Error refreshing token: {e}")
        print(traceback.format_exc())
        return False, f"Error refreshing token: {str(e)}"

def get_user_profile(parent_window=None):
    """Get current user profile"""
    if not is_authenticated():
        return None, "Not authenticated"
        
    try:
        token = get_auth_token()
        device_id = get_device_id()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "X-Device-ID": device_id,
            "X-App-Version": os.getenv("APP_VERSION", "1.0.0")
        }
        
        response = requests.get(
            f"{API_BASE_URL}/users/profile", 
            headers=headers
        )

        # Handle authentication errors
        if response.status_code in (401, 403):
            # Try to refresh the token first
            refresh_success, refresh_message = refresh_token()
            if refresh_success:
                # Retry with new token
                token = get_auth_token()
                headers["Authorization"] = f"Bearer {token}"
                response = requests.get(
                    f"{API_BASE_URL}/users/profile", 
                    headers=headers
                )
            else:
                # Token refresh failed, try to re-authenticate
                from src.utils.api_utils import handle_auth_error
                if handle_auth_error(parent_window):
                    # User logged in successfully, retry with new token
                    token = get_auth_token()
                    headers["Authorization"] = f"Bearer {token}"
                    response = requests.get(
                        f"{API_BASE_URL}/users/profile", 
                        headers=headers
                    )
                else:
                    # User canceled login
                    return None, "Authentication required"

        print(response.json())
        
        if response.status_code == 200:
            return response.json(), "Profile fetched"
        else:
            error_msg = response.json().get("error", "Unknown error")
            return None, f"Failed to fetch profile: {error_msg}"
            
    except Exception as e:
        return None, f"Error fetching profile: {str(e)}"

def request_password_reset(email):
    """Request a password reset email"""
    print(f"Requesting password reset for email: {email}")
    try:
        device_id = get_device_id()
        
        headers = {
            "Content-Type": "application/json",
            "X-Device-ID": device_id,
            "X-App-Version": os.getenv("APP_VERSION", "1.0.0")
        }
        
        payload = {
            "email": email
        }
        
        response = requests.post(
            f"{API_BASE_URL}/auth/request-password-reset", 
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"Password reset request response status: {response.status_code}")
        if response.status_code == 200:
            return True, "If your email is registered, you will receive a password reset link"
        else:
            try:
                error_msg = response.json().get("error", "Unknown error")
            except:
                error_msg = f"HTTP {response.status_code}"
            return False, f"Password reset request failed: {error_msg}"
            
    except Exception as e:
        print(f"Error in request_password_reset: {e}")
        print(traceback.format_exc())
        return False, f"Error: {str(e)}"

def reset_password(token, new_password):
    """Reset password using a token"""
    print(f"Resetting password with token")
    try:
        device_id = get_device_id()
        
        headers = {
            "Content-Type": "application/json",
            "X-Device-ID": device_id,
            "X-App-Version": os.getenv("APP_VERSION", "1.0.0")
        }
        
        payload = {
            "token": token,
            "new_password": new_password
        }
        
        response = requests.post(
            f"{API_BASE_URL}/auth/reset-password", 
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"Password reset response status: {response.status_code}")
        if response.status_code == 200:
            return True, "Password has been reset successfully"
        else:
            try:
                error_msg = response.json().get("error", "Unknown error")
            except:
                error_msg = f"HTTP {response.status_code}"
            return False, f"Password reset failed: {error_msg}"
            
    except Exception as e:
        print(f"Error in reset_password: {e}")
        print(traceback.format_exc())
        return False, f"Error: {str(e)}"

def request_email_verification():
    """Request a new email verification link"""
    print("Requesting email verification")
    if not is_authenticated():
        return False, "Not authenticated"
        
    try:
        token = get_auth_token()
        device_id = get_device_id()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "X-Device-ID": device_id,
            "X-App-Version": os.getenv("APP_VERSION", "1.0.0")
        }
        
        response = requests.post(
            f"{API_BASE_URL}/auth/request-email-verification", 
            headers=headers,
            timeout=10
        )
        
        print(f"Email verification request response status: {response.status_code}")
        if response.status_code == 200:
            return True, "Verification email has been sent"
        else:
            try:
                error_msg = response.json().get("error", "Unknown error")
            except:
                error_msg = f"HTTP {response.status_code}"
            return False, f"Email verification request failed: {error_msg}"
            
    except Exception as e:
        print(f"Error in request_email_verification: {e}")
        print(traceback.format_exc())
        return False, f"Error: {str(e)}"

def delete_account(password):
    """Delete the user's account"""
    print("Requesting account deletion")
    if not is_authenticated():
        return False, "Not authenticated"
        
    try:
        token = get_auth_token()
        device_id = get_device_id()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "X-Device-ID": device_id,
            "X-App-Version": os.getenv("APP_VERSION", "1.0.0")
        }
        
        payload = {
            "password": password
        }
        
        response = requests.delete(
            f"{API_BASE_URL}/auth/delete-account", 
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"Account deletion response status: {response.status_code}")
        if response.status_code == 200:
            # Clear auth data on successful deletion
            clear_auth_data()
            return True, "Account deleted successfully"
        else:
            try:
                error_msg = response.json().get("error", "Unknown error")
            except:
                error_msg = f"HTTP {response.status_code}"
            return False, f"Account deletion failed: {error_msg}"
            
    except Exception as e:
        print(f"Error in delete_account: {e}")
        print(traceback.format_exc())
        return False, f"Error: {str(e)}"

class AuthDialog:
    """Dialog for user login or registration"""
    
    def __init__(self, parent, title="Authentication Required"):
        print(f"Initializing AuthDialog with parent: {parent}, title: {title}")
        self.parent = parent
        self.result = False
        
        try:
            # Ensure parent is visible
            parent.update_idletasks()
            
            # Create dialog first
            self.dialog = tk.Toplevel(parent)
            self.dialog.title(title)
            self.dialog.geometry("400x450")
            self.dialog.resizable(False, False)
            self.dialog.transient(parent)
            self.dialog.grab_set()
            
            # Make dialog always on top to ensure visibility
            self.dialog.attributes('-topmost', True)
            
            # Center the dialog
            self.center_window()
            
            # Create UI
            self.create_ui()
            
            # Make sure dialog doesn't close unexpectedly
            self.dialog.protocol("WM_DELETE_WINDOW", self.on_close)
            print("AuthDialog initialized successfully")
        except Exception as e:
            print(f"Error initializing AuthDialog: {e}")
            print(traceback.format_exc())
            raise
            
    def on_close(self):
        """Handle dialog close"""
        print("Dialog close requested by user")
        self.result = False
        if hasattr(self, 'dialog') and self.dialog:
            self.dialog.destroy()
        
    def center_window(self):
        """Center the dialog on screen"""
        try:
            if not hasattr(self, 'dialog') or not self.dialog:
                return
                
            self.dialog.update_idletasks()
            width = self.dialog.winfo_width()
            height = self.dialog.winfo_height()
            x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
            self.dialog.geometry(f'{width}x{height}+{x}+{y}')
        except Exception as e:
            print(f"Error centering window: {e}")
            # Continue anyway, this is not critical

    def create_ui(self):
        """Create UI elements"""
        if not hasattr(self, 'dialog') or not self.dialog:
            return
            
        # Main frame with padding
        main_frame = tk.Frame(self.dialog, padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # App logo/name
        title_label = tk.Label(main_frame, text="TextExtract", font=("Arial", 18, "bold"))
        title_label.pack(pady=10)
        
        subtitle_label = tk.Label(main_frame, text="Sign in to continue", font=("Arial", 12))
        subtitle_label.pack(pady=5)
        
        # Create tabs for login and register
        tab_frame = tk.Frame(main_frame)
        tab_frame.pack(fill='x', pady=15)
        
        self.login_btn = tk.Button(tab_frame, text="Login", width=15, 
                                  command=self.show_login)
        self.login_btn.pack(side='left', padx=5)
        
        self.register_btn = tk.Button(tab_frame, text="Create Account", width=15,
                                     command=self.show_register)
        self.register_btn.pack(side='right', padx=5)
        
        # Container for form (login/register)
        self.form_container = tk.Frame(main_frame)
        self.form_container.pack(fill='both', expand=True)
        
        # Status message
        self.status_var = tk.StringVar()
        status_label = tk.Label(main_frame, textvariable=self.status_var, 
                               fg="red", wraplength=350)
        status_label.pack(pady=10)
        
        # Show login form by default
        self.show_login()
        
        # Set dialog to close on Escape key
        self.dialog.bind("<Escape>", lambda event: self.on_close())
        
    def show_login(self):
        """Show login form"""
        # Clear the form container
        for widget in self.form_container.winfo_children():
            widget.destroy()
            
        # Update button appearance
        self.login_btn.config(relief="sunken", bg="#e0e0e0")
        self.register_btn.config(relief="raised", bg="SystemButtonFace")
            
        # Create login form
        tk.Label(self.form_container, text="Email:").pack(anchor='w', pady=(10, 5))
        self.email_entry = tk.Entry(self.form_container, width=40)
        self.email_entry.pack(fill='x', pady=5)
        
        tk.Label(self.form_container, text="Password:").pack(anchor='w', pady=(10, 5))
        self.password_entry = tk.Entry(self.form_container, width=40, show="*")
        self.password_entry.pack(fill='x', pady=5)
        
        # Add a forgot password link
        forgot_btn = tk.Button(self.form_container, text="Forgot Password?", 
                              bd=0, fg="blue", command=self.show_forgot_password)
        forgot_btn.pack(anchor='e', pady=(0, 10))
        
        # Login button
        login_button = tk.Button(self.form_container, text="Login", 
                                width=20, command=self.perform_login)
        login_button.pack(pady=20)
        
        # Set focus to email entry
        self.email_entry.focus_set()
        
    def show_register(self):
        """Show registration form"""
        # Clear the form container
        for widget in self.form_container.winfo_children():
            widget.destroy()
            
        # Update button appearance
        self.login_btn.config(relief="raised", bg="SystemButtonFace")
        self.register_btn.config(relief="sunken", bg="#e0e0e0")
            
        # Create registration form
        tk.Label(self.form_container, text="Full Name:").pack(anchor='w', pady=(10, 5))
        self.name_entry = tk.Entry(self.form_container, width=40)
        self.name_entry.pack(fill='x', pady=5)
        
        tk.Label(self.form_container, text="Email:").pack(anchor='w', pady=(10, 5))
        self.email_entry = tk.Entry(self.form_container, width=40)
        self.email_entry.pack(fill='x', pady=5)
        
        tk.Label(self.form_container, text="Password:").pack(anchor='w', pady=(10, 5))
        self.password_entry = tk.Entry(self.form_container, width=40, show="*")
        self.password_entry.pack(fill='x', pady=5)
        
        # Register button
        register_button = tk.Button(self.form_container, text="Create Account", 
                                   width=20, command=self.perform_register)
        register_button.pack(pady=20)
        
        # Set focus to name entry
        self.name_entry.focus_set()
        
    def show_forgot_password(self):
        """Show forgot password form"""
        # Create a dialog for password reset
        reset_dialog = PasswordResetRequestDialog(self.dialog)
        reset_dialog.show()
        
    def perform_login(self):
        """Handle login button click"""
        print(f"Login attempt with email: {self.email_entry.get().strip()}")
        self.status_var.set("Logging in...")
        self.dialog.update()
        
        email = self.email_entry.get().strip()
        password = self.password_entry.get()
        
        if not email or not password:
            self.status_var.set("Please enter both email and password")
            return
            
        # Perform login in a separate thread to avoid freezing UI
        def login_thread():
            try:
                print(f"Sending login request to API for {email}")
                success, message = login(email, password)
                print(f"Login response: success={success}, message={message}")
                
                # Update UI from the main thread
                self.dialog.after(0, lambda: self.handle_auth_result(success, message))
            except Exception as e:
                print(f"Error in login thread: {e}")
                print(traceback.format_exc())
                self.dialog.after(0, lambda: self.status_var.set(f"Login error: {str(e)}"))
            
        threading.Thread(target=login_thread).start()
        
    def perform_register(self):
        """Handle register button click"""
        print(f"Register attempt with email: {self.email_entry.get().strip()}")
        self.status_var.set("Creating account...")
        self.dialog.update()
        
        full_name = self.name_entry.get().strip()
        email = self.email_entry.get().strip()
        password = self.password_entry.get()
        
        if not email or not password:
            self.status_var.set("Please enter email and password")
            return
            
        # Perform registration in a separate thread to avoid freezing UI
        def register_thread():
            try:
                print(f"Sending register request to API for {email}")
                success, message = register(email, password, full_name)
                print(f"Register response: success={success}, message={message}")
                
                # Update UI from the main thread
                self.dialog.after(0, lambda: self.handle_auth_result(success, message))
            except Exception as e:
                print(f"Error in register thread: {e}")
                print(traceback.format_exc())
                self.dialog.after(0, lambda: self.status_var.set(f"Registration error: {str(e)}"))
            
        threading.Thread(target=register_thread).start()
        
    def handle_auth_result(self, success, message):
        """Handle authentication result"""
        print(f"Authentication result: success={success}, message={message}")
        if success:
            self.result = True
            self.dialog.destroy()
        else:
            self.status_var.set(message)
        
    def show(self):
        """Show the dialog and return if login was successful"""
        print("Showing AuthDialog and waiting for result...")
        try:
            if not hasattr(self, 'dialog') or not self.dialog:
                print("Dialog not initialized properly")
                return False
                
            # Force parent to be visible momentarily to ensure dialog appears properly
            if self.parent.state() == 'withdrawn':
                print("Parent is withdrawn, making visible momentarily")
                self.parent.deiconify()
                self.parent.update()
            
            # Make sure the dialog is displayed properly
            self.dialog.deiconify()
            self.dialog.lift()
            self.dialog.focus_force()
            self.dialog.attributes('-topmost', True)
            self.dialog.update()
            
            # Add a timeout check to make sure dialog is visible
            def check_visibility():
                if not self.dialog.winfo_viewable():
                    print("Dialog not visible, attempting to show again")
                    self.dialog.deiconify()
                    self.dialog.lift()
                    self.dialog.focus_force()
                
            self.parent.after(500, check_visibility)
            
            # Make sure parent waits for this window
            self.parent.wait_window(self.dialog)
            
            # Re-hide parent if it was hidden before
            if self.parent.state() != 'withdrawn':
                self.parent.withdraw()
            
            print(f"AuthDialog closed, result={self.result}")
            return self.result
        except Exception as e:
            print(f"Error showing dialog: {e}")
            print(traceback.format_exc())
            return False

class PasswordResetRequestDialog:
    """Dialog for requesting password reset"""
    
    def __init__(self, parent):
        self.parent = parent
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Reset Password")
        self.dialog.geometry("350x200")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Make dialog always on top to ensure visibility
        self.dialog.attributes('-topmost', True)
        
        # Center the dialog
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')
        
        # Create UI
        self.create_ui()
        
    def create_ui(self):
        # Main frame with padding
        main_frame = tk.Frame(self.dialog, padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # Instructions
        tk.Label(main_frame, text="Enter your email address to receive a password reset link:", 
                wraplength=300).pack(pady=(0, 15))
        
        # Email field
        tk.Label(main_frame, text="Email:").pack(anchor='w')
        self.email_entry = tk.Entry(main_frame, width=40)
        self.email_entry.pack(fill='x', pady=5)
        
        # Status message
        self.status_var = tk.StringVar()
        tk.Label(main_frame, textvariable=self.status_var, fg="red", wraplength=300).pack(pady=5)
        
        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(15, 0))
        
        cancel_btn = tk.Button(button_frame, text="Cancel", command=self.dialog.destroy)
        cancel_btn.pack(side='left', padx=5)
        
        reset_btn = tk.Button(button_frame, text="Send Reset Link", command=self.request_reset)
        reset_btn.pack(side='right', padx=5)
        
        # Set focus to email entry
        self.email_entry.focus_set()
        
    def request_reset(self):
        """Request password reset"""
        email = self.email_entry.get().strip()
        
        if not email:
            self.status_var.set("Please enter your email address")
            return
            
        self.status_var.set("Sending reset link...")
        self.dialog.update()
        
        # Start request in a separate thread
        def reset_thread():
            try:
                success, message = request_password_reset(email)
                # Update UI from the main thread
                self.dialog.after(0, lambda: self.handle_reset_result(success, message))
            except Exception as e:
                print(f"Error in reset thread: {e}")
                print(traceback.format_exc())
                self.dialog.after(0, lambda: self.status_var.set(f"Error: {str(e)}"))
                
        threading.Thread(target=reset_thread).start()
        
    def handle_reset_result(self, success, message):
        """Handle reset result"""
        self.status_var.set(message)
        
        if success:
            # Close the dialog after a delay
            self.dialog.after(3000, self.dialog.destroy)
            
    def show(self):
        """Show the dialog"""
        self.dialog.focus_set()
        self.dialog.wait_window()

class PasswordResetDialog:
    """Dialog for resetting password with a token"""
    
    def __init__(self, parent, token):
        self.parent = parent
        self.token = token
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Set New Password")
        self.dialog.geometry("350x250")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Make dialog always on top to ensure visibility
        self.dialog.attributes('-topmost', True)
        
        # Center the dialog
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')
        
        # Create UI
        self.create_ui()
        
    def create_ui(self):
        # Main frame with padding
        main_frame = tk.Frame(self.dialog, padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # Instructions
        tk.Label(main_frame, text="Enter your new password:", 
                wraplength=300).pack(pady=(0, 15))
        
        # Password field
        tk.Label(main_frame, text="New Password:").pack(anchor='w')
        self.password_entry = tk.Entry(main_frame, width=40, show="*")
        self.password_entry.pack(fill='x', pady=5)
        
        # Confirm password field
        tk.Label(main_frame, text="Confirm Password:").pack(anchor='w', pady=(10, 0))
        self.confirm_entry = tk.Entry(main_frame, width=40, show="*")
        self.confirm_entry.pack(fill='x', pady=5)
        
        # Status message
        self.status_var = tk.StringVar()
        tk.Label(main_frame, textvariable=self.status_var, fg="red", wraplength=300).pack(pady=5)
        
        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(15, 0))
        
        cancel_btn = tk.Button(button_frame, text="Cancel", command=self.dialog.destroy)
        cancel_btn.pack(side='left', padx=5)
        
        reset_btn = tk.Button(button_frame, text="Reset Password", command=self.reset_password)
        reset_btn.pack(side='right', padx=5)
        
        # Set focus to password entry
        self.password_entry.focus_set()
        
    def reset_password(self):
        """Reset password"""
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()
        
        if not password:
            self.status_var.set("Please enter a new password")
            return
            
        if password != confirm:
            self.status_var.set("Passwords do not match")
            return
            
        self.status_var.set("Resetting password...")
        self.dialog.update()
        
        # Start request in a separate thread
        def reset_thread():
            try:
                success, message = reset_password(self.token, password)
                # Update UI from the main thread
                self.dialog.after(0, lambda: self.handle_reset_result(success, message))
            except Exception as e:
                print(f"Error in reset thread: {e}")
                print(traceback.format_exc())
                self.dialog.after(0, lambda: self.status_var.set(f"Error: {str(e)}"))
                
        threading.Thread(target=reset_thread).start()
        
    def handle_reset_result(self, success, message):
        """Handle reset result"""
        self.status_var.set(message)
        
        if success:
            # Show success message
            messagebox.showinfo("Success", message)
            # Close the dialog
            self.dialog.destroy()
            
    def show(self):
        """Show the dialog"""
        self.dialog.focus_set()
        self.dialog.wait_window()

# Utility function to handle password reset tokens from URLs
def handle_password_reset_token(parent, token):
    """Handle password reset token from URL"""
    reset_dialog = PasswordResetDialog(parent, token)
    reset_dialog.show()

def open_browser_url(url):
    """Open URL in default browser"""
    try:
        webbrowser.open(url)
        return True
    except Exception as e:
        print(f"Error opening URL: {e}")
        return False

def reset_authentication_state():
    """For debugging: Completely reset all authentication state"""
    print("Completely resetting all authentication state")
    
    # Clear all auth data in keyring or memory storage
    clear_auth_data()
    
    # Clear any running servers
    try:
        # Check if there's a socket open on the auth callback port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', AUTH_CALLBACK_PORT))
        sock.close()
        
        if result == 0:
            print(f"Port {AUTH_CALLBACK_PORT} is in use, attempting to close it")
            # Just in case there's a hanging server instance
            dummy_server = socketserver.TCPServer(("", AUTH_CALLBACK_PORT + 1), http.server.SimpleHTTPRequestHandler)
            dummy_server.server_close()
    except Exception as e:
        print(f"Error checking for open servers: {e}")
    
    print("Authentication state reset complete")
    return True 