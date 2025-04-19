# src/ocr.py
import os
import tempfile
import threading
import sys
import base64
from PIL import Image, ImageEnhance
from mss import mss
from config import DEFAULT_LANGUAGE
from clipboard import copy_to_clipboard
from google.cloud import vision

# Initialize Google Vision client - use a lock to prevent multiple initializations
vision_lock = threading.Lock()
_vision_client = None

def get_vision_client():
    """Get or initialize Google Vision client instance using a singleton pattern"""
    global _vision_client
    with vision_lock:
        if _vision_client is None:
            try:
                _vision_client = vision.ImageAnnotatorClient()
            except Exception as e:
                print(f"Error initializing Google Vision client: {e}")
                print("Make sure you have set GOOGLE_APPLICATION_CREDENTIALS environment variable "
                      "pointing to your Google Cloud service account key JSON file.")
                raise
    return _vision_client

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

def image_to_bytes(image):
    """Convert PIL Image to bytes."""
    import io
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return buffered.getvalue()

def extract_text_from_area(x1, y1, x2, y2):
    """Extract text from the specified screen area using Google Vision API."""
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
        
        # Convert image to bytes
        img_bytes = image_to_bytes(img)
        
        try:
            # Get Vision client
            client = get_vision_client()
            
            # Create image object
            image = vision.Image(content=img_bytes)
            
            # Perform text detection
            response = client.text_detection(image=image)
            
            # Handle potential errors
            if response.error.message:
                print(f"Google Vision API Error: {response.error.message}")
                return None
                
            # Extract the text from the response
            # Get full text annotation which preserves formatting better
            texts = response.text_annotations
            
            if texts:
                # The first annotation contains the entire text
                text = texts[0].description
                
                if text:
                    copy_to_clipboard(text)
                return text
            else:
                print("No text detected in the image")
                return None
            
        except Exception as e:
            print(f"OCR Error - Google Vision API failed: {e}")
            return None
            
    except Exception as e:
        print(f"OCR Error: {e}")
        return None
    finally:
        # Clean up resources
        if screenshot_taker:
            screenshot_taker.close()