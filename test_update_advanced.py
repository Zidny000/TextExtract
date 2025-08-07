"""
Advanced test script for the update system
This script provides detailed logging and error handling to help diagnose update issues
"""

import os
import sys
import time
import logging
import tkinter as tk
from tkinter import ttk
import traceback
from threading import Thread

# Configure logging to both file and console with timestamps
log_file = "update_test_detailed.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("UpdateTester")

class LoggingHandler(logging.Handler):
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget
        self.formatter = logging.Formatter('%(levelname)s: %(message)s')
        
    def emit(self, record):
        msg = self.formatter.format(record)
        def update_text():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.see(tk.END)
            self.text_widget.configure(state='disabled')
        self.text_widget.after(0, update_text)

class MockAppState:
    def __init__(self):
        self.running = True
        self.update_in_progress = False

def main():
    try:
        logger.info("=== Update System Test Application ===")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Current directory: {os.getcwd()}")
        
        # Create main window
        root = tk.Tk()
        root.title("TextExtract Update System Tester")
        root.geometry("800x600")
        
        # Create a mock app state
        app_state = MockAppState()
        
        # Create a notebook with tabs for different test scenarios
        notebook = ttk.Notebook(root)
        notebook.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Log tab
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="Logs")
        
        # Create a text widget for logging
        log_text = tk.Text(log_frame, wrap=tk.WORD, height=20)
        log_text.pack(expand=True, fill='both', padx=5, pady=5)
        log_text.configure(state='disabled')
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(log_text, orient='vertical', command=log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        log_text['yscrollcommand'] = scrollbar.set
        
        # Add custom log handler to display logs in UI
        text_handler = LoggingHandler(log_text)
        text_handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(text_handler)
        
        # Test actions tab
        action_frame = ttk.Frame(notebook)
        notebook.add(action_frame, text="Test Actions")
        
        # Progress variables
        progress_var = tk.DoubleVar(value=0.0)
        status_var = tk.StringVar(value="Ready")
        
        # Progress display
        ttk.Label(action_frame, text="Test Progress:").pack(pady=(10, 0))
        progress = ttk.Progressbar(action_frame, orient="horizontal", 
                                   length=400, mode="determinate",
                                   variable=progress_var)
        progress.pack(pady=(5, 10), padx=20, fill=tk.X)
        
        status_label = ttk.Label(action_frame, textvariable=status_var)
        status_label.pack(pady=5)
        
        # Functions for test actions
        def update_status(message, progress_value=None):
            status_var.set(message)
            if progress_value is not None:
                progress_var.set(progress_value)
            logger.info(message)
        
        def run_direct_update_test():
            """Run a direct update test"""
            try:
                update_status("Starting direct update test", 10)
                # Import the update manager
                from src.updater import UpdateManager
                
                # Create an update manager with the mock app state
                update_manager = UpdateManager(app_state)
                update_status("Created update manager", 20)
                
                # Simulate update available
                update_manager.update_available = True
                update_manager.latest_version = "1.1.0"
                update_manager.download_url = "https://github.com/Zidny000/textextract-releases/releases/download/v1.0.1/TextExtract_Setup.exe"
                update_manager.update_info = {
                    "version": "1.1.0",
                    "release_notes": "Test release notes for version 1.1.0",
                    "silent_install": True
                }
                update_status("Configured mock update data", 30)
                
                # Show update prompt
                update_status("Showing update prompt", 40)
                should_update = update_manager.prompt_for_update(root)
                
                if should_update:
                    update_status("User accepted update, starting download", 50)
                    update_manager.download_and_install_update(root, show_progress=True)
                else:
                    update_status("User declined the update", 0)
            except Exception as e:
                logger.error(f"Error in direct update test: {e}")
                logger.error(traceback.format_exc())
                update_status(f"Error: {str(e)}", 0)
        
        def run_background_update_test():
            """Run a background update test"""
            try:
                update_status("Starting background update test", 10)
                
                from src.updater import UpdateManager
                
                # Create and prepare an update manager
                update_manager = UpdateManager(app_state)
                update_manager.update_available = True
                update_manager.latest_version = "1.1.0"
                update_manager.download_url = "https://github.com/Zidny000/textextract-releases/releases/download/v1.0.1/TextExtract_Setup.exe"
                update_manager.update_info = {
                    "version": "1.1.0",
                    "release_notes": "Test release notes for background update test",
                    "silent_install": True
                }
                
                # Store it in the app state
                app_state._update_manager = update_manager
                
                # Import and run the background update check
                from src.updater import start_background_update_check
                update_status("Starting background update process", 20)
                
                # Start the background update check
                thread = start_background_update_check(app_state, root)
                
                # Monitor the thread
                def check_thread():
                    if thread.is_alive():
                        update_status("Background update thread still running", 30)
                        root.after(1000, check_thread)
                    else:
                        update_status("Background update thread completed", 100)
                
                # Start monitoring
                root.after(1000, check_thread)
                
            except Exception as e:
                logger.error(f"Error in background update test: {e}")
                logger.error(traceback.format_exc())
                update_status(f"Error: {str(e)}", 0)
        
        def run_download_only_test():
            """Test just the download functionality"""
            try:
                update_status("Testing file download only", 10)
                
                from src.updater import UpdateManager
                import tempfile
                
                # Create temporary directory
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Create update manager
                    update_manager = UpdateManager(app_state)
                    
                    # Set download destination
                    download_url = "https://github.com/Zidny000/textextract-releases/releases/download/v1.0.1/TextExtract_Setup.exe"
                    destination = os.path.join(temp_dir, "TextExtract_Setup.exe")
                    
                    update_status(f"Downloading to {destination}", 20)
                    
                    # Start download in a separate thread
                    def do_download():
                        try:
                            update_manager._download_file(download_url, destination)
                            # Check result on main thread
                            root.after(0, lambda: check_download_result(destination))
                        except Exception as e:
                            logger.error(f"Download error: {e}")
                            logger.error(traceback.format_exc())
                            root.after(0, lambda: update_status(f"Download failed: {str(e)}", 0))
                    
                    def check_download_result(dest_path):
                        if os.path.exists(dest_path):
                            size_mb = os.path.getsize(dest_path) / (1024 * 1024)
                            update_status(f"Download completed: {size_mb:.2f} MB", 100)
                        else:
                            update_status("Download failed: File not found", 0)
                    
                    # Start the download thread
                    download_thread = Thread(target=do_download)
                    download_thread.daemon = True
                    download_thread.start()
                    
                    # Start monitoring
                    def monitor_download():
                        if download_thread.is_alive():
                            update_status("Download in progress...", 50)
                            root.after(1000, monitor_download)
                    
                    root.after(1000, monitor_download)
                    
            except Exception as e:
                logger.error(f"Error in download test: {e}")
                logger.error(traceback.format_exc())
                update_status(f"Error: {str(e)}", 0)
                
        def run_batch_file_test():
            """Test just the batch file creation and execution"""
            try:
                update_status("Testing batch file creation", 10)
                
                import tempfile
                import subprocess
                from src.updater import APP_NAME
                
                # Create a simple test batch file
                user_temp = os.environ.get('TEMP', os.path.expanduser('~'))
                batch_path = os.path.join(user_temp, f"{APP_NAME}_Test_Batch.bat")
                
                update_status(f"Creating batch file at {batch_path}", 20)
                
                # Write a simple batch file that just shows a message
                with open(batch_path, 'w') as f:
                    f.write('@echo off\n')
                    f.write('echo This is a test batch file for TextExtract updater\n')
                    f.write('echo Current directory: %CD%\n')
                    f.write('echo Process ID: %RANDOM%-%RANDOM%\n')
                    f.write('timeout /t 5\n')
                    f.write('echo Test completed\n')
                    f.write('del "%~f0"\n')
                    f.write('exit\n')
                
                update_status("Batch file created", 50)
                
                # Launch the batch file
                update_status("Launching batch file", 60)
                
                # Setup startupinfo for visible window
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 1
                
                # Launch the process
                process = subprocess.Popen(
                    f'cmd.exe /c "{batch_path}"',
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                
                update_status(f"Batch file launched with PID: {process.pid}", 100)
                
            except Exception as e:
                logger.error(f"Error in batch file test: {e}")
                logger.error(traceback.format_exc())
                update_status(f"Error: {str(e)}", 0)
        
        # Add buttons for different tests
        ttk.Button(action_frame, text="Run Direct Update Test", 
                   command=run_direct_update_test).pack(pady=10)
        ttk.Button(action_frame, text="Run Background Update Test", 
                   command=run_background_update_test).pack(pady=10)
        ttk.Button(action_frame, text="Test Download Only", 
                   command=run_download_only_test).pack(pady=10)
        ttk.Button(action_frame, text="Test Batch File", 
                   command=run_batch_file_test).pack(pady=10)
        ttk.Button(action_frame, text="Exit", 
                   command=root.quit).pack(pady=20)
        
        # Setup tab
        setup_frame = ttk.Frame(notebook)
        notebook.add(setup_frame, text="Environment")
        
        # Show environment info
        env_text = tk.Text(setup_frame, wrap=tk.WORD, height=20)
        env_text.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Environment info
        env_info = [
            f"Python version: {sys.version}",
            f"Current directory: {os.getcwd()}",
            f"Log file: {os.path.abspath(log_file)}",
        ]
        
        # Add module info
        try:
            import src.updater
            env_info.append(f"Updater module: {src.updater.__file__}")
            from src.updater import APP_NAME, __version__
            env_info.append(f"Application: {APP_NAME} v{__version__}")
        except Exception as e:
            env_info.append(f"Error getting updater info: {e}")
        
        # Add environment variables
        env_info.append("\nEnvironment Variables:")
        for key, value in os.environ.items():
            if key in ['TEMP', 'TMP', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 
                      'PATH', 'PYTHONPATH', 'SystemRoot']:
                env_info.append(f"{key}: {value}")
        
        # Set environment text
        for line in env_info:
            env_text.insert(tk.END, line + '\n')
        
        env_text.configure(state='disabled')
        
        # Start the app
        update_status("Application started")
        root.mainloop()
        
    except Exception as e:
        logger.error(f"Critical error: {e}")
        logger.error(traceback.format_exc())
        
if __name__ == "__main__":
    main()
