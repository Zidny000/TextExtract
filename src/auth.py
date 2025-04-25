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
        
        if response.status_code == 200:
            return response.json(), "Profile fetched"
        else:
            error_msg = response.json().get("error", "Unknown error")
            return None, f"Failed to fetch profile: {error_msg}"
            
    except Exception as e:
        return None, f"Error fetching profile: {str(e)}"

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