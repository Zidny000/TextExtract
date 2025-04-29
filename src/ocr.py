# src/ocr.py
import os
import tempfile
import threading
import sys
import base64
import json
import requests
import time
from PIL import Image, ImageEnhance
from mss import mss
from config import DEFAULT_LANGUAGE
from clipboard import copy_to_clipboard
import auth  # Import our auth module

# Configuration for the proxy service
# For local development, use localhost
PROXY_API_URL = "http://localhost:5000/api/ocr"

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
    if not auth.is_authenticated():
        # Show login modal
        from src.ui.dialogs.auth_modal import create_auth_modal
        login_modal = create_auth_modal(parent_window, "Authentication Required")
        is_authenticated = login_modal.show() if login_modal else False
        
        if not is_authenticated:
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
            token = auth.get_auth_token()
            device_id = auth.get_device_id()
            
            # Prepare headers
            headers = {
                "Authorization": f"Bearer {token}",
                "X-Device-ID": device_id,
                "X-App-Version": os.getenv("APP_VERSION", "1.0.0"),
                "Content-Type": "application/json"
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
                # Token expired or invalid - try to refresh token
                refresh_success, _ = auth.refresh_token()
                
                if refresh_success:
                    # Try again with new token
                    token = auth.get_auth_token()
                    headers["Authorization"] = f"Bearer {token}"
                    
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
                    is_authenticated = login_modal.show() if login_modal else False
                    
                    if not is_authenticated:
                        print("Authentication required to use OCR features")
                        return None
                    
                    # Try again with new token
                    token = auth.get_auth_token()
                    headers["Authorization"] = f"Bearer {token}"
                    
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
            
            # Check if we still have errors
            response.raise_for_status()
            
            # Parse the response
            result = response.json()
            
            # Extract the text from the response
            text = result.get('text', '')
            
            if text:
                copy_to_clipboard(text)
                
            # Log usage info if available
            if "meta" in result and "remaining_requests" in result["meta"]:
                print(f"Remaining requests today: {result['meta']['remaining_requests']}")
                
            return text
            
        except requests.RequestException as e:
            print(f"OCR Error - API request failed: {e}")
            return None
            
    except Exception as e:
        print(f"OCR Error: {e}")
        return None
    finally:
        # Clean up resources
        if screenshot_taker:
            screenshot_taker.close()