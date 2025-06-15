import requests
import threading
import logging
import tkinter as tk
from functools import wraps
import src.auth as auth

logger = logging.getLogger(__name__)

def handle_auth_error(parent_window=None):
    """Shows login modal when authentication fails and returns True if user logged in successfully"""
    # Import here to avoid circular imports
    from src.ui.dialogs.auth_modal import create_auth_modal
    
    # Create a separate window for the login dialog if parent is None
    if parent_window is None:
        temp_window = tk.Tk()
        temp_window.withdraw()  # Hide the window
        login_modal = create_auth_modal(temp_window, "Session Expired")
        result = login_modal.show() if login_modal else False
        temp_window.destroy()
        return result
    else:
        login_modal = create_auth_modal(parent_window, "Session Expired")
        return login_modal.show() if login_modal else False

def authenticated_request(func):
    """
    Decorator for functions that make authenticated API requests.
    Handles token refreshing and reauthentication if token is expired.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Extract parameters from kwargs
        parent_window = kwargs.get('parent_window', None)
        allow_restart = kwargs.pop('allow_restart', False)  # Whether to restart app if all auth attempts fail
        max_retries = 2
        retries = 0
        
        while retries < max_retries:
            try:
                # Try to make the API call
                result = func(*args, **kwargs)
                return result
            except requests.HTTPError as e:
                if hasattr(e.response, 'status_code') and e.response.status_code in (401, 403):
                    # Token expired or invalid - try to refresh token
                    logger.info("Authentication error detected, trying to refresh token")
                    refresh_success, refresh_message = auth.refresh_token()
                    
                    if refresh_success:
                        # Token refreshed, retry the API call
                        logger.info("Token refreshed successfully, retrying request")
                        retries += 1
                    else:
                        # Token refresh failed, try to re-authenticate
                        logger.info(f"Token refresh failed: {refresh_message}, showing login modal")
                        auth_success = handle_auth_error(parent_window)
                        
                        if auth_success:
                            # User successfully logged in, retry the API call
                            logger.info("User re-authenticated, retrying request")
                            retries += 1
                        else:
                            # User canceled login, fail the request
                            logger.warning("User canceled login, authentication failed")
                            
                            # If allowed to restart the app and we've tried the max times
                            if allow_restart and retries == max_retries - 1:
                                logger.warning("Authentication failed multiple times, asking to restart app")
                                if parent_window:
                                    restart = tk.messagebox.askyesno(
                                        "Authentication Failed",
                                        "The application could not authenticate after multiple attempts. "
                                        "Would you like to restart the application?",
                                        parent=parent_window
                                    )
                                    if restart:
                                        logger.info("User chose to restart the application")
                                        # Import here to avoid circular imports
                                        import sys
                                        import os
                                        
                                        # Restart the application
                                        os.execl(sys.executable, sys.executable, *sys.argv)
                            
                            return None
                else:
                    # Other HTTP errors that aren't auth-related
                    logger.error(f"HTTP error: {e}")
                    raise
            except Exception as e:
                # Any other exception
                logger.error(f"Error in authenticated_request: {e}")
                raise
        
        # If we get here, we've exceeded retries
        logger.error("Exceeded maximum authentication retries")
        return None
    
    return wrapper 