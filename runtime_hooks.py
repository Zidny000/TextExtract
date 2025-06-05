import os
import sys
import importlib.util
import traceback

# This runtime hook helps PyInstaller find the Python DLL
# It adds the executable directory to the PATH environment variable
# And ensures all modules can be correctly imported

# Set up debugging log file in AppData
log_dir = os.path.join(os.environ.get('APPDATA', ''), 'TextExtract')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'runtime_hooks_debug.log')

# Log initialization
with open(log_file, 'w') as f:
    f.write(f"Runtime hooks starting\n")
    f.write(f"Python version: {sys.version}\n")
    f.write(f"Executable: {sys.executable}\n")
    f.write(f"Frozen: {getattr(sys, 'frozen', False)}\n")
    f.write(f"Current directory: {os.getcwd()}\n")
    f.write(f"sys.path: {sys.path}\n\n")

try:
    if getattr(sys, 'frozen', False):
        # We are running in a PyInstaller bundle
        bundle_dir = os.path.dirname(sys.executable)
        
        with open(log_file, 'a') as f:
            f.write(f"Bundle directory: {bundle_dir}\n")
        
        # Add the bundle directory to PATH
        os.environ['PATH'] = bundle_dir + os.pathsep + os.environ.get('PATH', '')
        
        # Add bundle_dir and src to sys.path to ensure imports work correctly
        if bundle_dir not in sys.path:
            sys.path.insert(0, bundle_dir)
        
        # Add src directory to path
        src_dir = os.path.join(bundle_dir, 'src')
        if os.path.exists(src_dir) and src_dir not in sys.path:
            sys.path.insert(0, src_dir)
            with open(log_file, 'a') as f:
                f.write(f"Added src directory to path: {src_dir}\n")
          # Create directory structure if it doesn't exist
        for dir_name in ['src', 'src/ui', 'src/ui/dialogs', 'src/utils', 'src/utils/threading']:
            dir_path = os.path.join(bundle_dir, dir_name)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                with open(log_file, 'a') as f:
                    f.write(f"Created directory: {dir_path}\n")
            
            # Add empty __init__.py files to directories if they don't exist
            init_file = os.path.join(dir_path, '__init__.py')
            if not os.path.exists(init_file):
                try:
                    with open(init_file, 'w') as f:
                        f.write('# Auto-generated __init__.py')
                    with open(log_file, 'a') as f:
                        f.write(f"Created __init__.py in {dir_path}\n")
                except Exception as e:
                    with open(log_file, 'a') as f:
                        f.write(f"Error creating __init__.py in {dir_path}: {e}\n")
        
        # Log updated sys.path
        with open(log_file, 'a') as f:
            f.write(f"Updated sys.path: {sys.path}\n")
except Exception as e:
    with open(log_file, 'a') as f:
        f.write(f"Error in runtime hook: {e}\n")
        f.write(traceback.format_exc())
    
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