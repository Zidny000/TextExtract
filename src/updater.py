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
            response = requests.get(full_update_url, params=query_params, timeout=10)
            response.raise_for_status()
            
            update_info = response.json()
            print(update_info)
            self.latest_version = update_info.get("version")
            
            # Update the last check time
            self._set_last_check_time()
            
            # Compare versions
            if self._is_newer_version(self.latest_version, self.current_version):
                self.update_info = update_info
                self.download_url = update_info.get("download_url")
                self.update_available = True
                logger.info(f"Update available: {self.latest_version} (current: {self.current_version})")
                return True
            else:
                logger.info(f"No updates available. Current version: {self.current_version}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
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
        return result
    
    def download_and_install_update(self, parent_window=None, show_progress=True):
        """Download and install the latest update"""
        if not self.download_url:
            logger.error("No download URL available")
            return False
            
        if self.update_in_progress:
            logger.info("Update already in progress")
            return False
            
        self.update_in_progress = True
        
        # Start update in a background thread
        self.update_thread = Thread(
            target=self._perform_update_process,
            args=(parent_window, show_progress),
            daemon=True
        )
        self.update_thread.start()
        return True
    
    def _perform_update_process(self, parent_window=None, show_progress=True):
        """Perform the actual update process in a background thread"""
        try:
            # Create progress dialog if requested
            if show_progress and parent_window:
                progress_dialog = self._create_progress_dialog(parent_window)
                progress_dialog.update()
            else:
                progress_dialog = None
                
            # Create a temporary directory for the download
            with tempfile.TemporaryDirectory() as temp_dir:
                # Update progress
                if progress_dialog:
                    progress_dialog.update_status("Downloading update...")
                    progress_dialog.update_progress(10)
                
                # Download the update file
                installer_path = os.path.join(temp_dir, f"{APP_NAME}_Setup.exe")
                self._download_file(self.download_url, installer_path)
                
                # Update progress
                if progress_dialog:
                    progress_dialog.update_status("Download complete. Preparing to install...")
                    progress_dialog.update_progress(50)
                
                # Execute the installer
                # Before running installer, close the progress dialog and the application
                if progress_dialog:
                    progress_dialog.update_status("Starting installation...")
                    progress_dialog.update_progress(75)
                    time.sleep(1)  # Give user a moment to see the message
                    progress_dialog.destroy()
                
                # Get the current executable path to restart after update
                if getattr(sys, 'frozen', False):
                    app_path = sys.executable
                else:
                    app_path = None
                
                # Run the installer
                # Use silent installation if available
                silent_args = "/SILENT" if self.update_info.get("silent_install", False) else ""
                cmd = f'"{installer_path}" {silent_args}'
                
                # Launch installer and exit current instance
                if parent_window:
                    parent_window.destroy()
                
                subprocess.Popen(cmd, shell=True)
                
                # Exit the application to allow the update to proceed
                sys.exit(0)
                
        except Exception as e:
            logger.error(f"Error during update process: {e}")
            self.update_in_progress = False
            
            if progress_dialog and progress_dialog.winfo_exists():
                progress_dialog.destroy()
                
            messagebox.showerror(
                "Update Error", 
                f"An error occurred during the update process:\n{str(e)}",
                parent=parent_window
            )
    
    def _download_file(self, url, destination):
        """Download a file from the given URL to the destination path"""
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return True
        except Exception as e:
            logger.error(f"Error downloading update: {e}")
            raise
    
    def _create_progress_dialog(self, parent):
        """Create a progress dialog for the update process"""
        dialog = tk.Toplevel(parent)
        dialog.title("Downloading Update")
        dialog.geometry("400x150")
        dialog.resizable(False, False)
        dialog.transient(parent)
        dialog.grab_set()
        
        # Center the dialog on the parent window
        dialog.geometry("+%d+%d" % (
            parent.winfo_rootx() + parent.winfo_width()//2 - 200,
            parent.winfo_rooty() + parent.winfo_height()//2 - 75
        ))
        
        # Dialog content
        tk.Label(dialog, text=f"Downloading update for {APP_NAME}...", font=("Arial", 12)).pack(pady=(20, 10))
        
        # Status label
        status_label = tk.Label(dialog, text="Initializing...", font=("Arial", 10))
        status_label.pack(pady=(0, 10))
        
        # Progress bar
        progress_var = tk.IntVar(value=0)
        progress_bar = tk.Scale(
            dialog, 
            from_=0, to=100, 
            orient=tk.HORIZONTAL, 
            variable=progress_var,
            state=tk.DISABLED,
            length=350
        )
        progress_bar.pack(pady=(0, 20), padx=25)
        
        # Add methods to update the progress dialog
        def update_progress(value):
            progress_var.set(value)
            dialog.update_idletasks()
            
        def update_status(text):
            status_label.config(text=text)
            dialog.update_idletasks()
            
        dialog.update_progress = update_progress
        dialog.update_status = update_status
        
        return dialog
        
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
        # Wait a bit to allow application to fully start
        time.sleep(20)
        
        try:
            update_manager = UpdateManager(app_state)
            update_available = update_manager.check_for_updates()
            
            if update_available and parent_window and parent_window.winfo_exists():
                # Schedule the prompt on the main thread
                parent_window.after(
                    1000,
                    lambda: show_update_prompt(update_manager, parent_window)
                )
        except Exception as e:
            logger.error(f"Error in background update check: {e}")
            
    def show_update_prompt(update_manager, parent_window):
        """Show the update prompt on the main thread"""
        try:
            if parent_window and parent_window.winfo_exists():
                should_update = update_manager.prompt_for_update(parent_window)
                
                if should_update:
                    update_manager.download_and_install_update(parent_window)
        except Exception as e:
            logger.error(f"Error showing update prompt: {e}")
    
    # Start the background thread
    thread = Thread(target=check_in_background, daemon=True)
    thread.start()
