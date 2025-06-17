# src/config.py

import json
import os
import sys
from screeninfo import get_monitors

# OCR Configuration
# Default language for OCR 
DEFAULT_LANGUAGE = 'en'  # English

# Together.ai API key for Qwen2-VL
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY", "")

# API Configuration
# Set to True to use production API, False to use local development API
USE_PRODUCTION_API = os.getenv("USE_PRODUCTION_API", "False").lower() == "true"

# API URLs
DEV_API_URL = "http://localhost:5000"
PROD_API_URL = "https://textextract.onrender.com"

# Frontend URLs
DEV_FRONTEND_URL = "http://localhost:3000"
PROD_FRONTEND_URL = "https://textextract1.onrender.com"  # Update this if your frontend URL is different

# Get the appropriate API URL based on environment
def get_api_url():
    print(USE_PRODUCTION_API)
    return PROD_API_URL if USE_PRODUCTION_API else DEV_API_URL

# Get the appropriate frontend URL based on environment
def get_frontend_url():
    return PROD_FRONTEND_URL if USE_PRODUCTION_API else DEV_FRONTEND_URL

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
def save_ocr_settings(language=None):
    """Save OCR settings to a configuration file."""
    config = {
        "language": language or DEFAULT_LANGUAGE,
        "together_api_key": TOGETHER_API_KEY
    }
    
    config_dir = os.path.expanduser("~/.textextract")
    os.makedirs(config_dir, exist_ok=True)
    
    config_file = os.path.join(config_dir, "config.json")
    with open(config_file, "w") as f:
        json.dump(config, f, indent=4)

def load_ocr_settings():
    """Load OCR settings from configuration file."""
    config_file = os.path.expanduser("~/.textextract/config.json")
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            config = json.load(f)
            return config.get("language", DEFAULT_LANGUAGE), config.get("together_api_key", "")
    return DEFAULT_LANGUAGE, ""

# Load OCR settings on module import
load_ocr_settings()