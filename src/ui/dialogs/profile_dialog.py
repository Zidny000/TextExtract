"""
User Profile Dialog for displaying and editing user information.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import logging
import threading
import traceback
from typing import Optional, Dict, Any, Callable
from datetime import datetime

from src.ui.base_dialog import BaseDialog
import src.auth as auth
from src.utils.threading.thread_manager import run_on_main_thread

# Configure logger
logger = logging.getLogger(__name__)

class UserProfileDialog(BaseDialog):
    """Enhanced user profile dialog with account management options"""
    
    def __init__(self, parent, profile_data, on_profile_update=None, on_logout=None):
        """
        Initialize the user profile dialog.
        
        Args:
            parent: The parent window
            profile_data: The user profile data
            on_profile_update: Optional callback to execute when profile is updated
            on_logout: Optional callback to execute when user logs out
        """
        self.profile_data = profile_data
        self.user = profile_data["user"]
        self.usage = profile_data["usage"]
        self.on_profile_update = on_profile_update
        self.on_logout = on_logout
        
        # Initialize the base dialog
        super().__init__(
            parent=parent,
            title="User Profile",
            size=(500, 500),
            resizable=False,
            modal=False,  # Changed to non-modal to prevent application freeze
            topmost=True,
            centered=True
        )
        
        # Make sure dialog is visible after initialization
        if hasattr(self, 'dialog') and self.dialog:
            self.dialog.attributes('-topmost', True)
            self.dialog.update()
            self.dialog.lift()
            self.dialog.focus_force()
            # After a short delay, allow other windows to go on top
            self.dialog.after(1000, lambda: self.dialog.attributes('-topmost', False))
    
    def _create_ui(self):
        """Create the dialog UI"""
        # Main frame with padding
        self.main_frame = ttk.Frame(self.dialog, padding=20)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # User info section
        ttk.Label(self.main_frame, text="User Profile", font=("Arial", 16, "bold")).pack(pady=(0, 15))
        
        # Create a notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(10, 15))
        
        # Profile tab
        profile_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(profile_frame, text="Profile")
        
        # Usage tab
        usage_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(usage_frame, text="Usage")
        
        # Account tab
        account_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(account_frame, text="Account")
        
        # Build Profile tab
        self._build_profile_tab(profile_frame)
        
        # Build Usage tab
        self._build_usage_tab(usage_frame)
        
        # Build Account tab
        self._build_account_tab(account_frame)
        
        # Button frame at the bottom
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill=tk.X, pady=(15, 0))
        
        # Logout button
        logout_btn = ttk.Button(button_frame, text="Logout", command=self._confirm_logout)
        logout_btn.pack(side=tk.LEFT, padx=5)
        
        # Close button
        close_btn = ttk.Button(button_frame, text="Close", command=self.on_close)
        close_btn.pack(side=tk.RIGHT, padx=5)
    
    def _build_profile_tab(self, parent):
        """Build the Profile tab"""
        # Email
        ttk.Label(parent, text="Email:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        ttk.Label(parent, text=self.user.get("email", "Unknown")).grid(row=0, column=1, sticky=tk.W, pady=5, columnspan=2)
        
        # Email verification status
        is_verified = self.user.get("email_verified", False)
        status_text = "Verified" if is_verified else "Not Verified"
        status_color = "green" if is_verified else "red"
        
        ttk.Label(parent, text="Status:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        
        status_label = ttk.Label(parent, text=status_text, foreground=status_color)
        status_label.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Verification button if not verified
        if not is_verified:
            verify_btn = ttk.Button(parent, text="Verify Email", command=self._request_verification)
            verify_btn.grid(row=1, column=2, padx=5)
        
        # Full name
        ttk.Label(parent, text="Name:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=5, padx=5)
        self.name_var = tk.StringVar(value=self.user.get("full_name", ""))
        name_entry = ttk.Entry(parent, textvariable=self.name_var, width=30)
        name_entry.grid(row=2, column=1, sticky=tk.W, pady=5, columnspan=2)
        
        # Plan
        ttk.Label(parent, text="Plan:", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky=tk.W, pady=5, padx=5)
        plan_text = self.user.get("plan_type", "Free").capitalize()
        ttk.Label(parent, text=plan_text).grid(row=3, column=1, sticky=tk.W, pady=5, columnspan=2)
        
        # Member since
        ttk.Label(parent, text="Member Since:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky=tk.W, pady=5, padx=5)
        created_date = self.user.get("created_at", "Unknown")
        # Format date if it's a string
        if isinstance(created_date, str) and 'T' in created_date:
            try:
                date_obj = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                created_date = date_obj.strftime("%B %d, %Y")
            except:
                pass
        ttk.Label(parent, text=created_date).grid(row=4, column=1, sticky=tk.W, pady=5, columnspan=2)
        
        # Separator
        ttk.Separator(parent, orient=tk.HORIZONTAL).grid(row=5, column=0, columnspan=3, sticky=tk.EW, pady=10)
        
        # Save button
        save_btn = ttk.Button(parent, text="Save Changes", command=self._save_profile)
        save_btn.grid(row=6, column=1, sticky=tk.W, pady=15)
        
        # Status message
        self.profile_status_var = tk.StringVar()
        ttk.Label(parent, textvariable=self.profile_status_var, foreground="red").grid(row=7, column=0, columnspan=3, pady=5)
        
    def _build_usage_tab(self, parent):
        """Build the Usage tab"""
        # Today's usage
        ttk.Label(parent, text="Today's Usage:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=10, padx=5)
        ttk.Label(parent, text=f"{self.usage.get('today_requests', 0)} requests used").grid(row=0, column=1, sticky=tk.W, pady=10)
        
        # Remaining requests
        ttk.Label(parent, text="Remaining Requests:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky=tk.W, pady=10, padx=5)
        ttk.Label(parent, text=f"{self.usage.get('remaining_requests', 0)} of {self.usage.get('plan_limit', 0)}").grid(row=1, column=1, sticky=tk.W, pady=10)
        
        # Progress bar for usage
        ttk.Label(parent, text="Usage Progress:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=10, padx=5)
        
        try:
            used = int(self.usage.get('today_requests', 0))
            total = int(self.usage.get('plan_limit', 100))
            progress = min(used / total * 100 if total > 0 else 0, 100)
        except (ValueError, ZeroDivisionError):
            progress = 0
            
        progress_bar = ttk.Progressbar(parent, orient=tk.HORIZONTAL, length=200, mode="determinate")
        progress_bar["value"] = progress
        progress_bar.grid(row=2, column=1, sticky=tk.W, pady=10)
        
        # Separator
        ttk.Separator(parent, orient=tk.HORIZONTAL).grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=10)
        
        # Devices section
        ttk.Label(parent, text="Registered Devices:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky=tk.W, pady=(20,10), padx=5, columnspan=2)
        
        # Devices list (in a frame with scrollbar if needed)
        devices_frame = ttk.Frame(parent)
        devices_frame.grid(row=5, column=0, columnspan=2, sticky=tk.EW, padx=5)
        
        devices = self.profile_data.get("devices", [])
        if devices:
            for i, device in enumerate(devices[:5]):  # Show max 5 devices
                device_name = device.get("device_name", "Unknown Device")
                device_type = device.get("device_type", "")
                if device_type:
                    device_name = f"{device_name} ({device_type})"
                    
                ttk.Label(devices_frame, text=device_name).grid(row=i, column=0, sticky=tk.W, pady=2)
                last_active = device.get("last_active", "")
                if last_active and isinstance(last_active, str) and 'T' in last_active:
                    try:
                        date_obj = datetime.fromisoformat(last_active.replace('Z', '+00:00'))
                        last_active = date_obj.strftime("%b %d, %Y")
                    except:
                        pass
                ttk.Label(devices_frame, text=f"Last active: {last_active}", foreground="gray").grid(row=i, column=1, sticky=tk.W, pady=2, padx=10)
        else:
            ttk.Label(devices_frame, text="No devices registered", foreground="gray").grid(row=0, column=0, sticky=tk.W, pady=5)
            
    def _build_account_tab(self, parent):
        """Build the Account tab"""
        # Change password section
        ttk.Label(parent, text="Change Password", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(10,15), padx=5, columnspan=2)
        
        change_pwd_btn = ttk.Button(parent, text="Change Password", width=20, command=self._show_change_password)
        change_pwd_btn.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        # Separator
        ttk.Separator(parent, orient=tk.HORIZONTAL).grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=20)
        
        # Account management section
        ttk.Label(parent, text="Account Management", font=("Arial", 12, "bold")).grid(row=3, column=0, sticky=tk.W, pady=(10,15), padx=5, columnspan=2)
        
        delete_btn = ttk.Button(parent, text="Delete Account", width=20, style="Accent.TButton", command=self._confirm_delete_account)
        delete_btn.grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        
        # Warning label
        ttk.Label(parent, text="Warning: Account deletion is permanent and cannot be undone.", 
                foreground="red", wraplength=350).grid(row=5, column=0, sticky=tk.W, padx=5, pady=10, columnspan=2)
                
    def _save_profile(self):
        """Save profile changes"""
        self.profile_status_var.set("Saving changes...")
        self.dialog.update()
        
        new_name = self.name_var.get().strip()
        
        # Update user profile in a separate thread
        def update_profile():
            token = auth.get_auth_token()
            device_id = auth.get_device_id()
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "X-Device-ID": device_id,
                "X-App-Version": "1.0.0"  # TODO: Get from app config
            }
            
            payload = {
                "full_name": new_name
            }
            
            import requests
            response = requests.put(
                f"{auth.API_BASE_URL}/users/profile", 
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                # Success!
                updated_user = response.json()
                return True, updated_user
            else:
                error_msg = "Failed to update profile"
                try:
                    error_details = response.json()
                    if "error" in error_details:
                        error_msg = error_details["error"]
                except:
                    pass
                return False, error_msg
                
        # Handle profile update result
        def handle_result(result):
            success, data = result
            
            if success:
                # Update local data
                self.user["full_name"] = new_name
                self.profile_status_var.set("Profile updated successfully")
                
                # Call the callback if provided
                if self.on_profile_update:
                    try:
                        self.on_profile_update(data)
                    except Exception as e:
                        logger.error(f"Error in profile update callback: {e}")
            else:
                self.profile_status_var.set(data)
                
        # Handle error
        def handle_error(error):
            logger.error(f"Error updating profile: {error}")
            self.profile_status_var.set(f"Error: {str(error)}")
        
        # Run the update in the background
        self.run_in_background(
            update_profile,
            callback=handle_result,
            error_callback=handle_error
        )
        
    def _request_verification(self):
        """Request email verification"""
        
        # Show progress
        self.profile_status_var.set("Sending verification email...")
        self.dialog.update()
        
        # Run verification request in background
        self.run_in_background(
            auth.request_email_verification,
            callback=self._handle_verification_result,
            error_callback=lambda e: self.profile_status_var.set(f"Error: {str(e)}")
        )
    
    def _handle_verification_result(self, result):
        """Handle verification result"""
        success, message = result
        
        if success:
            self.profile_status_var.set("Verification email sent. Please check your inbox.")
            messagebox.showinfo(
                "Verification Email Sent", 
                "A verification email has been sent to your email address. "
                "Please check your inbox and follow the instructions to verify your account.",
                parent=self.dialog
            )
        else:
            self.profile_status_var.set(f"Error: {message}")
        
    def _show_change_password(self):
        """Show change password dialog"""
        from src.ui.dialogs.auth_dialog import PasswordResetRequestDialog
        reset_dialog = PasswordResetRequestDialog(self.dialog)
        reset_dialog.email_entry.insert(0, self.user.get("email", ""))
        reset_dialog.email_entry.configure(state="disabled")  # Don't allow changing email
        reset_dialog.show()
        
    def _confirm_logout(self):
        """Confirm and perform logout"""
        if messagebox.askyesno(
            "Confirm Logout", 
            "Are you sure you want to logout?",
            parent=self.dialog
        ):
            # Close the dialog first
            self.dialog.destroy()
            
            # Execute logout callback if provided
            if self.on_logout:
                try:
                    self.on_logout()
                except Exception as e:
                    logger.error(f"Error in logout callback: {e}")
            else:
                # Default logout behavior
                success, _ = auth.logout()
                if success:
                    messagebox.showinfo("Logout", "You have been logged out successfully")
                else:
                    messagebox.showerror("Error", "Failed to logout")
        
    def _confirm_delete_account(self):
        """Confirm account deletion"""
        if messagebox.askyesno(
            "Confirm Deletion", 
            "Are you sure you want to delete your account? This action cannot be undone and all your data will be permanently deleted.",
            icon="warning",
            parent=self.dialog
        ):
            # Ask for password confirmation
            password = simpledialog.askstring(
                "Password Required", 
                "Please enter your password to confirm account deletion:",
                show='*',
                parent=self.dialog
            )
            
            if password:
                # Show progress
                self.profile_status_var.set("Deleting account...")
                self.dialog.update()
                
                # Delete account in background
                self.run_in_background(
                    auth.delete_account,
                    password,
                    callback=self._handle_delete_result,
                    error_callback=lambda e: self.profile_status_var.set(f"Error: {str(e)}")
                )
    
    def _handle_delete_result(self, result):
        """Handle account deletion result"""
        success, message = result
        
        if success:
            # Close the dialog
            self.dialog.destroy()
            
            # Show success message
            messagebox.showinfo(
                "Account Deleted", 
                "Your account has been successfully deleted."
            )
            
            # Execute logout callback if provided
            if self.on_logout:
                try:
                    self.on_logout()
                except Exception as e:
                    logger.error(f"Error in logout callback: {e}")
        else:
            self.profile_status_var.set(f"Error: {message}")

# Factory function to create a user profile dialog
def create_user_profile_dialog(parent, profile_data, on_profile_update=None, on_logout=None):
    """
    Create and return a user profile dialog.
    
    Args:
        parent: The parent window
        profile_data: The user profile data
        on_profile_update: Optional callback to execute when profile is updated
        on_logout: Optional callback to execute when user logs out
        
    Returns:
        UserProfileDialog: The created dialog
    """
    return UserProfileDialog(parent, profile_data, on_profile_update, on_logout) 