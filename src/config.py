# src/config.py

import json
import os
import sys
from screeninfo import get_monitors

# OCR Configuration
# Default language for OCR (using Tesseract language codes)
# Common codes: eng (English), chi_sim (Simplified Chinese), 
# jpn (Japanese), kor (Korean), fra (French), deu (German), etc.
DEFAULT_LANGUAGE = 'en'  # Maps to 'eng' in Tesseract

CONFIG_FILE = "config.json"

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
        
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_selected_monitor(monitor):
    config = load_config()
    config.update({
        "monitor": {
            "x": monitor.x,
            "y": monitor.y,
            "width": monitor.width,
            "height": monitor.height
        }
    })
    save_config(config)

def load_selected_monitor():
    config = load_config()
    if not config.get("monitor"):
        return None
    
    monitor_config = config["monitor"]
    
    # Find matching monitor from current setup
    for m in get_monitors():
        if (m.x == monitor_config["x"] and 
            m.y == monitor_config["y"] and 
            m.width == monitor_config["width"] and 
            m.height == monitor_config["height"]):
            return m
    return None

# Update OCR settings
def save_ocr_settings(language=DEFAULT_LANGUAGE):
    config = load_config()
    config.update({
        "ocr": {
            "language": language
        }
    })
    save_config(config)
    
    # Update global settings
    global DEFAULT_LANGUAGE
    DEFAULT_LANGUAGE = language

# Load OCR settings
def load_ocr_settings():
    config = load_config()
    if "ocr" in config:
        global DEFAULT_LANGUAGE
        DEFAULT_LANGUAGE = config["ocr"].get("language", DEFAULT_LANGUAGE)

# Load OCR settings on module import
load_ocr_settings()