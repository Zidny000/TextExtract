import tkinter as tk
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# Import the auth module
from auth import AuthDialog

def main():
    print("Creating test window...")
    root = tk.Tk()
    root.geometry("300x200")
    root.title("Auth Test")
    
    # Add a button to show the login dialog
    def show_login_dialog():
        print("Showing login dialog...")
        dialog = AuthDialog(root, "Login Test")
        result = dialog.show()
        print(f"Login result: {result}")
        status_label.config(text=f"Login result: {result}")
    
    button = tk.Button(root, text="Show Login Dialog", command=show_login_dialog)
    button.pack(pady=20)
    
    status_label = tk.Label(root, text="No login attempted")
    status_label.pack(pady=10)
    
    # Start the test
    root.after(500, show_login_dialog)  # Show dialog after window appears
    
    # Start the main loop
    print("Starting main loop...")
    root.mainloop()

if __name__ == "__main__":
    main() 