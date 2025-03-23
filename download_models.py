#!/usr/bin/env python
"""
Tesseract OCR Language Pack Downloader for TextExtract

This script downloads Tesseract language packs for use with TextExtract.
"""

import os
import sys
import subprocess
import tempfile
import threading
import urllib.request
import tkinter as tk
from tkinter import ttk
import shutil
from pathlib import Path

def download_tesseract_language_packs():
    """Download Tesseract language packs with a progress window"""
    # Language data GitHub repository URL
    TESSDATA_URL = "https://github.com/tesseract-ocr/tessdata/raw/main/"
    
    # Create main window
    root = tk.Tk()
    root.title("TextExtract - Download Tesseract Language Packs")
    root.geometry("500x400")
    root.resizable(False, False)
    
    # Create a frame for the UI
    frame = ttk.Frame(root, padding="20")
    frame.pack(fill=tk.BOTH, expand=True)
    
    # Status display
    status_var = tk.StringVar(value="Initializing...")
    status_label = ttk.Label(frame, textvariable=status_var, wraplength=450)
    status_label.pack(pady=(0, 10))
    
    # Progress bar
    progress = ttk.Progressbar(frame, orient=tk.HORIZONTAL, length=450, mode='determinate')
    progress.pack(pady=(0, 10))
    
    # Progress text
    progress_text = tk.StringVar(value="")
    progress_label = ttk.Label(frame, textvariable=progress_text)
    progress_label.pack(pady=(0, 5))
    
    # Log display
    log_frame = ttk.LabelFrame(frame, text="Download Log", padding="10")
    log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
    
    log_text = tk.Text(log_frame, height=10, width=50, wrap=tk.WORD)
    log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=log_text.yview)
    log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    log_text.configure(yscrollcommand=log_scrollbar.set)
    
    def add_to_log(text):
        log_text.configure(state="normal")
        log_text.insert(tk.END, text + "\n")
        log_text.see(tk.END)
        log_text.configure(state="disabled")
        root.update_idletasks()
    
    def update_status(message):
        status_var.set(message)
        add_to_log(message)
        root.update_idletasks()
    
    def update_progress(current, total, lang=""):
        progress["value"] = current / total * 100
        progress_text.set(f"Downloaded {current} of {total} ({int(current/total*100)}%)")
        root.update_idletasks()
    
    # Function to download a specific language pack
    def download_language_pack(lang_code, dest_dir):
        lang_file = f"{lang_code}.traineddata"
        lang_url = f"{TESSDATA_URL}{lang_file}"
        dest_file = os.path.join(dest_dir, lang_file)
        
        update_status(f"Downloading {lang_code} language pack...")
        
        try:
            if os.path.exists(dest_file):
                update_status(f"{lang_code} language pack already exists. Skipping.")
                return True
                
            with urllib.request.urlopen(lang_url) as response, open(dest_file, 'wb') as out_file:
                file_size = int(response.info().get('Content-Length', 0))
                add_to_log(f"Downloading {lang_file} ({file_size / 1024 / 1024:.1f} MB)")
                
                # Download the file
                downloaded = 0
                block_size = 8192
                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                    downloaded += len(buffer)
                    out_file.write(buffer)
                    
                add_to_log(f"Downloaded {lang_file} successfully")
                return True
        except Exception as e:
            add_to_log(f"Error downloading {lang_code}: {str(e)}")
            return False
    
    # Set up the language checkboxes
    language_frame = ttk.LabelFrame(frame, text="Select Languages to Download", padding="10")
    language_frame.pack(fill=tk.X, pady=10)
    
    # Language options with more descriptive labels
    language_options = [
        ("eng", "English", True),  # Required
        ("fra", "French", False),
        ("deu", "German", False),
        ("spa", "Spanish", False),
        ("ita", "Italian", False),
        ("por", "Portuguese", False),
        ("rus", "Russian", False),
        ("chi_sim", "Chinese (Simplified)", False),
        ("jpn", "Japanese", False),
        ("kor", "Korean", False),
        ("ara", "Arabic", False)
    ]
    
    # Create checkboxes arranged in columns
    language_vars = {}
    for i, (code, name, required) in enumerate(language_options):
        var = tk.BooleanVar(value=required)
        language_vars[code] = var
        
        # Calculate row and column for grid layout (3 columns)
        row, col = divmod(i, 3)
        
        # Disable checkbox if language is required
        state = "disabled" if required else "normal"
        cb = ttk.Checkbutton(language_frame, text=name, variable=var, state=state)
        cb.grid(row=row, column=col, sticky="w", padx=5, pady=2)
    
    # Download button
    def start_download():
        # Get the selected languages
        selected_langs = [code for code, var in language_vars.items() if var.get()]
        
        if not selected_langs:
            update_status("No languages selected. Please select at least one language.")
            return
            
        # Disable controls during download
        download_button.configure(state="disabled")
        for child in language_frame.winfo_children():
            if isinstance(child, ttk.Checkbutton) and child["state"] != "disabled":
                child.configure(state="disabled")
        
        def download_thread_func():
            success = False
            error_message = None
            
            try:
                update_status("Checking for pytesseract installation...")
                
                # Check if pytesseract is installed
                try:
                    import pytesseract
                    update_status("pytesseract is installed")
                except ImportError:
                    update_status("Installing pytesseract...")
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "pytesseract"])
                    import pytesseract
                
                # Set up tessdata directory
                # First check if Tesseract is installed and where its tessdata directory is
                tessdata_dir = None
                
                # On Windows, check common Tesseract paths
                if sys.platform.startswith('win'):
                    common_paths = [
                        r'C:\Program Files\Tesseract-OCR\tessdata',
                        r'C:\Program Files (x86)\Tesseract-OCR\tessdata',
                    ]
                    
                    for path in common_paths:
                        if os.path.isdir(path) and os.access(path, os.W_OK):
                            tessdata_dir = path
                            break
                
                # If no writable tessdata directory found, use bundled directory
                if not tessdata_dir:
                    # Create bundled_tesseract/tessdata in the script directory
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    tessdata_dir = os.path.join(script_dir, "bundled_tesseract", "tessdata")
                    os.makedirs(tessdata_dir, exist_ok=True)
                    
                    # If on Windows, also create bundled_tesseract directory
                    if sys.platform.startswith('win'):
                        tesseract_exe = os.path.join(script_dir, "bundled_tesseract", "tesseract.exe")
                        if not os.path.exists(tesseract_exe):
                            update_status("Warning: bundled_tesseract directory selected but tesseract.exe not found.")
                            update_status("You will need to install Tesseract or copy tesseract.exe to this directory.")
                
                update_status(f"Using tessdata directory: {tessdata_dir}")
                
                # Download language packs
                total_langs = len(selected_langs)
                for i, lang in enumerate(selected_langs):
                    update_progress(i, total_langs, lang)
                    if download_language_pack(lang, tessdata_dir):
                        add_to_log(f"✓ {lang} language pack installed successfully")
                    else:
                        add_to_log(f"✗ Failed to download {lang} language pack")
                
                update_progress(total_langs, total_langs)
                update_status("Language packs download complete!")
                success = True
                
            except Exception as e:
                error_message = str(e)
                update_status(f"Error: {error_message}")
                add_to_log(f"Download failed: {error_message}")
            
            # Re-enable controls
            root.after(0, lambda: download_button.configure(state="normal"))
            for child in language_frame.winfo_children():
                if isinstance(child, ttk.Checkbutton) and child["state"] == "disabled" and child.cget("text") != "English":
                    root.after(0, lambda c=child: c.configure(state="normal"))
            
            return success, error_message
        
        # Start the download in a separate thread
        download_thread = threading.Thread(target=download_thread_func)
        download_thread.daemon = True
        download_thread.start()
    
    download_button = ttk.Button(frame, text="Download Selected Languages", command=start_download)
    download_button.pack(pady=10)
    
    # Close button
    close_button = ttk.Button(frame, text="Close", command=root.destroy)
    close_button.pack(pady=5)
    
    # Initialize
    update_status("Ready to download Tesseract language packs")
    progress["value"] = 0
    
    # Start the GUI
    root.mainloop()

if __name__ == "__main__":
    success, error = download_tesseract_language_packs()
    if success:
        print("Language packs downloaded successfully!")
        sys.exit(0)
    else:
        print(f"Error downloading language packs: {error}")
        sys.exit(1) 