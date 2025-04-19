# src/config.py

import json
import os
import sys
import base64
from screeninfo import get_monitors

# OCR Configuration
# Default language for OCR 
DEFAULT_LANGUAGE = 'en'  # English

# Google Cloud setup - embedded credentials approach for SaaS model
# The developer's Google Vision API credentials will be embedded in the application
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_VISION_CREDENTIALS", "")

# You can hardcode a base64-encoded Google Vision API key here for distribution
# This is a fallback if the environment variable is not set
# Format: HARDCODED_CREDENTIALS = "base64:YOUR_BASE64_ENCODED_CREDENTIALS_HERE"
HARDCODED_CREDENTIALS = ""

# Path to store the embedded credentials temporarily
def get_credentials_path():
    """Get the path to the temporary credentials file"""
    temp_dir = os.path.join(os.path.expanduser("~"), ".textextract")
    os.makedirs(temp_dir, exist_ok=True)
    return os.path.join(temp_dir, "vision_credentials.json")

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
        "language": language or DEFAULT_LANGUAGE
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
            return config.get("language", DEFAULT_LANGUAGE)
    return DEFAULT_LANGUAGE

# Setup embedded Google Vision credentials
def setup_embedded_credentials():
    """Set up the embedded Google Vision credentials for the application"""
    # First try the environment variable
    credentials_json_source = GOOGLE_CREDENTIALS_JSON
    
    # If environment variable is empty, try the hardcoded credentials
    if not credentials_json_source and HARDCODED_CREDENTIALS:
        credentials_json_source = HARDCODED_CREDENTIALS
        
    # If we have no credentials, return False
    if not credentials_json_source:
        return False
        
    try:
        # Decode the base64-encoded credentials if provided as base64
        if credentials_json_source.startswith("base64:"):
            credentials_json = base64.b64decode(credentials_json_source[7:]).decode('utf-8')
        else:
            credentials_json = credentials_json_source
            
        # Write the credentials to a temporary file
        credentials_path = get_credentials_path()
        with open(credentials_path, 'w') as f:
            f.write(credentials_json)
            
        # Set the environment variable to point to our temporary file
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        return True
    except Exception as e:
        print(f"Error setting up embedded credentials: {e}")
        return False

# Check if Google Vision credentials are available
def check_google_vision_credentials():
    """Check if Google Vision API credentials are properly set."""
    # First try to use the embedded credentials
    if setup_embedded_credentials():
        return True
        
    # Fall back to checking for user-provided credentials
    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path or not os.path.exists(credentials_path):
        return False
    return True

# Load OCR settings on module import
load_ocr_settings()