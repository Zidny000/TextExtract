"""
Automatic update system for TextExtract.
This module handles checking for updates, downloading, and installing them.
"""

import os
import sys
import json
import tempfile
import shutil
import subprocess
import requests
import time
import logging
import traceback
from threading import Thread
import tkinter as tk
from tkinter import messagebox
import winreg

# Import version information
from version import (
    __version__, APP_NAME, REGISTRY_PATH, 
    UPDATE_URL, ENABLE_AUTO_UPDATE, 
    UPDATE_CHECK_INTERVAL_HOURS, UPDATE_CHANNEL
)
from src.config import get_api_url

logger = logging.getLogger(__name__)

class UpdateManager:
    def __init__(self, app_state=None):
        """Initialize the update manager"""
        self.app_state = app_state
        self.current_version = __version__
        self.latest_version = None
        self.update_info = None
        self.download_url = None
        self.update_thread = None
        self.last_check_time = self._get_last_check_time()
        self.update_available = False
        self.update_in_progress = False
    
    def _get_last_check_time(self):
        """Get the last time an update check was performed from the registry"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH)
            last_check_time, _ = winreg.QueryValueEx(key, "LastUpdateCheck")
            winreg.CloseKey(key)
            return float(last_check_time)
        except (FileNotFoundError, WindowsError, ValueError):
            return 0
    
    def _set_last_check_time(self, timestamp=None):
        """Set the last update check time in the registry"""
        if timestamp is None:
            timestamp = time.time()
            
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH)
            winreg.SetValueEx(key, "LastUpdateCheck", 0, winreg.REG_SZ, str(timestamp))
            winreg.CloseKey(key)
        except Exception as e:
            logger.error(f"Error setting last update check time: {e}")
    
    def should_check_for_updates(self):
        """Determine if it's time to check for updates"""
        if not ENABLE_AUTO_UPDATE:
            return False
            
        # Check if enough time has passed since the last check
        current_time = time.time()
        elapsed_hours = (current_time - self.last_check_time) / 3600
        
        return elapsed_hours >= UPDATE_CHECK_INTERVAL_HOURS
    
    def check_for_updates(self, force=False):
        """Check if updates are available"""
        # Skip if auto-update is disabled and not forcing
        if not ENABLE_AUTO_UPDATE and not force:
            logger.info("Automatic updates are disabled")
            return False
        
        # Skip if not time to check and not forcing
        if not force and not self.should_check_for_updates():
            logger.info("Skipping update check (checked recently)")
            return False
            
        try:
            # Construct the full update URL using the API base URL
            api_base_url = get_api_url()
            full_update_url = f"{api_base_url}{UPDATE_URL}"
            
            # Add query parameters
            query_params = {
                'version': self.current_version,
                'platform': 'windows',
                'channel': UPDATE_CHANNEL
            }
            
            logger.info(f"Checking for updates from {full_update_url}")
            
            try:
                # Make the request with a reasonable timeout and retry logic
                for attempt in range(3):  # Try up to 3 times
                    try:
                        response = requests.get(
                            full_update_url,
                            params=query_params,
                            timeout=10,
                            headers={'User-Agent': f'TextExtract/{self.current_version}'}
                        )
                        response.raise_for_status()
                        break  # Break if successful
                    except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as req_err:
                        if attempt < 2:  # Don't log on final attempt as we'll catch it outside
                            logger.warning(f"Update check attempt {attempt+1} failed: {req_err}. Retrying...")
                            time.sleep(1)  # Short delay before retry
                        else:
                            raise  # Re-raise on final attempt
                            
                # Process the response
                update_info = response.json()
                logger.debug(f"Update check response: {update_info}")
                
                # Check for available flag in response
                if not update_info.get("available", False):
                    logger.info(f"No updates available: {update_info.get('message', 'Unknown reason')}")
                    self._set_last_check_time()  # Still update check time even if no updates
                    return False
                
                self.latest_version = update_info.get("version")
                
                # Update the last check time
                self._set_last_check_time()
                
                # Store update info
                self.update_info = update_info
                self.download_url = update_info.get("download_url")
                self.update_available = True
                logger.info(f"Update available: {self.latest_version} (current: {self.current_version})")
                return True
                
            except requests.exceptions.HTTPError as http_err:
                if hasattr(response, 'status_code') and response.status_code == 429:
                    logger.warning("Update check rate limited by server")
                    return False
                else:
                    logger.error(f"HTTP error during update check: {http_err}")
                    raise
            except requests.exceptions.ConnectionError:
                logger.error(f"Connection error when checking for updates - server may be down")
                raise
            except requests.exceptions.Timeout:
                logger.error(f"Timeout when checking for updates")
                raise
            except requests.exceptions.RequestException as req_err:
                logger.error(f"Request error when checking for updates: {req_err}")
                raise
                
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            # Update the last check time anyway to prevent constant retries on failures
            # But use a shorter interval (1/4 of normal) to retry sooner than normal
            self._set_last_check_time(time.time() - (UPDATE_CHECK_INTERVAL_HOURS * 3600 * 0.75))
            return False
    
    def _is_newer_version(self, latest_version, current_version):
        """Compare version strings to determine if the latest version is newer"""
        try:
            # Split version strings and convert to integers
            latest_parts = [int(part) for part in latest_version.split('.')]
            current_parts = [int(part) for part in current_version.split('.')]
            
            # Pad with zeros if needed
            while len(latest_parts) < 3:
                latest_parts.append(0)
            while len(current_parts) < 3:
                current_parts.append(0)
                
            # Compare major, minor, patch versions
            for latest, current in zip(latest_parts, current_parts):
                if latest > current:
                    return True
                elif latest < current:
                    return False
            
            # If we get here, versions are the same
            return False
            
        except Exception as e:
            logger.error(f"Error comparing versions: {e}")
            return False
    
    def prompt_for_update(self, parent_window=None):
        """Show a prompt asking the user if they want to update"""
        if not self.update_available:
            return False
            
        message = (f"A new version of {APP_NAME} is available!\n\n"
                  f"Current version: {self.current_version}\n"
                  f"New version: {self.latest_version}\n\n"
                  f"Release notes:\n{self.update_info.get('release_notes', 'No release notes available.')}\n\n"
                  f"Would you like to download and install this update now?")
                  
        result = messagebox.askyesno("Software Update", message, parent=parent_window)
        logger.info(f"User response to update prompt: {'Yes' if result else 'No'}")
        return result
    
    def download_and_install_update(self, parent_window=None, show_progress=True):
        """Download and install the latest update"""
        if not self.download_url:
            logger.error("No download URL available")
            return False
            
        if self.update_in_progress:
            logger.info("Update already in progress")
            return False
        logger.info("Starting update download and installation")
        self.update_in_progress = True

        if parent_window is None or not parent_window.winfo_exists():
            print("Invalid parent window provided to show_download_dialog")
            return False
            
        # Ensure the parent is visible while creating the dialog
        was_withdrawn = parent_window.state() == 'withdrawn'
        if was_withdrawn:
            parent_window.deiconify()
            parent_window.update()
        
        # Start update in a background thread
        self.update_thread = Thread(
            target=self._perform_update_process,
            args=(parent_window, show_progress),
            daemon=True
        )
        self.update_thread.start()
     
        
        # self._perform_update_process(parent_window, show_progress)
        return True
    
    def _perform_update_process(self, parent_window=None, show_progress=True):
        """Perform the actual update process in a background thread"""
        try:
            # Create a persistent copy of the installer outside the temp directory
            persistent_installer_path = os.path.join(os.path.dirname(tempfile.gettempdir()), f"{APP_NAME}_Setup.exe")
            
            # Create a temporary directory for the initial download
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_installer_path = os.path.join(temp_dir, f"{APP_NAME}_Setup.exe")
                
                
                # Show progress dialog in the main thread if requested
                if show_progress and parent_window:
                  # Use after to create dialog in main thread
                  logger.info(f"_create_and_show_progress_dialog called with parent_window")
                  parent_window.after(0, lambda: self._create_and_show_progress_dialog(parent_window, "Downloading update..."))
                  # Give time for the dialog to be created
                  time.sleep(0.5)
                 
                
                # Download the update file
                try:
                    logger.info(f"Downloading update from {self.download_url}")
                    self._download_file(self.download_url, temp_installer_path)
                    logger.info("Download completed successfully")
                    
                    # Copy to persistent location - but first make sure destination directory exists
                    persistent_dir = os.path.dirname(persistent_installer_path)
                    if not os.path.exists(persistent_dir):
                        os.makedirs(persistent_dir, exist_ok=True)
                    
                    # Make sure the target file doesn't exist (to avoid access conflicts)
                    if os.path.exists(persistent_installer_path):
                        try:
                            os.unlink(persistent_installer_path)
                        except Exception as e:
                            logger.warning(f"Could not remove existing installer: {e}")
                            # Generate a unique filename instead
                            persistent_installer_path = os.path.join(
                                os.path.dirname(persistent_installer_path),
                                f"{APP_NAME}_Setup_{int(time.time())}.exe"
                            )
                    
                    # Copy the file
                    shutil.copy2(temp_installer_path, persistent_installer_path)
                    logger.info(f"Copied installer to {persistent_installer_path}")
                    
                    # Ensure we don't have any open handles to the temp file
                    # This is important for clean temp directory removal
                    import gc
                    gc.collect()  # Force garbage collection to close any lingering file handles
                except Exception as e:
                    logger.error(f"Failed to download update: {e}")
                    # Update UI in main thread
                    if parent_window:
                        parent_window.after(0, lambda: messagebox.showerror(
                            "Download Error", 
                            f"Failed to download the update:\n{str(e)}",
                            parent=parent_window
                        ))
                    self.update_in_progress = False
                    return
            
            # Get the current executable path
            if getattr(sys, 'frozen', False):
                app_path = sys.executable
            else:
                app_path = None
            
            # Use silent installation if available
            silent_args = "/SILENT" if self.update_info.get("silent_install", False) else ""
            cmd = f'"{persistent_installer_path}" {silent_args}'
            
            # Use the main thread to finish the update process
            if parent_window:
                parent_window.after(0, lambda: self._finalize_update(parent_window, cmd, persistent_installer_path))
            else:
                # No parent window, so just run the installer directly
                subprocess.Popen(cmd, shell=True)
                sys.exit(0)
                
        except Exception as e:
            logger.error(f"Error during update process: {e}")
            self.update_in_progress = False
            
            # Show error in main thread
            if parent_window:
                parent_window.after(0, lambda: messagebox.showerror(
                    "Update Error", 
                    f"An error occurred during the update process:\n{str(e)}",
                    parent=parent_window
                ))
            
    def _finalize_update(self, parent_window, cmd, installer_path):
        """Finalize the update process in the main thread"""
        try:
            # Show final message
            messagebox.showinfo(
                "Installing Update",
                f"The update has been downloaded and will now be installed.\n"
                f"The application will close and the installer will start automatically.",
                parent=parent_window
            )
            
            logger.info("Starting finalize update process")
            
            # Create a batch file to run the installer after the application exits
            # First try the application directory as it's often writable by the app
            try:
                app_dir = None
                if getattr(sys, 'frozen', False):
                    app_dir = os.path.dirname(sys.executable)
                    logger.info(f"Using app directory for batch file: {app_dir}")
            except Exception:
                app_dir = None
                
            # If app dir isn't available or is read-only, use the user's temp directory
            if not app_dir or not os.access(app_dir, os.W_OK):
                user_temp = os.environ.get('TEMP', os.path.expanduser('~'))
                logger.info(f"Using temp directory for batch file: {user_temp}")
                batch_dir = user_temp
            else:
                batch_dir = app_dir
                
            # Generate a unique batch filename to avoid conflicts
            timestamp = int(time.time())
            batch_filename = f"{APP_NAME}_Install_Helper_{timestamp}.bat"
            batch_path = os.path.join(batch_dir, batch_filename)
            
            logger.info(f"Creating installer batch file at: {batch_path}")
            
            # The batch file waits a moment, then runs the installer
            try:
                # Create a robust batch file
                with open(batch_path, 'w') as f:
                    f.write('@echo off\n')
                    f.write('setlocal enabledelayedexpansion\n')
                    f.write(f'echo Installing update for {APP_NAME}...\n')
                    f.write('echo Process ID: %RANDOM%-%RANDOM%\n')  # Add some uniqueness
                    f.write('echo Waiting for application to exit completely...\n')
                    f.write('timeout /t 5 /nobreak > nul\n')  # Wait 5 seconds
                    
                    # Get current process ID (for logging)
                    f.write('for /f "tokens=2" %%a in (\'tasklist /nh /fi "imagename eq cmd.exe"\') do set PID=%%a\n')
                    f.write('echo Installer running from CMD process !PID!\n')
                    
                    # Run the installer with full path
                    f.write(f'echo Running installer: {cmd}\n')
                    f.write(f'start "" {cmd}\n')
                    f.write('if errorlevel 1 (\n')
                    f.write('   echo Failed to start installer\n')
                    f.write('   pause\n')
                    f.write(') else (\n')
                    f.write('   echo Installer started successfully\n')
                    f.write(')\n')
                    
                    # Wait, then clean up
                    f.write('timeout /t 5 /nobreak > nul\n')
                    f.write('echo Cleaning up...\n')
                    f.write('timeout /t 2 /nobreak > nul\n')
                    f.write('del "%~f0" >nul 2>&1\n')  # Self-delete the batch file
                    f.write('exit\n')
                
                logger.info(f"Created installer batch file successfully")
                
                # Make sure the batch file is executable
                os.chmod(batch_path, 0o755)
                
                # Make the batch file visible in Explorer so it can be manually run if needed
                os.system(f'attrib -h "{batch_path}"')
                
                # Launch the batch file that will run the installer
                logger.info("Launching installer batch file")
                
                # Use a different approach to launch the batch - more robust
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 1  # SW_SHOWNORMAL
                
                # Launch with cmd.exe explicitly to ensure it runs properly
                cmd_process = subprocess.Popen(
                    f'cmd.exe /c "{batch_path}"',
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    shell=True
                )
                
                logger.info(f"Batch file process launched with PID: {cmd_process.pid}")
            except Exception as e:
                logger.error(f"Error creating/launching batch file: {e}")
                logger.info(f"Traceback: {traceback.format_exc()}")
                
                # Fallback to direct launch if batch file creation fails
                logger.info("Using fallback direct installer launch")
                subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                logger.info("Launched installer directly as fallback")
            
            # Force garbage collection before exit to release any file handles
            import gc
            gc.collect()
            logger.info("Performed garbage collection before shutdown")
            
            # Schedule application shutdown
            logger.info("Scheduling application shutdown")
            parent_window.after(800, self._safe_shutdown_application, parent_window)
            
        except Exception as e:
            logger.error(f"Error finalizing update: {e}")
            messagebox.showerror(
                "Update Error", 
                f"Failed to launch the installer:\n{str(e)}",
                parent=parent_window
            )
            self.update_in_progress = False
                
        except Exception as e:
            logger.error(f"Error during update process: {e}")
            self.update_in_progress = False
                
            # Show error in main thread
            if parent_window:
                parent_window.after(0, lambda: messagebox.showerror(
                    "Update Error", 
                    f"An error occurred during the update process:\n{str(e)}",
                    parent=parent_window
                ))
            
    def _safe_shutdown_application(self, parent_window):
        """Safely shutdown the application with proper cleanup"""
        try:
            logger.info("Performing safe shutdown for update...")
            
            # If we have a progress dialog, destroy it
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                try:
                    if self.progress_dialog.winfo_exists():
                        self.progress_dialog.destroy()
                        logger.info("Progress dialog closed successfully")
                except Exception as e:
                    logger.error(f"Error closing progress dialog: {e}")
            
            # Force garbage collection to release file handles
            import gc
            gc.collect()
            logger.info("Garbage collection performed")
            
            # Set flag that update is in progress so other parts of app know
            if self.app_state:
                self.app_state.update_in_progress = True
                logger.info("App state updated - update in progress")
            
            # Display a final message to console
            print("\n\nUpdate is ready. Application will close now and update will install automatically.\n\n")
            logger.info("Final update message displayed")
            
            # Delay slightly to allow messages to be processed
            time.sleep(1.0)
            
            try:
                # Call destroy explicitly before quit to ensure proper cleanup
                logger.info("Destroying main window")
                parent_window.destroy()
                logger.info("Main window destroyed")
            except Exception as e:
                logger.error(f"Error destroying window: {e}")
            
            # After a delay, call the final quit
            logger.info("Scheduling final application quit")
            if hasattr(parent_window, 'after'):
                try:
                    parent_window.after(500, lambda: self._final_quit())
                    logger.info("Quit scheduled through tkinter")
                except Exception as e:
                    logger.error(f"Error scheduling quit: {e}")
                    # If scheduling fails, quit directly
                    self._final_quit()
            else:
                # If the window was already destroyed, exit more directly
                logger.info("Window already destroyed, exiting directly")
                self._final_quit()
                
        except Exception as e:
            logger.error(f"Error during safe shutdown: {e}")
            # Try direct exit as last resort
            logger.info("Attempting direct system exit as last resort")
            sys.exit(0)
    
    def _final_quit(self):
        """Final function to quit the application after update is prepared"""
        try:
            logger.info("Final quit executing")
            # Do one final garbage collection
            import gc
            gc.collect()
            # Exit the application
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error in final quit: {e}")
            # Force exit
            os._exit(0)
    
    def _download_file(self, url, destination):
        """Download a file from the given URL to the destination path"""
        response = None
        temp_file = f"{destination}.downloading"
        try:
            # First create the directory if it doesn't exist
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            
            # Clean up any existing temporary download file
            if os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                    logger.info("Removed existing temporary download file")
                except Exception as e:
                    logger.warning(f"Could not remove existing temp file: {e}")
            
            # Setup headers to help with large files and handle redirects
            headers = {
                'User-Agent': f'TextExtract/{self.current_version}',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            }
            
            # Download with explicit cleanup and properly handle redirects
            logger.info(f"Starting download from {url}")
            
            # Use a session to handle redirects properly
            with requests.Session() as session:
                # Set session options
                session.max_redirects = 5
                
                # Make the initial request - with stream=True for large files
                response = session.get(
                    url, 
                    stream=True, 
                    timeout=60,  # Longer timeout for large files
                    headers=headers,
                    allow_redirects=True
                )
                response.raise_for_status()
                
                # Get the file size if available
                file_size = int(response.headers.get('content-length', 0))
                if file_size > 0:
                    logger.info(f"Download size: {file_size / (1024*1024):.2f} MB")
                    # Store the file size for progress calculations
                    self._download_total_size = file_size
                else:
                    self._download_total_size = 0
                    
                # Reset progress tracking
                self._download_progress = 0
                
                # Download with progress tracking
                downloaded = 0
                last_log_time = time.time()
                last_progress_update = time.time()
                
                # Download to temporary file
                with open(temp_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=64*1024):  # 64KB chunks
                        if chunk:
                            f.write(chunk)
                            
                            # Track download progress
                            downloaded += len(chunk)
                            
                            # Update progress for UI
                            if file_size > 0:
                                self._download_progress = (downloaded / file_size) * 100
                                
                                # Update progress dialog if available
                                current_time = time.time()
                                if hasattr(self, 'progress_dialog') and self.progress_dialog and current_time - last_progress_update > 0.3:
                                    try:
                                        if self.progress_dialog.winfo_exists():
                                            # Update on main thread
                                            progress_value = int(self._download_progress)
                                            status_text = f"Downloading: {progress_value}% ({downloaded/(1024*1024):.2f} MB)"
                                            
                                            # Access root through progress dialog
                                            if hasattr(self.progress_dialog, 'master') and self.progress_dialog.master:
                                                self.progress_dialog.master.after(
                                                    0, 
                                                    lambda: self._update_progress_safe(progress_value, status_text)
                                                )
                                        last_progress_update = current_time
                                    except Exception as e:
                                        logger.error(f"Error updating progress dialog: {e}")
                            
                            # Log progress every few seconds
                            current_time = time.time()
                            if current_time - last_log_time > 3.0 and file_size > 0:
                                percent = (downloaded / file_size) * 100
                                logger.info(f"Download progress: {percent:.1f}% ({downloaded/(1024*1024):.2f} MB)")
                                last_log_time = current_time
                
                # Log completion
                logger.info(f"Download complete: {downloaded/(1024*1024):.2f} MB")
                
                # Set final progress
                if file_size > 0:
                    self._download_progress = 100
                    # Final update to progress dialog
                    if hasattr(self, 'progress_dialog') and self.progress_dialog:
                        try:
                            if self.progress_dialog.winfo_exists():
                                self.progress_dialog.master.after(
                                    0, 
                                    lambda: self._update_progress_safe(100, f"Download complete: {downloaded/(1024*1024):.2f} MB")
                                )
                        except Exception as e:
                            logger.error(f"Error updating final progress: {e}")
                
                # Explicit close and cleanup of the response
                response.close()
                response = None
            
            # Verify the temporary file exists and has content
            if not os.path.exists(temp_file) or os.path.getsize(temp_file) == 0:
                raise Exception(f"Downloaded file is empty or missing: {temp_file}")
            
            # Rename the temporary file to the final destination
            logger.info(f"Moving downloaded file to final destination: {destination}")
            if os.path.exists(destination):
                try:
                    os.unlink(destination)  # Remove existing file
                except Exception as e:
                    logger.warning(f"Could not remove existing destination file: {e}")
                    # Try with a unique destination instead
                    destination = f"{destination}.{int(time.time())}"
                    logger.info(f"Using alternative destination: {destination}")
            
            # Move the file using shutil instead of rename (more robust)
            shutil.move(temp_file, destination)
            
            # Final verification
            if os.path.exists(destination) and os.path.getsize(destination) > 0:
                logger.info(f"Download completed and verified: {os.path.getsize(destination)/(1024*1024):.2f} MB")
                return True
            else:
                raise Exception("Final downloaded file verification failed")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during download: {e}")
            if isinstance(e, requests.exceptions.ConnectionError):
                logger.error("Connection error - check your internet connection")
            elif isinstance(e, requests.exceptions.Timeout):
                logger.error("Download timed out - server may be slow or file too large")
            elif isinstance(e, requests.exceptions.HTTPError):
                logger.error(f"HTTP error {e.response.status_code if hasattr(e, 'response') else 'unknown'}")
            raise Exception(f"Download failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error downloading update: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
        finally:
            # Ensure resources are cleaned up
            if response:
                try:
                    response.close()
                except:
                    pass
            
            # Clean up temp file if it exists and we failed
            if os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                    logger.info("Cleaned up temporary download file")
                except Exception as e:
                    logger.warning(f"Could not remove temporary file: {e}")
    
    def _create_progress_dialog(self, parent):
        """Create a progress dialog for the update process"""
        dialog = tk.Toplevel(parent)
        dialog.title("Downloading Update")
        dialog.geometry("450x180")
        dialog.resizable(False, False)
        dialog.transient(parent)
        dialog.grab_set()
        
        # Center the dialog on the parent window
        dialog.geometry("+%d+%d" % (
            parent.winfo_rootx() + parent.winfo_width()//2 - 225,
            parent.winfo_rooty() + parent.winfo_height()//2 - 90
        ))
        
        # Configure dialog appearance
        dialog.configure(bg="#f0f0f0")  # Light gray background
        
        # Create a frame for better layout
        main_frame = tk.Frame(dialog, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        # Dialog title
        tk.Label(
            main_frame, 
            text=f"Downloading update for {APP_NAME}...", 
            font=("Arial", 12, "bold"),
            bg="#f0f0f0"
        ).pack(pady=(5, 15), anchor='w')
        
        # Progress frame
        progress_frame = tk.Frame(main_frame, bg="#f0f0f0")
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Progress bar - using Progressbar from ttk for better appearance
        try:
            from tkinter import ttk
            progress_var = tk.DoubleVar(value=0)
            progress_bar = ttk.Progressbar(
                progress_frame,
                orient="horizontal",
                length=410,
                mode="determinate",
                variable=progress_var
            )
        except ImportError:
            # Fallback to standard Tk widgets if ttk is not available
            progress_var = tk.IntVar(value=0)
            progress_bar = tk.Scale(
                progress_frame, 
                from_=0, to=100, 
                orient=tk.HORIZONTAL, 
                variable=progress_var,
                state=tk.DISABLED,
                length=410,
                showvalue=0,  # Don't show the value on the scale
                sliderlength=10  # Smaller slider
            )
        
        progress_bar.pack(fill=tk.X, pady=5)
        
        # Progress percentage
        percent_label = tk.Label(
            progress_frame, 
            text="0%", 
            font=("Arial", 9),
            bg="#f0f0f0"
        )
        percent_label.pack(anchor='e')
        
        # Status label
        status_label = tk.Label(
            main_frame, 
            text="Initializing download...", 
            font=("Arial", 10),
            bg="#f0f0f0"
        )
        status_label.pack(pady=(5, 15), fill=tk.X)
        
        # Cancel button (optional)
        # We won't implement actual cancellation now, but the button will be there for UI consistency
        button_frame = tk.Frame(main_frame, bg="#f0f0f0")
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        def cancel_operation():
            dialog.destroy()
            
        cancel_btn = tk.Button(
            button_frame,
            text="Cancel",
            command=cancel_operation,
            width=10
        )
        cancel_btn.pack(side=tk.RIGHT)
        
        # Add methods to update the progress dialog
        def update_progress(value):
            progress_var.set(value)
            percent_label.config(text=f"{int(value)}%")
            dialog.update_idletasks()
            
        def update_status(text):
            status_label.config(text=text)
            dialog.update_idletasks()
            
        dialog.update_progress = update_progress
        dialog.update_status = update_status
        
        # Initialize progress display
        update_progress(0)
        update_status("Preparing to download...")
        
        return dialog
        
    def _create_and_show_progress_dialog(self, parent, status_text):
        """Create and show a progress dialog in the main thread"""
        try:
            logger.info("Creating progress dialog in main thread")
            # Create dialog
            dialog = self._create_progress_dialog(parent)
            
            # Initialize progress tracking variables
            self._download_progress = 0
            self._download_total_size = 0
            self._progress_value = 5  # Start at 5%
            
            # Set initial status
            dialog.update_status(status_text)
            dialog.update_progress(5)
            
            # Store as instance variable for later access
            self.progress_dialog = dialog
            
            # Schedule auto-updates
            self._schedule_progress_updates(parent)
            
            logger.info("Progress dialog created and displayed")
            return dialog
        except Exception as e:
            logger.error(f"Error creating progress dialog: {e}")
            return None
            
    def _schedule_progress_updates(self, parent):
        """Schedule progress updates to keep the UI responsive"""
        if not hasattr(self, 'progress_dialog') or not self.progress_dialog:
            return
            
        try:
            if self.progress_dialog.winfo_exists():
                # Use actual download progress if available, otherwise use animated progress
                if hasattr(self, '_download_progress') and self._download_progress > 0:
                    # Use the actual download progress
                    progress = int(self._download_progress)
                    self.progress_dialog.update_progress(progress)
                    
                    # Update status with download info if available
                    if hasattr(self, '_download_total_size') and self._download_total_size > 0:
                        downloaded = (self._download_progress / 100) * self._download_total_size
                        self.progress_dialog.update_status(
                            f"Downloading: {progress}% ({downloaded/(1024*1024):.2f} MB)"
                        )
                else:
                    # Fallback to animated progress when download hasn't started yet
                    progress = getattr(self, '_progress_value', 10)
                    progress = min(progress + 2, 15)  # Increment but cap at 15% for initial stages
                    self._progress_value = progress
                    self.progress_dialog.update_progress(progress)
                
                # Schedule next update
                parent.after(300, lambda: self._schedule_progress_updates(parent))
        except Exception as e:
            logger.error(f"Error updating progress dialog: {e}")
            # Don't reschedule if there's an error
            
    def _update_progress_safe(self, progress_value, status_text=None):
        """Update progress dialog safely from any thread"""
        try:
            if hasattr(self, 'progress_dialog') and self.progress_dialog and self.progress_dialog.winfo_exists():
                self.progress_dialog.update_progress(progress_value)
                if status_text:
                    self.progress_dialog.update_status(status_text)
        except Exception as e:
            logger.error(f"Error in safe progress update: {e}")
        
# Helper function to check for updates at application startup
def check_for_updates_at_startup(app_state=None, parent_window=None, silent=False):
    """Check for updates at application startup"""
    update_manager = UpdateManager(app_state)
    
    # Check if it's time to check for updates
    if not update_manager.should_check_for_updates():
        return False
        
    try:
        # Check for updates
        update_available = update_manager.check_for_updates()
        
        if update_available and not silent:
            # Show update prompt
            should_update = update_manager.prompt_for_update(parent_window)
            
            if should_update:
                # Download and install update
                update_manager.download_and_install_update(parent_window)
        
        return update_available
    except Exception as e:
        logger.error(f"Error checking for updates at startup: {e}")
        return False
        
# Create a background thread to check for updates
def start_background_update_check(app_state=None, parent_window=None):
    """Start a background thread to check for updates"""
    def check_in_background():
        try:
            logger.info("Starting background update check thread")
            # Wait a bit to allow application to fully start
            time.sleep(20)
            
            # Make sure we don't try to update if the app is shutting down
            if app_state and hasattr(app_state, 'running') and not app_state.running:
                logger.info("Application shutting down, cancelling update check")
                return
                
            logger.info("Background update check running")
            
            try:
                # Store a reference to the update manager for later use
                if app_state:
                    app_state._update_manager = UpdateManager(app_state)
                    update_manager = app_state._update_manager
                    logger.info("Created update manager with app state")
                else:
                    update_manager = UpdateManager(app_state)
                    logger.info("Created update manager without app state")
                
                # Check for updates - force update check regardless of last check time
                logger.info("Checking for updates in background (forcing check)")
                update_available = update_manager.check_for_updates(force=True)
                
                if update_available:
                    logger.info(f"Update available: {update_manager.latest_version} (current: {update_manager.current_version})")
                    
                    # Verify parent window still exists before scheduling
                    if parent_window:
                        try:
                            if parent_window.winfo_exists():
                                logger.info("Parent window exists, scheduling update prompt")
                                # Schedule the prompt on the main thread with a small delay
                                parent_window.after(
                                    1000,
                                    lambda: show_update_prompt(update_manager, parent_window)
                                )
                                logger.info("Update prompt scheduled for display in 1 second")
                            else:
                                logger.warning("Parent window no longer exists, can't show update prompt")
                        except Exception as e:
                            logger.error(f"Error checking window existence: {e}")
                else:
                    logger.info("No updates available in background check")
            except Exception as e:
                logger.error(f"Error in background update check process: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                # Log detailed info about the exception for debugging
                if hasattr(e, 'response') and e.response:
                    try:
                        logger.error(f"HTTP Response Status: {e.response.status_code}")
                        logger.error(f"HTTP Response Text: {e.response.text[:500]}")  # First 500 chars of response
                    except:
                        pass
        except Exception as e:
            # Catch-all for the entire thread
            logger.error(f"Unhandled error in background update thread: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
    def show_update_prompt(update_manager, parent_window):
        """Show the update prompt on the main thread"""
        try:
            logger.info("Preparing to show update prompt")
            
            # Make sure parent window exists before proceeding
            if not parent_window:
                logger.warning("No parent window provided, skipping update prompt")
                return
                
            try:
                if not parent_window.winfo_exists():
                    logger.warning("Parent window no longer exists, skipping update prompt")
                    return
            except Exception as e:
                logger.error(f"Error checking window existence: {e}")
                return
                
            # Make sure app is not shutting down
            if app_state and hasattr(app_state, 'running') and not app_state.running:
                logger.info("Application shutting down, skipping update prompt")
                return
                
            # Verify we still have update info before showing prompt
            if not update_manager.update_available or not update_manager.update_info:
                logger.warning("Update info no longer available, skipping update prompt")
                return
                
            # Show update prompt
            logger.info("Showing update prompt to user")
            should_update = update_manager.prompt_for_update(parent_window)
            
            if should_update:
                logger.info("User accepted update, starting download and installation")
                update_manager.download_and_install_update(parent_window)
            else:
                logger.info("User declined the update")
                
        except Exception as e:
            logger.error(f"Error showing update prompt: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Start the background thread
    logger.info("Starting background update check thread")
    thread = Thread(target=check_in_background, name="UpdateCheckThread", daemon=True)
    thread.start()
    return thread  # Return the thread so caller can keep track if needed
