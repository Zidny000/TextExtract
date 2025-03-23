# src/ocr.py
import os
import tempfile
import threading
import sys
import numpy as np
from PIL import Image, ImageEnhance
from mss import mss
from config import DEFAULT_LANGUAGE
from clipboard import copy_to_clipboard

# Try to import pytesseract
try:
    import pytesseract
    from pytesseract import TesseractError, Output
except ImportError:
    # Create a placeholder pytesseract module so the module can be imported
    class pytesseract:
        @staticmethod
        def image_to_string(*args, **kwargs):
            raise ImportError(
                "pytesseract could not be imported. Please install the required packages:\n"
                "pip install pytesseract"
            )
            
        @staticmethod
        def get_tesseract_version():
            return "0.0.0"
    
    class TesseractError(Exception):
        pass
    
    class Output:
        DICT = "dict"

# Check for Tesseract executable path on Windows
if sys.platform.startswith('win'):
    # Look for bundled Tesseract first
    bundled_tesseract_path = os.path.abspath(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
        "bundled_tesseract", "tesseract.exe"
    ))
    
    if os.path.exists(bundled_tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = bundled_tesseract_path
    else:
        # Try to find installed Tesseract
        for path in [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        ]:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break

# Initialize Tesseract - use a lock to prevent concurrent operations
tesseract_lock = threading.Lock()

def get_tesseract_version():
    """Get Tesseract version to verify it's working"""
    try:
        return pytesseract.get_tesseract_version()
    except Exception as e:
        print(f"Error getting Tesseract version: {e}")
        return None

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

def extract_text_from_area(x1, y1, x2, y2):
    """Extract text from the specified screen area using Tesseract OCR."""
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

    temp_file = None
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
        
        # Save the processed image to a temp file
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, "textextract_debug.png")
        img.save(temp_file)
        
        try:
            # Extract text using Tesseract OCR with thread safety
            with tesseract_lock:
                # Map the DEFAULT_LANGUAGE code to Tesseract language format
                # Default to 'eng' if not specified
                lang = 'eng'
                if DEFAULT_LANGUAGE == 'ch':
                    lang = 'chi_sim'
                elif DEFAULT_LANGUAGE == 'ja':
                    lang = 'jpn'
                elif DEFAULT_LANGUAGE == 'ko':
                    lang = 'kor'
                elif DEFAULT_LANGUAGE == 'fr':
                    lang = 'fra'
                elif DEFAULT_LANGUAGE == 'de':
                    lang = 'deu'
                elif DEFAULT_LANGUAGE == 'es':
                    lang = 'spa'
                
                # Configure OCR options
                config = '--psm 6'  # Assume a single block of text
                
                # Run OCR
                text = pytesseract.image_to_string(img, lang=lang, config=config)
                
        except ImportError as e:
            print(f"OCR Error - Tesseract import failed: {e}")
            text = f"ERROR: Tesseract OCR could not be initialized. Please install pytesseract package."
        except TesseractError as e:
            print(f"Tesseract Error: {e}")
            text = f"ERROR: Tesseract OCR failed to process the image."
            
        if text:
            copy_to_clipboard(text)
        return text.strip()
    except Exception as e:
        print(f"OCR Error: {e}")
        return None
    finally:
        # Clean up resources
        if screenshot_taker:
            screenshot_taker.close()