import os
import requests
import uuid
import logging
import sys
import traceback
import threading
import webbrowser
import socket
import http.server
import socketserver
import urllib.parse
from threading import Thread


# Set up basic logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("auth")

print("Initializing auth module...")

# Import API configuration
from src.config import get_api_url, get_frontend_url

# API Base URL - centralized configuration
API_BASE_URL = get_api_url()
print(f"Using API endpoint: {API_BASE_URL}")

# Helper function to determine appropriate protocol for local callbacks
def get_callback_protocol():
    # In production mode, we might need HTTPS
    # For local development, we use HTTP
    return "https" if "https://" in get_api_url() else "http"

# Auth callback server settings
AUTH_CALLBACK_PORT = 9845  # Choose an available port
AUTH_REDIRECT_URL = f"{get_callback_protocol()}://localhost:{AUTH_CALLBACK_PORT}/callback"

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

def is_authenticated():
    """Check if user is authenticated"""
    token = get_auth_token()
    return token is not None and token != ""

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
                AUTH_REDIRECT_URL = f"{get_callback_protocol()}://localhost:{AUTH_CALLBACK_PORT}/callback"
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
    state = str(uuid.uuid4())    # Create a direct auth URL for already logged-in users
    direct_auth_url = urllib.parse.quote(f"{get_callback_protocol()}://localhost:{AUTH_CALLBACK_PORT}/direct_auth")
    
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

# Utility function to handle password reset tokens from URLs
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