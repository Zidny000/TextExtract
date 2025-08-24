# src/config.py

import json
import os
import sys
import traceback
from screeninfo import get_monitors

# OCR Configuration
# Default language for OCR 
DEFAULT_LANGUAGE = 'en'  # English

# Together.ai API key for Qwen2-VL
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY", "")

# API Configuration
# Set to True to use production API, False to use local development API
USE_PRODUCTION_API = os.getenv("USE_PRODUCTION_API", "False").lower() == "true"

# Check if this is a PyInstaller bundle
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # If running as compiled executable, always use production API
    USE_PRODUCTION_API = True
else:
    # For development, use environment variable
    USE_PRODUCTION_API = os.getenv("USE_PRODUCTION_API", "False").lower() == "true"

# API URLs
DEV_PROTOCOL = "https"
PROD_PROTOCOL = "https"
DEV_DOMAIN = "textextract-dev.onrender.com"
PROD_DOMAIN = "textextract.onrender.com"

# Frontend URLs
DEV_FRONTEND_DOMAIN = "localhost:3000"
PROD_FRONTEND_DOMAIN = "textextract1.onrender.com"  # Update this if your frontend URL is different

# Update system configuration
UPDATE_GITHUB_OWNER = "Zidny000"
UPDATE_GITHUB_REPO = "TextExtract"

# Get the appropriate API URL based on environment
def get_api_url():
    print(USE_PRODUCTION_API)
    return f"{PROD_PROTOCOL}://{PROD_DOMAIN}" if USE_PRODUCTION_API else f"{DEV_PROTOCOL}://{DEV_DOMAIN}"

# Get the appropriate frontend URL based on environment
def get_frontend_url():
    return f"{PROD_PROTOCOL}://{PROD_FRONTEND_DOMAIN}" if USE_PRODUCTION_API else f"{DEV_PROTOCOL}://{DEV_FRONTEND_DOMAIN}"

def get_config_file_path():
    """Get the appropriate config file path based on environment"""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # If running as compiled executable, use user's app data directory
        config_dir = os.path.join(os.path.expanduser("~"), ".textextract")
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "config.json")
    else:
        # For development, use the current directory
        return "config.json"

def save_config(config):
    config_file = get_config_file_path()
    try:
        with open(config_file, "w") as f:
            json.dump(config, f)
    except Exception as e:
        print(f"Error saving config to {config_file}: {e}")

def load_config():
    config_file = get_config_file_path()
    if not os.path.exists(config_file):
        return {}
    
    try:
        with open(config_file, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config from {config_file}: {e}")
        return {}

def save_selected_monitor(monitor):
    try:
        print(f"Saving monitor config: {monitor.width}x{monitor.height} at {monitor.x},{monitor.y}")
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
        print("Monitor configuration saved successfully")
    except Exception as e:
        print(f"Error saving monitor configuration: {e}")
        print(traceback.format_exc())

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