# src/ocr.py
import os
import tempfile
import threading
import sys
import base64
import json
import requests
import time
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageEnhance
from mss import mss
from src.config import DEFAULT_LANGUAGE, get_api_url, get_frontend_url
from src.clipboard import copy_to_clipboard
from src.auth import is_authenticated, get_auth_token, refresh_token, get_device_id

# Configuration for the proxy service
# Use the centralized API URL configuration
PROXY_API_URL = f"{get_api_url()}/api/ocr"

# Initialize API client with a lock to prevent multiple initializations
api_lock = threading.Lock()
_api_session = None

def get_api_session():
    """Get or initialize API session instance using a singleton pattern"""
    global _api_session
    with api_lock:
        if _api_session is None:
            try:
                _api_session = requests.Session()
                # Set common headers, etc.
                _api_session.headers.update({
                    "User-Agent": f"TextExtract/{getattr(sys, 'frozen', False) and 'app' or 'dev'}",
                    "X-App-Version": os.getenv("APP_VERSION", "1.0.0")
                })
            except Exception as e:
                print(f"Error initializing API client: {e}")
                raise
    return _api_session

def preprocess_image(image):
    """Preprocess image for better OCR results."""
    # Ensure RGB mode
    image = image.convert("RGB")
    
    # Enhance contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.5)
    
    # Enhance sharpness
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(1.2)
    
    # Enhance brightness slightly
    enhancer = ImageEnhance.Brightness(image)
    image = enhancer.enhance(1.1)
    
    return image

def image_to_base64(image):
    """Convert PIL Image to base64 string."""
    import io
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def show_upgrade_dialog(parent_window, current_count, max_count):
    """Show dialog prompting user to upgrade their subscription"""
    root = tk.Tk() if parent_window is None else tk.Toplevel(parent_window)
    root.withdraw()  # Hide the root window
    
    result = messagebox.askyesno(        "Subscription Limit Reached",
        f"You have used {current_count} of your {max_count} monthly OCR requests.\n\n"
        "Would you like to upgrade your subscription plan for more requests?",
        parent=parent_window if parent_window else root
    )
    
    if result:
        # Open subscription page in browser
        import webbrowser
        webbrowser.open(f"{get_frontend_url()}/subscription")
    
    if parent_window is None:
        root.destroy()
    
    return result

def show_error_dialog(parent_window, error_message):
    """Show error dialog with the provided error message"""
    root = tk.Tk() if parent_window is None else tk.Toplevel(parent_window)
    root.withdraw()  # Hide the root window

    messagebox.showerror(
        "Error",
        f"An error occurred: {error_message}\n\n",
        parent=parent_window if parent_window else root
    )
    
    if parent_window is None:
        root.destroy()
    

def show_device_limit_dialog(parent_window):
    """Show dialog informing user they've reached device limit"""
    root = tk.Tk() if parent_window is None else tk.Toplevel(parent_window)
    root.withdraw()  # Hide the root window
    
    result = messagebox.askyesno(        "Device Limit Reached",
        "You have reached the maximum number of devices allowed on your current plan.\n\n"
        "Would you like to upgrade your subscription for more devices?",
        parent=parent_window if parent_window else root
    )
    
    if result:
        # Open subscription page in browser
        import webbrowser
        webbrowser.open(f"{get_frontend_url()}/subscription")
    
    if parent_window is None:
        root.destroy()
    
    return result

