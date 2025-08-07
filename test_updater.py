"""
Simple test script for the updater module
"""
import tkinter as tk
import time
from src.updater import UpdateManager

def main():
    # Create a simple tkinter window
    root = tk.Tk()
    root.title("Update Test")
    root.geometry("300x200")
    
    # Create a button to trigger the update
    def trigger_update():
        print("Triggering update check...")
        update_manager = UpdateManager()
        update_manager.check_for_updates(force=True)
        
        # Simulate update available
        update_manager.update_available = True
        update_manager.latest_version = "1.1.0"
        update_manager.download_url = "https://example.com/update.exe"
        update_manager.update_info = {
            "version": "1.1.0",
            "release_notes": "Test release",
            "silent_install": True
        }
        
        # Show update prompt
        should_update = update_manager.prompt_for_update(root)
        if should_update:
            print("Starting update download...")
            update_manager.download_and_install_update(root)
            
    tk.Button(root, text="Check for Updates", command=trigger_update).pack(pady=50)
    
    # Start the main loop
    root.mainloop()

if __name__ == "__main__":
    main()
