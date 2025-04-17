# src/ocr.py
import os
import tempfile
import threading
import sys
import base64
from PIL import Image, ImageEnhance
from mss import mss
from config import DEFAULT_LANGUAGE, TOGETHER_API_KEY
from clipboard import copy_to_clipboard
from together import Together

# Initialize Together client - use a lock to prevent multiple initializations
together_lock = threading.Lock()
_together_client = None

def get_together_client():
    """Get or initialize Together client instance using a singleton pattern"""
    global _together_client
    with together_lock:
        if _together_client is None:
            try:
                if not TOGETHER_API_KEY:
                    raise ValueError("Together.ai API key not found. Please set the TOGETHER_API_KEY environment variable or add it to your config file.")
                _together_client = Together(api_key=TOGETHER_API_KEY)
            except Exception as e:
                print(f"Error initializing Together client: {e}")
                raise
    return _together_client

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

def extract_text_from_area(x1, y1, x2, y2):
    """Extract text from the specified screen area using Qwen2-VL model."""
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
        
        # Convert image to base64
        img_base64 = image_to_base64(img)
        
        try:
            # Get Together client
            client = get_together_client()
            
            # Prepare the prompt for text extraction
            prompt = "Extract and return only the exact text visible in this image without any modifications, reformatting, additional explanations, or extra characters. Preserve the text exactly as it appears, including all punctuation, spacing, and formatting. Do not add or enclose the text within any additional symbols such as triple backticks (```) or other formatting markers. Output only the raw text as it appears in the image."
            
            # Create the message with the image
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_base64}"
                            }
                        }
                    ]
                }
            ]
            
            # Call the Together API with Qwen2-VL model
            response = client.chat.completions.create(
                model="meta-llama/Llama-4-Scout-17B-16E-Instruct",
                messages=messages,
                max_tokens=1024,
                temperature=0.1,  # Lower temperature for more focused output
                top_p=0.9
            )
            
            # Extract the text from the response
            text = response.choices[0].message.content.strip()
            
            if text:
                copy_to_clipboard(text)
            return text
            
        except Exception as e:
            print(f"OCR Error - Together API failed: {e}")
            return None
            
    except Exception as e:
        print(f"OCR Error: {e}")
        return None
    finally:
        # Clean up resources
        if screenshot_taker:
            screenshot_taker.close()