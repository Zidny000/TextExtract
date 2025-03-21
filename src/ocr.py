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

# Try to import PaddleOCR
try:
    from paddleocr import PaddleOCR
except ImportError:
    # Create a placeholder PaddleOCR class so the module can be imported
    class PaddleOCR:
        def __init__(self, **kwargs):
            raise ImportError(
                "PaddleOCR could not be imported. Please install the required packages:\n"
                "pip install paddlepaddle==2.6.2 paddleocr==2.10.0"
            )
        
        def ocr(self, *args, **kwargs):
            raise ImportError(
                "PaddleOCR could not be imported. Please install the required packages:\n"
                "pip install paddlepaddle==2.6.2 paddleocr==2.10.0"
            )

# Initialize PaddleOCR - use a lock to prevent multiple initializations
paddle_lock = threading.Lock()
_paddle_ocr = None

def get_paddle_ocr():
    """Get or initialize PaddleOCR instance using a singleton pattern"""
    global _paddle_ocr
    with paddle_lock:
        if _paddle_ocr is None:
            try:
                # Initialize PaddleOCR with the appropriate language
                # For PaddleOCR 2.10.0, we use specific parameters for best compatibility
                _paddle_ocr = PaddleOCR(
                    use_angle_cls=True, 
                    lang=DEFAULT_LANGUAGE,
                    show_log=False,
                    use_gpu=False  # Set to True if you have a GPU with CUDA
                )
            except ImportError as e:
                print(f"Error initializing PaddleOCR: {e}")
                print(f"Please ensure both paddle and paddleocr packages are installed.")
                print(f"Required versions: paddlepaddle==2.6.2 paddleocr==2.10.0")
                raise
            except Exception as e:
                print(f"Unexpected error initializing PaddleOCR: {e}")
                raise
    
    return _paddle_ocr

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
    """Extract text from the specified screen area using PaddleOCR."""
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
            # Extract text using PaddleOCR
            ocr = get_paddle_ocr()
            
            # Run OCR
            result = ocr.ocr(temp_file, cls=True)
            
            # Process the OCR results
            text = ""
            if result and len(result) > 0:
                # Handle PaddleOCR 2.10.0 result structure
                if isinstance(result[0], list):
                    # New structure in PaddleOCR 2.10.0
                    lines = []
                    for line in result[0]:
                        if len(line) >= 2:  # Ensure it contains text
                            lines.append(line[1][0])  # Extract text content
                    text = "\n".join(lines)
                else:
                    # Older structure fallback
                    lines = []
                    for line in result:
                        for word_info in line:
                            if len(word_info) >= 2:
                                lines.append(word_info[1][0])
                    text = "\n".join(lines)
                    
        except ImportError as e:
            print(f"OCR Error - PaddleOCR import failed: {e}")
            text = f"ERROR: PaddleOCR could not be initialized. Please install required packages."
            print(f"Required versions: paddlepaddle==2.6.2 paddleocr==2.10.0")
            
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