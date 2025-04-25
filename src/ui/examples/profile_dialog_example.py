"""
Example showing how to use the UserProfileDialog.

Run this file directly to see the dialog in action:
python -m src.ui.examples.profile_dialog_example
"""

import tkinter as tk
from tkinter import ttk
import logging
import json
import os
import sys

# Add the project root to the path to make imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Import the user profile dialog
from src.ui.dialogs.profile_dialog import create_user_profile_dialog

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProfileDialogExample:
    """Example application to demonstrate UserProfileDialog"""
    
    def __init__(self):
        # Create main window
        self.root = tk.Tk()
        self.root.title("Profile Dialog Example")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        
        # Center the window
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
        # Create main frame
        self.main_frame = ttk.Frame(self.root, padding=20)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a button to open the profile dialog
        ttk.Label(
            self.main_frame, 
            text="User Profile Dialog Example", 
            font=("Arial", 16, "bold")
        ).pack(pady=(0, 20))
        
        ttk.Label(
            self.main_frame,
            text="Click the button below to open the user profile dialog with mock data.",
            wraplength=350
        ).pack(pady=(0, 30))
        
        # Create button to open dialog
        ttk.Button(
            self.main_frame,
            text="Open Profile Dialog",
            width=20,
            command=self.show_profile_dialog
        ).pack(pady=10)
        
        # Status label
        self.status_var = tk.StringVar()
        ttk.Label(
            self.main_frame,
            textvariable=self.status_var,
            foreground="blue"
        ).pack(pady=(30, 0))
        
    def show_profile_dialog(self):
        """Show the user profile dialog with mock data"""
        # Create mock profile data
        profile_data = self._get_mock_profile_data()
        
        # Create the dialog
        dialog = create_user_profile_dialog(
            self.root,
            profile_data,
            on_profile_update=self._handle_profile_update,
            on_logout=self._handle_logout
        )
        
        # Show the dialog
        dialog.show()
    
    def _get_mock_profile_data(self):
        """Create mock profile data for demonstration"""
        return {
            "user": {
                "id": "usr_123456789",
                "email": "user@example.com",
                "email_verified": True,
                "full_name": "John Doe",
                "plan_type": "premium",
                "created_at": "2023-05-15T10:30:45Z"
            },
            "usage": {
                "today_requests": 45,
                "remaining_requests": 955,
                "plan_limit": 1000
            },
            "devices": [
                {
                    "device_id": "dev_123",
                    "device_name": "My Windows PC",
                    "device_type": "Windows",
                    "last_active": "2023-10-20T14:25:33Z"
                },
                {
                    "device_id": "dev_456",
                    "device_name": "Work Laptop",
                    "device_type": "MacOS",
                    "last_active": "2023-10-18T09:12:05Z"
                }
            ]
        }
    
    def _handle_profile_update(self, updated_profile):
        """Handle profile update callback"""
        logger.info(f"Profile updated: {json.dumps(updated_profile, indent=2)}")
        self.status_var.set("Profile updated successfully!")
    
    def _handle_logout(self):
        """Handle logout callback"""
        logger.info("User logged out")
        self.status_var.set("User logged out successfully!")
    
    def run(self):
        """Run the example application"""
        self.root.mainloop()

if __name__ == "__main__":
    # Create and run the example
    app = ProfileDialogExample()
    app.run() 