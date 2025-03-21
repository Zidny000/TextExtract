import os
import sys
import time
import tkinter as tk
from tkinter import ttk
import threading
import traceback

def download_paddleocr_models():
    """Download PaddleOCR models with a progress window"""
    # Create the progress window
    root = tk.Tk()
    root.title("TextExtract - Downloading OCR Models")
    root.geometry("500x200")
    root.resizable(False, False)
    
    # Try to set the icon
    try:
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(os.path.dirname(sys.executable), 'assets', 'icon.ico')
        else:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'icon.ico')
        
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception:
        pass  # Ignore icon errors
    
    # Center the window
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    # Create UI elements
    frame = ttk.Frame(root, padding="20")
    frame.pack(fill=tk.BOTH, expand=True)
    
    # Header
    header_label = ttk.Label(frame, text="Downloading OCR Models", font=("Arial", 14, "bold"))
    header_label.pack(pady=(0, 10))
    
    # Description
    desc_label = ttk.Label(frame, text="TextExtract is downloading the required OCR models.\nThis may take a few minutes depending on your internet connection.", justify=tk.CENTER)
    desc_label.pack(pady=(0, 20))
    
    # Progress bar
    progress = ttk.Progressbar(frame, orient=tk.HORIZONTAL, length=400, mode='indeterminate')
    progress.pack(pady=(0, 10))
    progress.start(10)
    
    # Status label
    status_var = tk.StringVar(value="Initializing download...")
    status_label = ttk.Label(frame, textvariable=status_var)
    status_label.pack(pady=(0, 20))
    
    # Flag to track download status
    download_success = [False]
    download_error = [None]
    download_completed = [False]
    
    # Function to update status
    def update_status(message):
        status_var.set(message)
        root.update_idletasks()
    
    # Function to close the window
    def close_window():
        root.destroy()
    
    # Function to download models in a separate thread
    def download_thread():
        try:
            # First check if paddle is installed
            try:
                update_status("Checking for paddle package...")
                import paddle
                paddle_version = paddle.__version__
                update_status(f"Found PaddlePaddle {paddle_version}")
                
                # Check if version is what we want
                if paddle_version != "2.6.2":
                    update_status(f"Updating PaddlePaddle from {paddle_version} to 2.6.2...")
                    import subprocess
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "paddlepaddle==2.6.2", "--force-reinstall"])
                    update_status("PaddlePaddle updated successfully!")
            except ImportError:
                update_status("Installing paddle package (required for PaddleOCR)...")
                import subprocess
                
                # Check if 32-bit Python
                is_32bit = sys.maxsize <= 2**32
                
                if is_32bit:
                    update_status("Detected 32-bit Python. Installing paddlepaddle-tiny...")
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "paddlepaddle-tiny==1.6.1"])
                    update_status("Warning: 32-bit Python detected. PaddleOCR may have limited functionality.")
                else:
                    # Install the specific version
                    update_status("Installing PaddlePaddle 2.6.2. This may take a few minutes...")
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "paddlepaddle==2.6.2"])
                
                import paddle
            
            update_status("Importing PaddleOCR...")
            
            # Import required modules
            try:
                from paddleocr import PaddleOCR
                paddleocr_version = None
                try:
                    import paddleocr
                    paddleocr_version = paddleocr.__version__
                    update_status(f"Found PaddleOCR {paddleocr_version}")
                    
                    # Check if version is what we want
                    if paddleocr_version != "2.10.0":
                        update_status(f"Updating PaddleOCR from {paddleocr_version} to 2.10.0...")
                        subprocess.check_call([sys.executable, "-m", "pip", "install", "paddleocr==2.10.0", "--force-reinstall"])
                        update_status("PaddleOCR updated successfully!")
                except (ImportError, AttributeError):
                    pass
                    
            except ImportError:
                update_status("Installing PaddleOCR package...")
                import subprocess
                subprocess.check_call([sys.executable, "-m", "pip", "install", "paddleocr==2.10.0"])
                from paddleocr import PaddleOCR
            
            # Import dependent modules
            update_status("Importing dependent modules...")
            import numpy as np
            from PIL import Image
            
            # Default language
            lang = "en"  # English
            
            update_status(f"Downloading models for language: {lang}...")
            
            # Initialize PaddleOCR which triggers model download
            ocr = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)
            
            # Create a test image to trigger model loading
            update_status("Creating test image to trigger model loading...")
            import tempfile
            img = Image.new('RGB', (100, 30), color='white')
            
            # Create a temp file
            fd, path = tempfile.mkstemp(suffix='.png')
            try:
                os.close(fd)
                img.save(path)
                
                update_status("Running test OCR to ensure models are downloaded...")
                result = ocr.ocr(path)
                
                # Models downloaded successfully
                download_success[0] = True
                download_error[0] = None
            finally:
                try:
                    os.unlink(path)
                except:
                    pass
            
            update_status("Models downloaded successfully!")
            
        except Exception as e:
            error_message = f"Error: {str(e)}\n{traceback.format_exc()}"
            print(error_message)
            download_error[0] = error_message
            update_status(f"Error: {str(e)}")
        finally:
            download_completed[0] = True
    
    # Start the download thread
    download_thread = threading.Thread(target=download_thread, daemon=True)
    download_thread.start()
    
    # Check if download has completed every 100ms
    def check_download_status():
        if download_completed[0]:
            progress.stop()
            if download_success[0]:
                # Change to determinate mode and set to 100%
                progress.configure(mode='determinate', value=100)
            else:
                # Show error information
                progress.configure(mode='determinate', value=0)
        else:
            root.after(100, check_download_status)
    
    root.after(100, check_download_status)
    
    # Start the main loop
    root.mainloop()
    
    return download_success[0], download_error[0]

if __name__ == "__main__":
    success, error = download_paddleocr_models()
    if success:
        print("Models downloaded successfully!")
        sys.exit(0)
    else:
        print(f"Error downloading models: {error}")
        sys.exit(1) 