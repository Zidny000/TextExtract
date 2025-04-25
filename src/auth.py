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

# Set up basic logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("auth")

print("Initializing auth module...")

# API Base URL - change this to your production URL when deploying
API_BASE_URL = "http://localhost:5000"
print(f"Using API endpoint: {API_BASE_URL}")

# Key for storing auth token in keyring
SERVICE_NAME = "TextExtract"
ACCOUNT_NAME = "textextract_user"
TOKEN_KEY = "auth_token"
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

def save_auth_data(token, user_id, email):
    """Save authentication data securely using keyring or fallback storage"""
    print(f"Saving auth data for email: {email}")
    try:
        if _USE_KEYRING:
            keyring.set_password(SERVICE_NAME, TOKEN_KEY, token)
            keyring.set_password(SERVICE_NAME, USER_ID_KEY, user_id)
            keyring.set_password(SERVICE_NAME, EMAIL_KEY, email)
        else:
            _fallback_storage[TOKEN_KEY] = token
            _fallback_storage[USER_ID_KEY] = user_id
            _fallback_storage[EMAIL_KEY] = email
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
    try:
        token = get_auth_token()
        is_auth = token is not None and token != ""
        print(f"Authentication check: {is_auth}")
        return is_auth
    except Exception as e:
        print(f"Error checking authentication: {e}")
        print(traceback.format_exc())
        return False

def clear_auth_data():
    """Clear all authentication data"""
    print("Clearing auth data")
    try:
        if _USE_KEYRING:
            keyring.set_password(SERVICE_NAME, TOKEN_KEY, "")
            keyring.set_password(SERVICE_NAME, USER_ID_KEY, "")
            keyring.set_password(SERVICE_NAME, EMAIL_KEY, "")
        else:
            _fallback_storage[TOKEN_KEY] = ""
            _fallback_storage[USER_ID_KEY] = ""
            _fallback_storage[EMAIL_KEY] = ""
        return True
    except Exception as e:
        print(f"Error clearing auth data: {e}")
        return False

def register(email, password, full_name=""):
    """Register a new user account"""
    print(f"Attempting to register user: {email}")
    try:
        device_id = get_device_id()
        
        headers = {
            "Content-Type": "application/json",
            "X-Device-ID": device_id,
            "X-App-Version": os.getenv("APP_VERSION", "1.0.0")
        }
        
        payload = {
            "email": email,
            "password": password,
            "full_name": full_name
        }
        
        # Set a reasonable timeout
        print(f"Sending registration request to {API_BASE_URL}/auth/register")
        response = requests.post(
            f"{API_BASE_URL}/auth/register", 
            headers=headers,
            json=payload,
            timeout=10  # 10 seconds timeout
        )
        
        print(f"Registration response status: {response.status_code}")
        if response.status_code == 201:
            data = response.json()
            save_auth_data(data["token"], data["user"]["id"], email)
            return True, "Registration successful"
        else:
            try:
                error_msg = response.json().get("error", "Unknown error")
            except:
                error_msg = f"HTTP {response.status_code}"
            return False, f"Registration failed: {error_msg}"
            
    except requests.exceptions.ConnectionError:
        print("Connection error during registration")
        return False, "Connection error: Could not connect to the authentication server"
    except requests.exceptions.Timeout:
        print("Timeout during registration")
        return False, "Connection timed out. Please try again later"
    except requests.exceptions.RequestException as e:
        print(f"Request error during registration: {e}")
        return False, f"Network error: {str(e)}"
    except Exception as e:
        print(f"General error during registration: {e}")
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
    """Logout current user"""
    clear_auth_data()
    return True, "Logout successful"

def refresh_token():
    """Refresh the authentication token"""
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
            f"{API_BASE_URL}/auth/refresh", 
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            keyring.set_password(SERVICE_NAME, TOKEN_KEY, data["token"])
            return True, "Token refreshed"
        else:
            error_msg = response.json().get("error", "Unknown error")
            return False, f"Token refresh failed: {error_msg}"
            
    except Exception as e:
        return False, f"Token refresh error: {str(e)}"

