"""
Authentication dialog for login and registration.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable, Dict, Any
import logging
import threading
import traceback

from src.ui.base_dialog import BaseDialog
import src.auth as auth

# Configure logger
logger = logging.getLogger(__name__)

# Track active auth dialogs to prevent multiple dialogs
_active_auth_dialogs = {}

class AuthDialog(BaseDialog):
    """Dialog for user login or registration"""
    
    def __init__(self, parent, title="Authentication Required", on_auth_success: Optional[Callable] = None):
        """
        Initialize the authentication dialog.
        
        Args:
            parent: The parent window
            title: The dialog title
            on_auth_success: Optional callback to execute on successful authentication
        """
        self.on_auth_success = on_auth_success
        self.current_view = "login"  # Can be "login", "register", or "forgot_password"
        self.dialog_id = id(self)
        
        # Track this dialog
        _active_auth_dialogs[self.dialog_id] = self
        
        # Initialize the base dialog
        super().__init__(
            parent=parent,
            title=title,
            size=(400, 450),
            resizable=False,
            modal=True,
            topmost=True,
            centered=True
        )
        
        # Create the dialog window
        self._create_dialog()
        
        # Create the UI
        self._create_ui()
        
        # Set up close handler
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Show login form by default
        self.show_login()
    
    def _create_ui(self):
        """Create the dialog UI"""
        # Main frame with padding
        self.main_frame = ttk.Frame(self.dialog, padding=20)
        self.main_frame.pack(fill='both', expand=True)
        
        # App logo/name
        title_label = ttk.Label(self.main_frame, text="TextExtract", font=("Arial", 18, "bold"))
        title_label.pack(pady=10)
        
        self.subtitle_var = tk.StringVar(value="Sign in to continue")
        subtitle_label = ttk.Label(self.main_frame, textvariable=self.subtitle_var, font=("Arial", 12))
        subtitle_label.pack(pady=5)
        
        # Create tabs for login and register
        tab_frame = ttk.Frame(self.main_frame)
        tab_frame.pack(fill='x', pady=15)
        
        self.login_btn = ttk.Button(tab_frame, text="Login", width=15, 
                                   command=self.show_login)
        self.login_btn.pack(side='left', padx=5)
        
        self.register_btn = ttk.Button(tab_frame, text="Create Account", width=15,
                                      command=self.show_register)
        self.register_btn.pack(side='right', padx=5)
        
        # Container for form (login/register)
        self.form_container = ttk.Frame(self.main_frame)
        self.form_container.pack(fill='both', expand=True)
        
        # Status message
        self.status_var = tk.StringVar()
        status_label = ttk.Label(self.main_frame, textvariable=self.status_var, 
                               foreground="red", wraplength=350)
        status_label.pack(pady=10)
        
        # Set dialog to close on Escape key
        self.dialog.bind("<Escape>", lambda event: self.on_close())
    
    def on_close(self):
        """Handle dialog close"""
        try:
            # Remove from active dialogs
            dialog_id = self.dialog_id
            if dialog_id in _active_auth_dialogs:
                _active_auth_dialogs.pop(dialog_id, None)
                logger.debug(f"Removed dialog {dialog_id} from active dialogs")
            else:
                logger.warning(f"Dialog {dialog_id} not found in active dialogs")
            
            # Log remaining active dialogs for debugging
            if _active_auth_dialogs:
                logger.warning(f"Still have {len(_active_auth_dialogs)} active dialogs after closing one")
        except Exception as e:
            logger.error(f"Error in on_close: {e}")
            logger.error(traceback.format_exc())
        
        # Call the parent class method to close the dialog
        return super().on_close()
    
    def show_login(self):
        """Show login form"""
        # Clear the form container
        for widget in self.form_container.winfo_children():
            widget.destroy()
            
        # Update button appearance
        self.login_btn.state(['pressed'])
        self.register_btn.state(['!pressed'])
        
        self.subtitle_var.set("Sign in to continue")
        self.current_view = "login"
            
        # Create login form
        ttk.Label(self.form_container, text="Email:").pack(anchor='w', pady=(10, 5))
        self.email_entry = ttk.Entry(self.form_container, width=40)
        self.email_entry.pack(fill='x', pady=5)
        
        ttk.Label(self.form_container, text="Password:").pack(anchor='w', pady=(10, 5))
        self.password_entry = ttk.Entry(self.form_container, width=40, show="*")
        self.password_entry.pack(fill='x', pady=5)
        
        # Add a forgot password link
        forgot_btn = ttk.Button(self.form_container, text="Forgot Password?", 
                               style="Link.TButton", command=self.show_forgot_password)
        forgot_btn.pack(anchor='e', pady=(0, 10))
        
        # Login button
        login_button = ttk.Button(self.form_container, text="Login", 
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
        self.login_btn.state(['!pressed'])
        self.register_btn.state(['pressed'])
        
        self.subtitle_var.set("Create a new account")
        self.current_view = "register"
            
        # Create registration form
        ttk.Label(self.form_container, text="Full Name:").pack(anchor='w', pady=(10, 5))
        self.name_entry = ttk.Entry(self.form_container, width=40)
        self.name_entry.pack(fill='x', pady=5)
        
        ttk.Label(self.form_container, text="Email:").pack(anchor='w', pady=(10, 5))
        self.email_entry = ttk.Entry(self.form_container, width=40)
        self.email_entry.pack(fill='x', pady=5)
        
        ttk.Label(self.form_container, text="Password:").pack(anchor='w', pady=(10, 5))
        self.password_entry = ttk.Entry(self.form_container, width=40, show="*")
        self.password_entry.pack(fill='x', pady=5)
        
        # Register button
        register_button = ttk.Button(self.form_container, text="Create Account", 
                                    width=20, command=self.perform_register)
        register_button.pack(pady=20)
        
        # Set focus to name entry
        self.name_entry.focus_set()
    
    def show_forgot_password(self):
        """Show forgot password form"""
        # Clear the form container
        for widget in self.form_container.winfo_children():
            widget.destroy()
            
        # Update button appearance
        self.login_btn.state(['!pressed'])
        self.register_btn.state(['!pressed'])
        
        self.subtitle_var.set("Reset your password")
        self.current_view = "forgot_password"
        
        # Create forgot password form
        ttk.Label(self.form_container, text="Enter your email address to receive a password reset link:").pack(anchor='w', pady=(10, 5))
        
        self.email_entry = ttk.Entry(self.form_container, width=40)
        self.email_entry.pack(fill='x', pady=5)
        
        # Button frame
        button_frame = ttk.Frame(self.form_container)
        button_frame.pack(fill='x', pady=20)
        
        # Back button
        back_button = ttk.Button(button_frame, text="Back to Login", 
                                command=self.show_login)
        back_button.pack(side='left', padx=5)
        
        # Reset button
        reset_button = ttk.Button(button_frame, text="Send Reset Link", 
                                 command=self.perform_password_reset)
        reset_button.pack(side='right', padx=5)
        
        # Set focus to email entry
        self.email_entry.focus_set()
    
    def perform_login(self):
        """Handle login button click"""
        logger.debug(f"Login attempt with email: {self.email_entry.get().strip()}")
        self.status_var.set("Logging in...")
        self.dialog.update()
        
        email = self.email_entry.get().strip()
        password = self.password_entry.get()
        
        if not email or not password:
            self.status_var.set("Please enter both email and password")
            return
        
        # Perform login in background
        self.run_in_background(
            auth.login,
            email, password,
            callback=self.handle_auth_result,
            error_callback=self.handle_auth_error
        )
    
    def perform_register(self):
        """Handle register button click"""
        logger.debug(f"Register attempt with email: {self.email_entry.get().strip()}")
        self.status_var.set("Creating account...")
        self.dialog.update()
        
        full_name = self.name_entry.get().strip()
        email = self.email_entry.get().strip()
        password = self.password_entry.get()
        
        if not email or not password:
            self.status_var.set("Please enter email and password")
            return
        
        # Perform registration in background
        self.run_in_background(
            auth.register,
            email, password, full_name,
            callback=self.handle_auth_result,
            error_callback=self.handle_auth_error
        )
    
    def perform_password_reset(self):
        """Handle password reset button click"""
        logger.debug(f"Password reset attempt for email: {self.email_entry.get().strip()}")
        self.status_var.set("Sending reset link...")
        self.dialog.update()
        
        email = self.email_entry.get().strip()
        
        if not email:
            self.status_var.set("Please enter your email address")
            return
        
        # Request password reset in background
        self.run_in_background(
            auth.request_password_reset,
            email,
            callback=self.handle_reset_result,
            error_callback=self.handle_auth_error
        )
    
    def handle_auth_result(self, result):
        """Handle authentication result"""
        success, message = result
        logger.debug(f"Authentication result: success={success}, message={message}")
        
        if success:
            self.status_var.set("Success!")
            self.set_result(True)
            
            # Execute success callback if provided
            if self.on_auth_success:
                try:
                    self.on_auth_success()
                except Exception as e:
                    logger.error(f"Error in auth success callback: {e}")
                    logger.error(traceback.format_exc())
            
            # Close the dialog
            self.dialog.after(1000, self.on_close)
        else:
            self.status_var.set(message)
    
    def handle_reset_result(self, result):
        """Handle password reset result"""
        success, message = result
        logger.debug(f"Password reset result: success={success}, message={message}")
        
        if success:
            self.status_var.set(message)
            
            # Show login form after a delay
            self.dialog.after(3000, self.show_login)
        else:
            self.status_var.set(message)
    
    def handle_auth_error(self, error):
        """Handle authentication error"""
        logger.error(f"Authentication error: {str(error)}")
        self.status_var.set(f"Error: {str(error)}")
        
    def show(self):
        """Show the dialog and wait for it to be closed."""
        logger.debug(f"Showing dialog {self.__class__.__name__}")
        
        try:
            # Ensure dialog is visible and on top
            self.dialog.deiconify()
            self.dialog.lift()
            self.dialog.focus_force()
            self.dialog.attributes('-topmost', True)
            self.dialog.update()
            
            # Force dialog to redraw in case it's not appearing
            self.dialog.update_idletasks()
            
            # Schedule additional visibility check
            self.dialog.after(100, self._check_visibility)
            
            # If using modal dialog, wait for it to close
            if self.modal and self.parent.winfo_exists():
                self.parent.wait_window(self.dialog)
            
            logger.debug(f"Dialog {self.__class__.__name__} closed with result: {self.result}")
            return self.result
        except Exception as e:
            logger.error(f"Error showing dialog {self.__class__.__name__}: {e}")
            logger.error(traceback.format_exc())
            return None
        
    def _check_visibility(self):
        """Check if dialog is visible and fix if not."""
        try:
            # Store the retry count in the dialog instance if it doesn't exist
            if not hasattr(self, '_visibility_retries'):
                self._visibility_retries = 0
            
            # Check if the dialog is visible
            if not self.dialog.winfo_viewable():
                self._visibility_retries += 1
                logger.warning(f"Dialog {self.__class__.__name__} not visible, attempt {self._visibility_retries}/3")
                
                # Only try to fix visibility a limited number of times
                if self._visibility_retries <= 3:
                    self.dialog.deiconify()
                    self.dialog.attributes('-topmost', True)
                    self.dialog.focus_force()
                    
                    # Schedule another check
                    self.dialog.after(200, self._check_visibility)
                else:
                    logger.error(f"Failed to make dialog visible after {self._visibility_retries} attempts, giving up")
                    # Consider showing a fallback message box as a last resort
                    try:
                        import tkinter.messagebox as messagebox
                        messagebox.showwarning(
                            "Dialog Issue", 
                            "The login dialog could not be displayed properly. Please try again.",
                            parent=self.parent
                        )
                    except Exception as fallback_error:
                        logger.error(f"Error showing fallback message: {fallback_error}")
            else:
                # Dialog is visible, reset retry count
                self._visibility_retries = 0
        except Exception as e:
            logger.error(f"Error in visibility check: {e}")
            # Don't raise, just log

class PasswordResetDialog(BaseDialog):
    """Dialog for resetting password with a token"""
    
    def __init__(self, parent, token):
        self.token = token
        
        # Initialize the base dialog
        super().__init__(
            parent=parent,
            title="Reset Password",
            size=(350, 250),
            resizable=False,
            modal=True,
            topmost=True,
            centered=True
        )
    
    def _create_ui(self):
        """Create the dialog UI"""
        # Main frame with padding
        self.main_frame = ttk.Frame(self.dialog, padding=20)
        self.main_frame.pack(fill='both', expand=True)
        
        # Instructions
        ttk.Label(self.main_frame, text="Enter your new password:", 
                wraplength=300).pack(pady=(0, 15))
        
        # Password field
        ttk.Label(self.main_frame, text="New Password:").pack(anchor='w')
        self.password_entry = ttk.Entry(self.main_frame, width=40, show="*")
        self.password_entry.pack(fill='x', pady=5)
        
        # Confirm password field
        ttk.Label(self.main_frame, text="Confirm Password:").pack(anchor='w', pady=(10, 0))
        self.confirm_entry = ttk.Entry(self.main_frame, width=40, show="*")
        self.confirm_entry.pack(fill='x', pady=5)
        
        # Status message
        self.status_var = tk.StringVar()
        ttk.Label(self.main_frame, textvariable=self.status_var, 
                foreground="red", wraplength=300).pack(pady=5)
        
        # Buttons
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill='x', pady=(15, 0))
        
        ttk.Button(button_frame, text="Cancel", command=self.on_close).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Reset Password", command=self.reset_password).pack(side='right', padx=5)
        
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
        
        # Reset password in background
        self.run_in_background(
            auth.reset_password,
            self.token, password,
            callback=self.handle_reset_result,
            error_callback=self.handle_reset_error
        )
    
    def handle_reset_result(self, result):
        """Handle reset result"""
        success, message = result
        
        if success:
            self.status_var.set("Password has been reset successfully")
            
            # Show success message and close after delay
            tk.messagebox.showinfo("Success", message, parent=self.dialog)
            self.close(True)
        else:
            self.status_var.set(message)
    
    def handle_reset_error(self, error):
        """Handle reset error"""
        self.status_var.set(f"Error: {str(error)}")
        logger.error(f"Password reset error: {str(error)}")

class PasswordResetRequestDialog(BaseDialog):
    """Dialog for requesting a password reset email"""
    
    def __init__(self, parent):
        # Initialize the base dialog
        super().__init__(
            parent=parent,
            title="Reset Password",
            size=(350, 250),
            resizable=False,
            modal=True,
            topmost=True,
            centered=True
        )
    
    def _create_ui(self):
        """Create the dialog UI"""
        # Main frame with padding
        self.main_frame = ttk.Frame(self.dialog, padding=20)
        self.main_frame.pack(fill='both', expand=True)
        
        # Instructions
        ttk.Label(self.main_frame, text="Enter your email address to receive a password reset link:", 
                wraplength=300).pack(pady=(0, 15))
        
        # Email field
        ttk.Label(self.main_frame, text="Email:").pack(anchor='w')
        self.email_entry = ttk.Entry(self.main_frame, width=40)
        self.email_entry.pack(fill='x', pady=5)
        
        # Status message
        self.status_var = tk.StringVar()
        ttk.Label(self.main_frame, textvariable=self.status_var, 
                foreground="red", wraplength=300).pack(pady=5)
        
        # Buttons
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill='x', pady=(15, 0))
        
        ttk.Button(button_frame, text="Cancel", command=self.on_close).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Send Reset Link", command=self.request_reset).pack(side='right', padx=5)
        
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
        
        # Request password reset in background
        self.run_in_background(
            auth.request_password_reset,
            email,
            callback=self.handle_reset_result,
            error_callback=self.handle_reset_error
        )
    
    def handle_reset_result(self, result):
        """Handle reset result"""
        success, message = result
        
        if success:
            self.status_var.set("Reset link sent successfully")
            
            # Show success message and close after delay
            tk.messagebox.showinfo(
                "Success", 
                "A password reset link has been sent to your email address. Please check your inbox.",
                parent=self.dialog
            )
            self.close(True)
        else:
            self.status_var.set(message)
    
    def handle_reset_error(self, error):
        """Handle reset error"""
        self.status_var.set(f"Error: {str(error)}")
        logger.error(f"Password reset request error: {str(error)}")

# Factory function to create an auth dialog
def create_auth_dialog(parent, title="Authentication Required", on_auth_success=None):
    """
    Create and return an authentication dialog.
    
    Args:
        parent: The parent window
        title: The dialog title
        on_auth_success: Optional callback to execute on successful authentication
        
    Returns:
        AuthDialog: The created dialog or None if a dialog is already active
    """
    # Check if there's already an active auth dialog
    if _active_auth_dialogs:
        logger.info("Auth dialog already active, not creating another one")
        for dialog_id, dialog in _active_auth_dialogs.items():
            # Return the first active dialog
            return dialog
        return None
    
    # Create a new dialog
    return AuthDialog(parent, title, on_auth_success) 