def extract_text_from_area(x1, y1, x2, y2, parent_window=None):
    """Extract text from the specified screen area using the OCR proxy service."""
    # Check for invalid coordinates
    if None in (x1, y1, x2, y2):
        print("Invalid selection coordinates")
        return None

    # Normalize coordinates
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1

    # Check if selection is too small
    if x2 - x1 < 5 or y2 - y1 < 5:
        print("Selection area too small")
        return None

    # Check if user is authenticated
    if not is_authenticated():
        # Show login modal
        from src.ui.dialogs.auth_modal import create_auth_modal
        login_modal = create_auth_modal(parent_window, "Authentication Required")
        is_authenticate = login_modal.show() if login_modal else False
        
        if not is_authenticate:
            print("Authentication required to use OCR features")
            return None

    screenshot_taker = None
    
    try:
        # Capture screenshot
        screenshot_taker = mss()
        region = {
            "left": x1,
            "top": y1,
            "width": x2 - x1,
            "height": y2 - y1
        }
        screenshot = screenshot_taker.grab(region)
        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        
        # Apply preprocessing
        img = preprocess_image(img)
        
        # Convert image to base64
        img_base64 = image_to_base64(img)
        
        try:
            # Get API session
            session = get_api_session()
            
            # Get authentication token
            token = get_auth_token()
            device_id = get_device_id()
            
            # Use the token itself as the CSRF token (common pattern for API auth)
            csrf_token = token
            
            # Prepare headers
            headers = {
                "Authorization": f"Bearer {token}",
                "X-Device-ID": device_id,                "X-App-Version": os.getenv("APP_VERSION", "1.0.0"),
                "Content-Type": "application/json",
                "X-CSRF-TOKEN": csrf_token,
                "Origin": get_frontend_url()  # Add Origin header to satisfy CSRF protection
            }
            
            # Send the image to the backend proxy service
            response = session.post(
                PROXY_API_URL,
                headers=headers,
                json={
                    "image": img_base64,
                    "language": DEFAULT_LANGUAGE
                },
                timeout=30  # Set an appropriate timeout
            )
            
            # Check for errors
            if response.status_code == 401 or response.status_code == 403:
                # Try to parse the error response first
                try:
                    error_data = response.json()
                    error_message = error_data.get('error', '')
                    
                    # Token expired or invalid - try to refresh token
                    refresh_success, refresh_message = refresh_token()
                    
                    if refresh_success:
                        # Try again with new token
                        token = get_auth_token()
                        headers["Authorization"] = f"Bearer {token}"
                        headers["X-CSRF-TOKEN"] = token  # Update CSRF token as well
                        
                        # Retry the request
                        response = session.post(
                            PROXY_API_URL,
                            headers=headers,
                            json={
                                "image": img_base64,
                                "language": DEFAULT_LANGUAGE
                            },
                            timeout=30
                        )
                    else:
                        # Show login modal to get new credentials
                        from src.ui.dialogs.auth_modal import create_auth_modal
                        login_modal = create_auth_modal(parent_window, "Session Expired")
                        is_authenticate = login_modal.show() if login_modal else False
                        
                        if not is_authenticate:
                            print("Authentication required to use OCR features")
                            return None
                        
                        # Try again with new token
                        token = get_auth_token()
                        headers["Authorization"] = f"Bearer {token}"
                        headers["X-CSRF-TOKEN"] = token  # Update CSRF token as well
                        
                        # Retry the request
                        response = session.post(
                            PROXY_API_URL,
                            headers=headers,
                            json={
                                "image": img_base64,
                                "language": DEFAULT_LANGUAGE
                            },
                            timeout=30
                        )
                except:
                    # If we can't parse the error, proceed with normal flow
                    pass
                    
            elif response.status_code == 429:
                # Rate limiting error - subscription limit reached
                try:
                    error_data = response.json()
                    limit = error_data.get('limit', 20)
                    
                    # Show upgrade dialog
                    upgrade_result = show_upgrade_dialog(parent_window, limit, limit)
                    
                    return "ERROR: Daily OCR usage limit reached. Please try again tomorrow or upgrade your plan."
                except:
                    return "ERROR: Daily OCR usage limit reached. Please try again tomorrow or upgrade your plan."
            
            # Check for device limit error
            elif response.status_code == 403 and "device limit" in response.text.lower():
                # Device limit reached
                show_device_limit_dialog(parent_window)
                return "ERROR: Device limit reached. Please use one of your existing devices or upgrade your plan."
            
            # Check if the response is successful
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Extract the text from the response
                    text = data.get("text", "")
                    
                    # Get meta information
                    meta = data.get("meta", {})
                    remaining_requests = meta.get("remaining_requests", 0)
                    
                    # Show warning if nearing the limit (less than 20% remaining)
                    if "meta" in data and remaining_requests <= 2:
                        root = tk.Tk() if parent_window is None else tk.Toplevel(parent_window)
                        root.withdraw()
                        
                        messagebox.showwarning(
                            "Running Low on OCR Requests",
                            f"You have {remaining_requests} OCR requests remaining this month. " +
                            "Consider upgrading your plan for more requests.",
                            parent=parent_window if parent_window else root
                        )
                        
                        if parent_window is None:
                            root.destroy()

                    copy_to_clipboard(text)
                    
                    return text
                except Exception as e:
                    print(f"Error parsing response: {e}")
                    return None
            else:
                try:
                    error_data = response.json()
                    error_message = error_data.get('error', 'Unknown error')
                    show_error_dialog(parent_window, error_message)
                    print(f"API error: {error_message}")
                    return f"ERROR: {error_message}"
                except:
                    print(f"API error: {response.text}")
                    return f"ERROR: API request failed with status code {response.status_code}"
        
        except Exception as e:
            print(f"Error making API request: {e}")
            return None
            
    except Exception as e:
        print(f"Error capturing screenshot: {e}")
        return None
    
    finally:
        # Ensure screenshot taker is cleaned up
        if screenshot_taker:
            screenshot_taker.close()