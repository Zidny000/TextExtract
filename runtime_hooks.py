import os
import sys

# This runtime hook helps PyInstaller find the Python DLL
# It adds the executable directory to the PATH environment variable

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
    except Exception as e:
        # If logging fails, continue without error
        pass 