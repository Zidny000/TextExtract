"""
Web-based authentication modal for TextExtract.
"""

import tkinter as tk
from tkinter import ttk
import threading
import logging
import traceback
import webbrowser

import src.auth as auth
from src.ui.base_dialog import BaseDialog

# Configure logger
logger = logging.getLogger(__name__)

class AuthModal(BaseDialog):
    """Modal for web-based authentication"""
    
    def __init__(self, parent, title="Authentication Required", on_auth_success=None):
        """
        Initialize the authentication modal.
        
        Args:
            parent: The parent window
            title: The dialog title
            on_auth_success: Optional callback to execute on successful authentication
        """
        self.on_auth_success = on_auth_success
        self.dialog_id = id(self)
        self.auth_in_progress = False
        
        # Check if the parent exists and is valid
        if parent is None or not parent.winfo_exists():
            print("Warning: Invalid parent window provided to AuthModal")
            # Create a dummy root if needed
            parent = tk.Tk()
            parent.withdraw()
        
        # Create the dialog window directly instead of using BaseDialog
        # This gives us more control over the window lifecycle
        self.parent = parent
        self.result = False
        self.dialog = None
        self._create_dialog()
        
    def _create_dialog(self):
        """Create the dialog window"""
        try:
            # Create the dialog window as a Toplevel
            self.dialog = tk.Toplevel(self.parent)
            self.dialog.title("TextExtract Authentication")
            self.dialog.geometry("420x280")
            self.dialog.resizable(False, False)
            
            # Make it modal
            self.dialog.transient(self.parent)
            self.dialog.grab_set()
            
            # Make dialog always on top
            self.dialog.attributes('-topmost', True)
            
            # Center on screen
            self.dialog.update_idletasks()
            width = self.dialog.winfo_width()
            height = self.dialog.winfo_height()
            x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
            self.dialog.geometry(f'{width}x{height}+{x}+{y}')
            
            # Set up close handler
            self.dialog.protocol("WM_DELETE_WINDOW", self.on_close)
            
            # Create the UI
            self._create_ui()
            
            # Focus the dialog
            self.dialog.focus_force()
            
            # Execute deiconify and lift to ensure visibility
            self.dialog.after(100, self._ensure_visibility)
            
        except Exception as e:
            logger.error(f"Error creating auth dialog: {e}")
            logger.error(traceback.format_exc())
            # Try to recover by returning a basic dialog
            if self.dialog is None:
                self.dialog = tk.Toplevel(self.parent)
                self.dialog.title("Error")
                tk.Label(self.dialog, text=f"Error creating dialog: {e}").pack(padx=20, pady=20)
                tk.Button(self.dialog, text="Close", command=self.on_close).pack(pady=10)
    
    def _ensure_visibility(self):
        """Ensure the dialog is visible and stays on top"""
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.deiconify()
            self.dialog.lift()
            self.dialog.focus_force()
            # Schedule another check in case dialog gets buried
            self.dialog.after(500, self._ensure_visibility_if_needed)
    
    def _ensure_visibility_if_needed(self):
        """Only ensure visibility if auth is still in progress"""
        if self.auth_in_progress and self.dialog and self.dialog.winfo_exists():
            self.dialog.lift()
            self.dialog.focus_force()
            # Continue checking periodically
            self.dialog.after(1000, self._ensure_visibility_if_needed)
    
    def on_close(self):
        """Handle dialog close"""
        logger.debug("Auth modal closed by user")
        print("Auth modal is being closed")
        self.dialog.destroy()
    
    def _create_ui(self):
        """Create the dialog UI"""
        # Main frame with padding
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title label with larger font
        title_font = ("Arial", 16, "bold")
        title = ttk.Label(main_frame, text="TextExtract Authentication", font=title_font)
        title.pack(pady=(0, 20))
        
        # Instruction text
        instruction_text = (
            "You need to authenticate to use this feature.\n\n"
            "Click the button below to open a browser window where\n"
            "you can log in to your TextExtract account.\n\n"
            "After successful login, you'll be redirected back to the app."
        )
        instruction = ttk.Label(main_frame, text=instruction_text, justify=tk.CENTER)
        instruction.pack(pady=(0, 20), fill=tk.X)
        
        # Status variable for showing login status
        self.status_var = tk.StringVar()
        status_label = ttk.Label(main_frame, textvariable=self.status_var, foreground="blue")
        status_label.pack(pady=(0, 10))
        
        # Create a standard button - don't use custom styles which can be problematic
        login_button = tk.Button(
            main_frame, 
            text="Open Login Page",
            command=self.start_authentication,
            background="#0078d7",
            foreground="white",
            activebackground="#00569c",
            activeforeground="white",
            font=("Arial", 10, "bold"),
            relief=tk.RAISED,
            borderwidth=1,
            padx=20,
            pady=8,
            cursor="hand2"
        )
        login_button.pack(pady=(5, 10))

        # Create a cancel button
        cancel_button = tk.Button(
            main_frame, 
            text="Cancel",
            command=self.on_close,
            padx=10
        )
        cancel_button.pack(pady=(5, 10))
    
    def start_authentication(self):
        """Start the web-based authentication process"""
        if not self.dialog or not self.dialog.winfo_exists():
            logger.error("Authentication dialog no longer exists")
            return
            
        # First check if already authenticated
        if auth.is_authenticated():
            print("User is already authenticated, closing dialog with success")
            self.status_var.set("Already authenticated!")
            self.set_result(True)
            # Call success callback if provided
            if self.on_auth_success:
                try:
                    self.on_auth_success()
                except Exception as e:
                    print(f"Error in auth success callback: {e}")
                    logger.error(f"Error in auth success callback: {e}")
            # Close the dialog after a short delay
            self.dialog.after(500, self.on_close)
            return
            
        self.auth_in_progress = True
        self.status_var.set("Opening browser for authentication...")
        self.dialog.update_idletasks()
        
        # Disable the button to prevent multiple clicks
        for widget in self.dialog.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, tk.Button) and child['text'] == "Open Login Page":
                    child.config(state=tk.DISABLED, text="Opening browser...")
                    break
        
        # Log for debugging
        print("Authentication button clicked, opening browser...")
        
        # Set up a timeout to prevent hanging forever
        def check_auth_timeout():
            # If auth is still in progress after 2 minutes, force success if user is authenticated or allow retry
            if self.auth_in_progress and self.dialog and self.dialog.winfo_exists():
                print("Authentication timeout check - checking if user is authenticated")
                if auth.is_authenticated():
                    print("Timeout check: User is now authenticated, completing dialog")
                    self.dialog.after(0, lambda: self.handle_auth_success("Timeout - but user is authenticated"))
                else:
                    print("Timeout check: User still not authenticated, enabling retry")
                    self.status_var.set("Taking too long. Please try again.")
                    # Re-enable the button
                    for widget in self.dialog.winfo_children():
                        for child in widget.winfo_children():
                            if isinstance(child, tk.Button) and child['text'] == "Opening browser...":
                                child.config(state=tk.NORMAL, text="Open Login Page")
                                break
                    self.auth_in_progress = False

        # Schedule the timeout check
        auth_timeout_id = self.dialog.after(120000, check_auth_timeout)  # 2 minutes
        
        # Create callback for web authentication
        def auth_success_callback():
            print("Auth success callback received in AuthModal")
            # Cancel the timeout check
            self.dialog.after_cancel(auth_timeout_id)
            # Ensure dialog closes on success
            if self.dialog and self.dialog.winfo_exists():
                self.dialog.after(0, lambda: self.handle_auth_success("Authentication successful"))
        
        # Perform authentication in background to avoid freezing UI
        def auth_thread():
            try:
                # Start the web authentication flow with our close-on-success callback
                success, message = auth.web_authenticate(auth_success_callback)
                
                # Cancel the timeout check since we got a response
                try:
                    self.dialog.after_cancel(auth_timeout_id)
                except Exception:
                    pass
                
                # Make sure dialog exists before updating UI
                if self.dialog and self.dialog.winfo_exists():
                    # Check again if user is authenticated (in case web_authenticate didn't catch it)
                    if success or auth.is_authenticated():
                        print("Auth thread: Authentication is successful or user is authenticated")
                        self.dialog.after(0, lambda: self.handle_auth_success(message or "User is authenticated"))
                    else:
                        print(f"Authentication failed: {message}")
                        self.dialog.after(0, lambda: self.handle_auth_failure(message))
                else:
                    print("Dialog was closed during authentication process")
                    
            except Exception as e:
                print(f"Error in authentication thread: {e}")
                logger.error(f"Error in authentication thread: {e}")
                logger.error(traceback.format_exc())
                
                # Make sure dialog exists before updating UI
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.after(0, lambda: self.status_var.set(f"Error: {str(e)}"))
                    
                    # Re-enable the button on error
                    def reenable_button():
                        if self.dialog and self.dialog.winfo_exists():
                            for widget in self.dialog.winfo_children():
                                for child in widget.winfo_children():
                                    if isinstance(child, tk.Button) and child['text'] == "Opening browser...":
                                        child.config(state=tk.NORMAL, text="Open Login Page")
                                        break
                    self.dialog.after(0, reenable_button)
            finally:
                self.auth_in_progress = False
                
                # Schedule periodic checks to see if user is authenticated despite no callback
                def check_auth_status():
                    if not self.dialog or not self.dialog.winfo_exists():
                        return
                    
                    if auth.is_authenticated():
                        print("Periodic check: User is now authenticated, closing dialog")
                        self.dialog.after(0, lambda: self.handle_auth_success("User is now authenticated"))
                        return
                    
                    # If dialog is still open and we're still in auth_thread's finally block, schedule another check
                    if self.dialog and self.dialog.winfo_exists() and self.auth_in_progress:
                        self.dialog.after(2000, check_auth_status)  # Check every 2 seconds
                
                # Start periodic checks after a short delay
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.after(3000, check_auth_status)
        
        # Use a small delay before starting the thread to allow UI to update
        self.dialog.after(100, lambda: threading.Thread(target=auth_thread, daemon=True).start())
    
    def handle_auth_success(self, message):
        """Handle successful authentication"""
        print(f"Handling auth success with message: {message}")
        if not self.dialog or not self.dialog.winfo_exists():
            print("Dialog does not exist, can't update UI for success")
            return
            
        # Force dialog to be visible and active
        try:
            self.dialog.deiconify()
            self.dialog.lift()
            self.dialog.focus_force()
            self.dialog.update()
        except Exception as e:
            print(f"Error ensuring dialog visibility: {e}")
            
        self.status_var.set("Authentication successful!")
        self.set_result(True)
        self.auth_in_progress = False
        
        # Call the success callback if provided
        if self.on_auth_success:
            try:
                print("Calling provided on_auth_success callback")
                self.on_auth_success()
            except Exception as e:
                print(f"Error in auth success callback: {e}")
                logger.error(f"Error in auth success callback: {e}")
        
        # Close the dialog immediately
        print("Forcefully closing dialog now")
        try:
            self.dialog.destroy()
        except Exception as e:
            print(f"Error destroying dialog: {e}")
            logger.error(f"Error destroying dialog: {e}")
            # Try one more time with a delay
            self.dialog.after(100, self.on_close)
    
    def handle_auth_failure(self, message):
        """Handle authentication failure"""
        self.status_var.set(f"Authentication failed: {message}")
        self.set_result(False)
    
    def show(self):
        """Show the dialog and wait for it to be closed."""
        logger.debug(f"Showing auth modal dialog")
        
        try:
            if not self.dialog or not self.dialog.winfo_exists():
                logger.error("Dialog doesn't exist or isn't valid")
                return False

            # Check if already authenticated before even showing the dialog
            if auth.is_authenticated():
                print("User is already authenticated, completing with success without showing dialog")
                self.set_result(True)
                # Call success callback if provided
                if self.on_auth_success:
                    try:
                        self.on_auth_success()
                    except Exception as e:
                        print(f"Error in auth success callback: {e}")
                        logger.error(f"Error in auth success callback: {e}")
                # Don't show the dialog at all
                self.dialog.destroy()
                return True
                
            # Ensure dialog is visible and on top
            self._ensure_visibility()
            
            # If the parent exists, wait for dialog to close
            if self.parent and self.parent.winfo_exists():
                self.parent.wait_window(self.dialog)
            
            logger.debug(f"Auth modal dialog closed with result: {self.result}")
            return self.result
        except Exception as e:
            logger.error(f"Error showing auth modal dialog: {e}")
            logger.error(traceback.format_exc())
            return False

    def set_result(self, result):
        """Set the dialog result"""
        print(f"Setting auth result to: {result}")
        self.result = result

def create_auth_modal(parent, title="Authentication Required", on_auth_success=None):
    """Create and return an authentication modal"""
    try:
        print(f"Creating auth modal with parent: {parent}")
        # Ensure parent is specified and valid
        if parent is None or not hasattr(parent, 'winfo_exists') or not parent.winfo_exists():
            print("Warning: Invalid parent window provided. Creating dummy root.")
            dummy_root = tk.Tk()
            dummy_root.withdraw()
            parent = dummy_root
        
        dialog = AuthModal(parent, title, on_auth_success)
        print(f"Auth modal created: {dialog.dialog}")
        return dialog
    except Exception as e:
        logger.error(f"Error creating auth modal: {e}")
        logger.error(traceback.format_exc())
        print(f"Failed to create auth modal: {e}")
        return None 