import os
import sys
import json
import base64

# This runtime hook helps PyInstaller find the Python DLL
# It adds the executable directory to the PATH environment variable

def setup_vision_credentials():
    """Set up Google Vision credentials at runtime"""
    from src.config import setup_embedded_credentials, get_credentials_path
    
    # Ensure credentials are set up properly at runtime
    credentials_path = get_credentials_path()
    if not os.path.exists(credentials_path):
        setup_embedded_credentials()

if getattr(sys, 'frozen', False):
    # We are running in a PyInstaller bundle
    bundle_dir = os.path.dirname(sys.executable)
    
    # Add the bundle directory to PATH
    os.environ['PATH'] = bundle_dir + os.pathsep + os.environ.get('PATH', '')
    
    try:
        # Use AppData directory for logs instead of Program Files
        log_dir = os.path.join(os.environ.get('APPDATA', ''), 'TextExtract')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'pyinstaller_debug.log')
        
        # Print diagnostic information to a log file for debugging
        with open(log_file, 'w') as f:
            f.write(f"Python executable: {sys.executable}\n")
            f.write(f"Bundle directory: {bundle_dir}\n")
            f.write(f"PATH: {os.environ['PATH']}\n")
            f.write(f"sys.path: {sys.path}\n")
            
        # Set up Google Vision credentials
        setup_vision_credentials()
    except Exception as e:
        # If logging or setup fails, continue without error
        try:
            with open(log_file, 'a') as f:
                f.write(f"Error during startup: {str(e)}\n")
        except:
            pass 