def get_user_profile():
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
            
            # Create dialog
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
            
            # Ensure dialog is visible and brought to front
            self.dialog.update_idletasks()
            self.dialog.deiconify()
            self.dialog.lift()
            
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
        self.dialog.destroy()
        
    def center_window(self):
        """Center the dialog on screen"""
        try:
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
        self.dialog.bind("<Escape>", lambda event: self.dialog.destroy())
        
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

class UserProfileDialog:
    """Enhanced user profile dialog with account management options"""
    
    def __init__(self, parent, profile_data):
        self.parent = parent
        self.profile_data = profile_data
        self.user = profile_data["user"]
        self.usage = profile_data["usage"]
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("User Profile")
        self.dialog.geometry("450x500")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
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
        
        # User info section
        tk.Label(main_frame, text="User Profile", font=("Arial", 16, "bold")).pack(pady=(0, 15))
        
        # Create a notebook for tabs
        import tkinter.ttk as ttk
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True, pady=(10, 15))
        
        # Profile tab
        profile_frame = tk.Frame(self.notebook)
        self.notebook.add(profile_frame, text="Profile")
        
        # Usage tab
        usage_frame = tk.Frame(self.notebook)
        self.notebook.add(usage_frame, text="Usage")
        
        # Account tab
        account_frame = tk.Frame(self.notebook)
        self.notebook.add(account_frame, text="Account")
        
        # Build Profile tab
        self.build_profile_tab(profile_frame)
        
        # Build Usage tab
        self.build_usage_tab(usage_frame)
        
        # Build Account tab
        self.build_account_tab(account_frame)
        
        # Button frame at the bottom
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(15, 0))
        
        # Close button
        close_btn = tk.Button(button_frame, text="Close", command=self.dialog.destroy)
        close_btn.pack(side='right', padx=5)
        
    def build_profile_tab(self, parent):
        # Email
        tk.Label(parent, text="Email:", font=("Arial", 10, "bold"), anchor='w').grid(row=0, column=0, sticky='w', pady=5, padx=5)
        tk.Label(parent, text=self.user.get("email", "Unknown"), anchor='w').grid(row=0, column=1, sticky='w', pady=5)
        
        # Email verification status
        is_verified = self.user.get("email_verified", False)
        status_text = "Verified" if is_verified else "Not Verified"
        status_color = "green" if is_verified else "red"
        
        tk.Label(parent, text="Status:", font=("Arial", 10, "bold"), anchor='w').grid(row=1, column=0, sticky='w', pady=5, padx=5)
        status_label = tk.Label(parent, text=status_text, fg=status_color, anchor='w')
        status_label.grid(row=1, column=1, sticky='w', pady=5)
        
        # Verification button if not verified
        if not is_verified:
            verify_btn = tk.Button(parent, text="Verify Email", command=self.request_verification)
            verify_btn.grid(row=1, column=2, padx=5)
        
        # Full name
        tk.Label(parent, text="Name:", font=("Arial", 10, "bold"), anchor='w').grid(row=2, column=0, sticky='w', pady=5, padx=5)
        self.name_var = tk.StringVar(value=self.user.get("full_name", ""))
        name_entry = tk.Entry(parent, textvariable=self.name_var, width=30)
        name_entry.grid(row=2, column=1, sticky='w', pady=5, columnspan=2)
        
        # Plan
        tk.Label(parent, text="Plan:", font=("Arial", 10, "bold"), anchor='w').grid(row=3, column=0, sticky='w', pady=5, padx=5)
        plan_text = self.user.get("plan_type", "Free").capitalize()
        tk.Label(parent, text=plan_text, anchor='w').grid(row=3, column=1, sticky='w', pady=5)
        
        # Member since
        tk.Label(parent, text="Member Since:", font=("Arial", 10, "bold"), anchor='w').grid(row=4, column=0, sticky='w', pady=5, padx=5)
        created_date = self.user.get("created_at", "Unknown")
        # Format date if it's a string
        if isinstance(created_date, str) and 'T' in created_date:
            try:
                from datetime import datetime
                date_obj = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                created_date = date_obj.strftime("%B %d, %Y")
            except:
                pass
        tk.Label(parent, text=created_date, anchor='w').grid(row=4, column=1, sticky='w', pady=5)
        
        # Save button
        save_btn = tk.Button(parent, text="Save Changes", command=self.save_profile)
        save_btn.grid(row=5, column=1, sticky='w', pady=15)
        
        # Status message
        self.profile_status_var = tk.StringVar()
        tk.Label(parent, textvariable=self.profile_status_var, fg="red").grid(row=6, column=0, columnspan=3, pady=5)
        
    def build_usage_tab(self, parent):
        # Today's usage
        tk.Label(parent, text="Today's Usage:", font=("Arial", 10, "bold"), anchor='w').grid(row=0, column=0, sticky='w', pady=10, padx=5)
        tk.Label(parent, text=f"{self.usage.get('today_requests', 0)} requests used", anchor='w').grid(row=0, column=1, sticky='w', pady=10)
        
        # Remaining requests
        tk.Label(parent, text="Remaining Requests:", font=("Arial", 10, "bold"), anchor='w').grid(row=1, column=0, sticky='w', pady=10, padx=5)
        tk.Label(parent, text=f"{self.usage.get('remaining_requests', 0)} of {self.usage.get('plan_limit', 0)}", anchor='w').grid(row=1, column=1, sticky='w', pady=10)
        
        # Progress bar for usage
        import tkinter.ttk as ttk
        tk.Label(parent, text="Usage Progress:", font=("Arial", 10, "bold"), anchor='w').grid(row=2, column=0, sticky='w', pady=10, padx=5)
        
        try:
            used = int(self.usage.get('today_requests', 0))
            total = int(self.usage.get('plan_limit', 100))
            progress = min(used / total * 100 if total > 0 else 0, 100)
        except (ValueError, ZeroDivisionError):
            progress = 0
            
        progress_bar = ttk.Progressbar(parent, orient="horizontal", length=200, mode="determinate")
        progress_bar["value"] = progress
        progress_bar.grid(row=2, column=1, sticky='w', pady=10)
        
        # Devices section
        tk.Label(parent, text="Registered Devices:", font=("Arial", 10, "bold"), anchor='w').grid(row=3, column=0, sticky='w', pady=(20,10), padx=5, columnspan=2)
        
        # Devices list (in a frame with scrollbar if needed)
        devices_frame = tk.Frame(parent)
        devices_frame.grid(row=4, column=0, columnspan=2, sticky='ew', padx=5)
        
        devices = self.profile_data.get("devices", [])
        if devices:
            for i, device in enumerate(devices[:5]):  # Show max 5 devices
                device_name = device.get("device_name", "Unknown Device")
                device_type = device.get("device_type", "")
                if device_type:
                    device_name = f"{device_name} ({device_type})"
                    
                tk.Label(devices_frame, text=device_name, anchor='w').grid(row=i, column=0, sticky='w', pady=2)
                last_active = device.get("last_active", "")
                if last_active and isinstance(last_active, str) and 'T' in last_active:
                    try:
                        from datetime import datetime
                        date_obj = datetime.fromisoformat(last_active.replace('Z', '+00:00'))
                        last_active = date_obj.strftime("%b %d, %Y")
                    except:
                        pass
                tk.Label(devices_frame, text=f"Last active: {last_active}", anchor='w', fg="gray").grid(row=i, column=1, sticky='w', pady=2, padx=10)
        else:
            tk.Label(devices_frame, text="No devices registered", fg="gray").grid(row=0, column=0, sticky='w', pady=5)
            
    def build_account_tab(self, parent):
        # Change password section
        tk.Label(parent, text="Change Password", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky='w', pady=(10,15), padx=5, columnspan=2)
        
        change_pwd_btn = tk.Button(parent, text="Change Password", width=20, command=self.show_change_password)
        change_pwd_btn.grid(row=1, column=0, sticky='w', padx=5, pady=5)
        
        # Account management section
        tk.Label(parent, text="Account Management", font=("Arial", 12, "bold")).grid(row=3, column=0, sticky='w', pady=(30,15), padx=5, columnspan=2)
        
        delete_btn = tk.Button(parent, text="Delete Account", width=20, fg="red", command=self.confirm_delete_account)
        delete_btn.grid(row=4, column=0, sticky='w', padx=5, pady=5)
        
        # Warning label
        tk.Label(parent, text="Warning: Account deletion is permanent and cannot be undone.", 
                fg="red", wraplength=350).grid(row=5, column=0, sticky='w', padx=5, pady=10, columnspan=2)
                
    def save_profile(self):
        """Save profile changes"""
        self.profile_status_var.set("Saving changes...")
        self.dialog.update()
        
        new_name = self.name_var.get().strip()
        
        # Update user profile in a separate thread
        def update_thread():
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
                    "full_name": new_name
                }
                
                response = requests.put(
                    f"{API_BASE_URL}/users/profile", 
                    headers=headers,
                    json=payload,
                    timeout=10
                )
                
                if response.status_code == 200:
                    # Update UI from main thread
                    self.dialog.after(0, lambda: self.profile_status_var.set("Profile updated successfully"))
                    # Update local data
                    self.user["full_name"] = new_name
                else:
                    error_msg = "Failed to update profile"
                    try:
                        error_msg = response.json().get("error", error_msg)
                    except:
                        pass
                    self.dialog.after(0, lambda: self.profile_status_var.set(error_msg))
            except Exception as e:
                print(f"Error updating profile: {e}")
                self.dialog.after(0, lambda: self.profile_status_var.set(f"Error: {str(e)}"))
                
        threading.Thread(target=update_thread).start()
        
    def request_verification(self):
        """Request email verification"""
        # Call the API in a separate thread
        def verify_thread():
            success, message = request_email_verification()
            if success:
                messagebox.showinfo("Verification Email Sent", 
                                   "A verification email has been sent to your email address. Please check your inbox and follow the instructions.")
            else:
                messagebox.showerror("Error", f"Failed to send verification email: {message}")
                
        threading.Thread(target=verify_thread).start()
        
    def show_change_password(self):
        """Show change password dialog"""
        # We'll use the password reset request dialog to trigger the reset flow
        reset_dialog = PasswordResetRequestDialog(self.dialog)
        reset_dialog.email_entry.insert(0, self.user.get("email", ""))
        reset_dialog.email_entry.config(state='disabled')  # Don't allow changing email
        reset_dialog.show()
        
    def confirm_delete_account(self):
        """Confirm account deletion"""
        if messagebox.askyesno("Confirm Deletion", 
                              "Are you sure you want to delete your account? This action cannot be undone and all your data will be permanently deleted.",
                              icon="warning"):
            # Show password confirmation dialog
            password = simpledialog.askstring("Password Required", 
                                            "Please enter your password to confirm account deletion:",
                                            show='*',
                                            parent=self.dialog)
            
            if password:
                # Call delete account in a separate thread
                def delete_thread():
                    success, message = delete_account(password)
                    if success:
                        # Close dialog and show success message
                        self.dialog.after(0, self.dialog.destroy)
                        messagebox.showinfo("Account Deleted", "Your account has been successfully deleted.")
                        
                        # Force logout/app restart
                        try:
                            from main import exit_application
                            exit_application()
                        except:
                            messagebox.showinfo("Restart Required", "Please restart the application to complete the account deletion process.")
                    else:
                        messagebox.showerror("Error", f"Failed to delete account: {message}")
                        
                threading.Thread(target=delete_thread).start()
                
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