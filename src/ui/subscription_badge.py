"""
Subscription badge component for the desktop application
Displays current plan and usage information
"""

import tkinter as tk
from tkinter import ttk
import threading
import webbrowser
import requests
import json
import logging
from auth import get_auth_token, get_device_id

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SubscriptionBadge(ttk.Frame):
    """A badge showing subscription information and status"""
    
    def __init__(self, parent, *args, **kwargs):        
        super().__init__(parent, *args, **kwargs)
        
        from src.config import get_api_url
        
        self.parent = parent
        self.api_url = get_api_url()
        
        # Data
        self.plan_data = None
        self.loading = False
        self.error = None
        
        # Create the UI
        self._create_widgets()
        
        # Fetch data
        self._fetch_subscription_data()
    
    def _create_widgets(self):
        """Create the badge UI widgets"""
        # Main frame with border
        self.badge_frame = ttk.Frame(self, padding=(5, 3), relief="groove", borderwidth=1)
        self.badge_frame.pack(fill=tk.BOTH, expand=True)
        
        # Plan label
        self.plan_label = ttk.Label(
            self.badge_frame, 
            text="LOADING...", 
            font=("Helvetica", 9, "bold")
        )
        self.plan_label.pack(side=tk.TOP, anchor="w")
        
        # Usage progress frame
        self.usage_frame = ttk.Frame(self.badge_frame)
        self.usage_frame.pack(side=tk.TOP, fill=tk.X, expand=True, pady=(2, 0))
        
        # Usage labels
        self.usage_label = ttk.Label(
            self.usage_frame,
            text="Requests: --/--",
            font=("Helvetica", 8)
        )
        self.usage_label.pack(side=tk.LEFT)
        
        # Upgrade button
        self.upgrade_button = ttk.Button(
            self.badge_frame,
            text="Upgrade",
            command=self._open_upgrade_page,
            width=8
        )
        self.upgrade_button.pack(side=tk.TOP, anchor="e", pady=(3, 0))
        
        # Bind click event to the whole badge
        self.badge_frame.bind("<Button-1>", lambda e: self._open_upgrade_page())
        self.plan_label.bind("<Button-1>", lambda e: self._open_upgrade_page())
        self.usage_label.bind("<Button-1>", lambda e: self._open_upgrade_page())
    
    def _fetch_subscription_data(self):
        """Fetch subscription data from the API"""
        if self.loading:
            return
            
        self.loading = True
        self.plan_data = None
        self.error = None
        
        # Set UI to loading state
        self.plan_label.config(text="LOADING...")
        self.usage_label.config(text="Requests: --/--")
        
        # Start the API request in a separate thread
        thread = threading.Thread(target=self._fetch_data_thread)
        thread.daemon = True
        thread.start()
    
    def _fetch_data_thread(self):
        """Thread function to fetch data from API"""
        try:
            # Get auth token and device ID
            token = get_auth_token()
            device_id = get_device_id()
            
            if not token or not device_id:
                self.error = "Not logged in"
                self._update_ui_after_fetch()
                return
            
            # Prepare headers
            headers = {
                "Authorization": f"Bearer {token}",
                "X-Device-ID": device_id,
                "Content-Type": "application/json"
            }
            
            # Make API request
            response = requests.get(
                f"{self.api_url}/subscription/user-plan",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.plan_data = response.json()
            else:
                self.error = f"Error: {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        self.error = error_data["error"]
                except:
                    pass
        except Exception as e:
            logger.error(f"Error fetching subscription data: {e}")
            self.error = f"Error: {str(e)}"
        finally:
            self.loading = False
            # Update the UI in the main thread
            self.after(0, self._update_ui_after_fetch)
    
    def _update_ui_after_fetch(self):
        """Update the UI after data is fetched"""
        if self.error:
            self.plan_label.config(text="FREE PLAN")
            self.usage_label.config(text="Requests: Unknown")
            return
        
        if not self.plan_data:
            self.plan_label.config(text="FREE PLAN")
            self.usage_label.config(text="Requests: 0/20")
            return
        
        # Update plan name
        plan_name = self.plan_data.get("plan", {}).get("name", "free").upper()
        self.plan_label.config(text=f"{plan_name} PLAN")
        
        # Update usage info
        usage = self.plan_data.get("usage", {})
        today_requests = usage.get("today_requests", 0)
        max_requests = usage.get("max_requests", 20)
        
        self.usage_label.config(text=f"Requests: {today_requests}/{max_requests}")
        
        # Update button state
        if plan_name == "BASIC":
            self.upgrade_button.config(text="Manage")
        else:
            self.upgrade_button.config(text="Upgrade")
    
    def _open_upgrade_page(self):
        """Open the subscription upgrade page in browser"""
        webbrowser.open(f"{self.api_url.replace('5000', '3000')}/subscription")
    
    def refresh(self):
        """Refresh subscription data"""
        self._fetch_subscription_data()


# Test the component if run directly
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Subscription Badge Test")
    root.geometry("200x100")
    
    badge = SubscriptionBadge(root)
    badge.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    
    root.mainloop() 