# filepath: d:\Work\Personal\textextract\src\main.py
import ctypes
import keyboard
import threading
import queue
import os
import sys
import winreg
import socket
import traceback
import tkinter as tk
from screeninfo import get_monitors
import pystray
from PIL import Image, ImageDraw
import time
import tkinter.messagebox as messagebox
from threading import Thread
import logging
from src.monitor_selector import MonitorSelector
from src.overlay           import ScreenOverlay
from src.ocr               import extract_text_from_area
from src.config            import save_selected_monitor, load_selected_monitor
from src.visual_control    import FloatingIcon
from src.auth              import (
    is_authenticated, refresh_token,
    logout, open_browser_url, get_user_profile
)

logger = logging.getLogger(__name__)

# Import version information
try:
    from version import __version__, APP_NAME, REGISTRY_PATH
except ImportError:
    __version__ = "1.0.0"
    APP_NAME = "TextExtract"
    REGISTRY_PATH = r"Software\TextExtract"

# Enable DPI awareness
ctypes.windll.shcore.SetProcessDpiAwareness(2)

class AppState:
    def __init__(self):
        print("Initializing AppState")
        self.selected_monitor = load_selected_monitor()
        self.floating_icon = None
        self.tray_icon = None
        self.running = True
        self.command_queue = queue.Queue()
        self.register_app_in_registry()
        self.user_profile = None
        self.refreshing_token = False
        
    def register_app_in_registry(self):
        """Register the application in the Windows Registry for proper installation detection"""
        try:
            # Only register if running as a frozen executable (installed version)
            if getattr(sys, 'frozen', False):
                # Get the path to the executable
                app_path = sys.executable
                app_dir = os.path.dirname(app_path)
                
                # Create or open the registry key
                try:
                    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH)
                    
                    # Set registry values
                    winreg.SetValueEx(key, "InstallPath", 0, winreg.REG_SZ, app_dir)
                    winreg.SetValueEx(key, "Version", 0, winreg.REG_SZ, __version__)
                    winreg.SetValueEx(key, "ExecutablePath", 0, winreg.REG_SZ, app_path)
                    
                    # Set last run time
                    winreg.SetValueEx(key, "LastRun", 0, winreg.REG_SZ, time.strftime("%Y-%m-%d %H:%M:%S"))
                    
                    # Close the key
                    winreg.CloseKey(key)
                    print(f"{APP_NAME} registered in Windows Registry")
                except Exception as e:
                    print(f"Error writing to registry: {e}")
            else:
                print("Not registering in registry (not running as frozen executable)")
        except Exception as e:
            print(f"Registry registration error: {e}")
            # Proceed anyway, this is not critical

def create_tray_icon_image(width, height, color1, color2):
    # Create a simple icon image
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    
    # Draw a "T" for TextExtract
    dc.rectangle([(width//4, height//4), (3*width//4, height//4 + height//10)], fill=color2)  # Top of T
    dc.rectangle([(width//2 - width//10, height//4), (width//2 + width//10, 3*height//4)], fill=color2)  # Stem of T
    
    return image

# Function to ensure only one instance of the application is running
def ensure_single_instance():
    try:
        # Try to create a socket on a specific port
        single_instance_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        single_instance_socket.bind(('localhost', 47809))  # Use a unique port number
        single_instance_socket.listen(1)
        return True, single_instance_socket
    except socket.error:
        print("Another instance of TextExtract is already running")
        return False, None

def show_login_dialog(parent_window):
    """Show a login dialog and return True if login is successful"""
    from src.ui.dialogs.auth_modal import create_auth_modal
    print("Creating web-based authentication modal...")
    
    try:
        # Make sure parent window exists and is valid
        if parent_window is None or not parent_window.winfo_exists():
            print("Invalid parent window provided to show_login_dialog")
            return False
            
        # Ensure the parent is visible while creating the dialog
        was_withdrawn = parent_window.state() == 'withdrawn'
        if was_withdrawn:
            parent_window.deiconify()
            parent_window.update()
            
        # Create the auth modal directly using the parent window
        auth_modal = create_auth_modal(parent_window, "Welcome to TextExtract")
        
        # Show the modal
        if auth_modal:
            result = auth_modal.show()
            
            # Restore parent state if needed
            if was_withdrawn:
                parent_window.withdraw()
                
            return result
        else:
            print("Failed to create auth modal")
            
            # Restore parent state if needed
            if was_withdrawn:
                parent_window.withdraw()
                
            return False
        
    except Exception as e:
        print(f"Error showing login dialog: {e}")
        print(traceback.format_exc())
        
        # Restore parent state if needed
        if was_withdrawn:
            parent_window.withdraw()
            
        return False

# Function to fetch user profile that can be used anywhere
def fetch_profile_thread(app_state, root=None):
    print("Fetching user profile in background...")
    try:
        profile, message = get_user_profile(root)
        if profile:
            app_state.user_profile = profile
            print(f"Logged in as: {profile['user'].get('email', 'Unknown')}")
            print(f"Remaining requests today: {profile['usage'].get('remaining_requests', 'Unknown')}")
        else:
            print(f"Could not fetch profile: {message}")
    except Exception as e:
        print(f"Error fetching profile: {str(e)}")
        print(traceback.format_exc())

def main():
    print("\n\n==== STARTING APPLICATION ====")
    print(f"Python version: {sys.version}")
    print(f"Current directory: {os.getcwd()}")
    
    try:
        print("Testing auth module availability...")
    except Exception as e:
        print(f"Auth module test error: {e}")
    
    try:
        # Check for single instance
        print("Checking for single instance...")
        can_run, single_instance_socket = ensure_single_instance()
        if not can_run:
            print("Another instance is already running, exiting.")
            return

        # Create root window
        print("Creating Tkinter root window...")
        root = tk.Tk()
        
        # Initialize thread manager
        from src.utils.threading.thread_manager import init_thread_manager
        init_thread_manager(root)
        print("Thread manager initialized")
        
        # Create a simple splash screen
        splash = tk.Toplevel(root)
        splash.title("Starting TextExtract")
        splash.geometry("400x200")
        splash.attributes('-topmost', True)
        
        # Center the splash screen
        splash.update_idletasks()
        width = splash.winfo_width()
        height = splash.winfo_height()
        x = (splash.winfo_screenwidth() // 2) - (width // 2)
        y = (splash.winfo_screenheight() // 2) - (height // 2)
        splash.geometry(f'{width}x{height}+{x}+{y}')
        
        # Add content to splash screen
        tk.Label(splash, text="TextExtract", font=("Arial", 18, "bold")).pack(pady=(20, 5))
        tk.Label(splash, text="Initializing application...").pack(pady=5)
        
        # Update the splash screen
        splash.update()
        
        # Hide the root window
        root.withdraw()
        
        # Authentication variables 
        auth_required = True
        auth_success = False

        # Check if user is authenticated
        print("Checking if user is authenticated...")
        try:
            authenticated = is_authenticated()
            print(f"Authentication status: {authenticated}")
            
            if authenticated:
                print("User already authenticated, continuing...")
                auth_success = True
                # Destroy splash screen
                splash.destroy()
            else:
                print("User not authenticated, showing login modal...")
                # Update splash screen
                tk.Label(splash, text="Please login to continue...").pack(pady=10)
                splash.update()
                
                # Close splash after a delay and show login modal
                def transition_to_login():
                    try:
                        print("Transitioning to login screen...")
                        # Destroy splash carefully
                        try:
                            if splash and splash.winfo_exists():
                                splash.destroy()
                        except Exception as splash_e:
                            print(f"Error destroying splash: {splash_e}")
                        
                        # Show the login modal using our dedicated function
                        print("Showing login dialog...")
                        # Make sure root is visible temporarily to ensure proper dialog parenting
                        root_was_withdrawn = root.state() == 'withdrawn'
                        if root_was_withdrawn:
                            root.deiconify()
                            root.update()
                        
                        login_result = show_login_dialog(root)
                        
                        # Restore root state if needed
                        if root_was_withdrawn:
                            root.withdraw()
                        
                        if login_result:
                            print("Login completed successfully")
                            auth_success = True
                            # Update UI to reflect successful login
                            root.after(0, lambda: update_after_login_success())
                        else:
                            print("Authentication required to use the application. User canceled login.")
                            # Instead of immediately exiting, we'll continue with limited functionality
                            messagebox.showwarning("Limited Functionality", 
                                                 "You're continuing without authentication. Some features will be unavailable.")
                    except Exception as e:
                        print(f"Error in transition_to_login: {e}")
                        print(traceback.format_exc())
                        messagebox.showerror("Error", f"Failed to show login screen: {str(e)}")
                
                # Function to update UI after successful login
                def update_after_login_success():
                    try:
                        # Fetch user profile after successful login
                        Thread(target=lambda: fetch_profile_thread(app_state, root), daemon=True).start()
                    except Exception as e:
                        print(f"Error updating after login: {e}")
                
                # Schedule the transition
                root.after(1500, transition_to_login)
        except Exception as e:
            print(f"Authentication error: {e}")
            print(traceback.format_exc())
            
            # Destroy splash screen
            splash.destroy()
            
            # Ask the user if they want to continue despite the authentication error
            result = messagebox.askyesno("Authentication Error", 
                                        f"Could not connect to the authentication service: {str(e)}\n\n"
                                        "Do you want to continue with limited functionality?")
            if not result:
                print("User chose to exit after authentication error")
                root.destroy()
                return
            
            # User chose to continue without authentication
            auth_required = False
            print("Continuing with limited functionality (no authentication)")

        # Initialize application state
        print("Initializing application state...")
        app_state = AppState()
        
        # Fetch user profile in the background only if authenticated
        if auth_success:
            Thread(target=lambda: fetch_profile_thread(app_state, root), daemon=True).start()
        
        print(f"{APP_NAME} v{__version__} started")
        print("- Ctrl+Alt+C: Capture from last selected monitor")
        print("- Ctrl+Alt+M: Change monitor selection")
        print("- Ctrl+Alt+V: Show visual control icon")
        print("- Floating icon available for visual control")
        print("- System tray icon available in the notification area")

        # Command processor for handling UI actions in the main thread
        def process_commands():
            try:
                while not app_state.command_queue.empty():
                    command, args = app_state.command_queue.get_nowait()
                    if command == "capture":
                        capture_from_selected_monitor()
                    elif command == "change_monitor":
                        change_monitor_selection()
                    elif command == "change_monitor_by_index":
                        change_monitor_by_index(args[0])
                    elif command == "toggle_floating_icon":
                        toggle_floating_icon()
                    elif command == "open_profile_browser":
                        open_profile_in_browser()
                    elif command == "logout":
                        logout_user()
                    elif command == "exit":
                        exit_application()
                    app_state.command_queue.task_done()
            except queue.Empty:
                pass
            
            # Schedule the next command processing if still running
            if app_state.running:
                root.after(100, process_commands)

        def capture_from_selected_monitor():
            if not app_state.selected_monitor:
                print("No monitor selected. Press Ctrl+Alt+M to select one.")
                return

            # Check if user is authenticated
            if auth_required and not is_authenticated():
                print("Not authenticated, showing login modal")
                
                # Ensure the root window is temporarily visible to properly show dialogs
                root_was_withdrawn = root.state() == 'withdrawn'
                if root_was_withdrawn:
                    print("Making root window temporarily visible for dialog")
                    root.deiconify()
                    root.update_idletasks()
                    
                # Show login dialog using our dedicated function
                print("Showing login dialog...")
                login_result = show_login_dialog(root)
                
                # Restore root state if needed
                if root_was_withdrawn:
                    root.withdraw()
                
                if not login_result:
                    print("User canceled login")
                    return

            # Temporarily make root visible to help with focus issues
            root.update_idletasks()
            
            overlay = ScreenOverlay(app_state.selected_monitor, root)
            overlay.start()

            x1, y1, x2, y2 = overlay.get_selection_coordinates()
            if x1 is None:  # User canceled
                return
            
            extracted_text = extract_text_from_area(x1, y1, x2, y2, root)
            if extracted_text:
                print(f"Extracted Text:\n{extracted_text}")
            else:
                print("No text found.")

        def change_monitor_selection():
            # Temporarily make root visible to help with focus issues
            root.update_idletasks()
            
            selector = MonitorSelector(root)  # Pass root as the parent
            new_monitor = selector.start()
            if new_monitor:
                app_state.selected_monitor = new_monitor
                save_selected_monitor(new_monitor)
                print(f"Monitor changed to: {new_monitor.width}x{new_monitor.height}")

        def change_monitor_by_index(monitor_index):
            monitors = get_monitors()
            if 0 <= monitor_index < len(monitors):
                app_state.selected_monitor = monitors[monitor_index]
                save_selected_monitor(app_state.selected_monitor)
                print(f"Monitor changed to: {app_state.selected_monitor.width}x{app_state.selected_monitor.height}")

        def get_selected_monitor():
            return app_state.selected_monitor
        
        
        def open_profile_in_browser():
            """Open the user profile in the web browser"""
            print("Opening profile page in web browser...")
            try:
                # Use the auth module's function to open the browser URL
                open_browser_url("http://localhost:3000/profile")
            except Exception as e:
                print(f"Error opening profile in browser: {e}")
                print(traceback.format_exc())
                messagebox.showerror("Error", f"Failed to open profile page: {str(e)}")
        
        def logout_user():
            """Safely logout the user"""
            try:
                success, message = logout()
                if success:
                    app_state.user_profile = None
                    app_state.is_authenticated = False
                    messagebox.showinfo("Logout", "You have been logged out successfully")
                else:
                    messagebox.showerror("Error", f"Failed to logout: {message}")
            except Exception as e:
                logger.error(f"Error during logout: {e}")
                messagebox.showerror("Error", f"An error occurred during logout: {str(e)}")

        def exit_application():
            print("Exiting application...")
            app_state.running = False
            
            # Unhook all keyboard listeners
            keyboard.unhook_all()
            
            # Stop the tray icon if it exists
            if app_state.tray_icon:
                try:
                    app_state.tray_icon.stop()
                except Exception as e:
                    print(f"Error stopping tray icon: {e}")
            
            # Safely destroy any remaining UI elements
            if app_state.floating_icon and app_state.floating_icon.is_visible:
                try:
                    app_state.floating_icon.hide_window()
                except Exception as e:
                    print(f"Error hiding floating icon: {e}")
            
            # Update registry with last run time if installed version
            try:
                if getattr(sys, 'frozen', False):
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_WRITE)
                    winreg.SetValueEx(key, "LastRun", 0, winreg.REG_SZ, time.strftime("%Y-%m-%d %H:%M:%S"))
                    winreg.CloseKey(key)
            except Exception as e:
                print(f"Registry update error: {e}")
            
            # Close single instance socket
            if single_instance_socket:
                try:
                    single_instance_socket.close()
                except Exception as e:
                    print(f"Error closing socket: {e}")
            
            # Schedule the actual quit to happen after all pending events are processed
            root.after(100, root.quit)

        # Thread-safe versions of commands
        def safe_capture():
            root.after(0, lambda: app_state.command_queue.put(("capture", None)))
        
        def safe_toggle_floating_icon():
            root.after(0, lambda: app_state.command_queue.put(("toggle_floating_icon", None)))

        def safe_open_profile_in_browser():
            # Execute in the main thread using after() to avoid freezing
            root.after(0, lambda: app_state.command_queue.put(("open_profile_browser", None)))
        
        def safe_logout():
            # Execute in the main thread using after() to avoid freezing
            root.after(0, lambda: app_state.command_queue.put(("logout", None)))
        
        def safe_exit():
            root.after(0, lambda: app_state.command_queue.put(("exit", None)))
        
        def safe_change_monitor_by_index(idx):
            root.after(0, lambda: app_state.command_queue.put(("change_monitor_by_index", [idx])))

        # Function to toggle the floating icon visibility
        def toggle_floating_icon():
            if app_state.floating_icon:
                if app_state.floating_icon.is_visible:
                    print("Visual control icon is already visible")
                else:
                    app_state.floating_icon.show_window()
                    print("Visual control icon shown")
            else:
                # Create the floating icon if it doesn't exist
                create_floating_icon()

        # Function to create the floating icon
        def create_floating_icon():
            if not app_state.floating_icon:
                # Create capture callback that checks authentication first
                def authenticated_capture():
                    if auth_required and not is_authenticated():
                        print("Not authenticated, showing login modal")
                        
                        # Ensure the root window is temporarily visible to properly show dialogs
                        root_was_withdrawn = root.state() == 'withdrawn'
                        if root_was_withdrawn:
                            print("Making root window temporarily visible for dialog")
                            root.deiconify()
                            root.update_idletasks()
                            
                        # Show login dialog using our dedicated function
                        print("Showing login dialog...")
                        login_result = show_login_dialog(root)
                        
                        # Restore root state if needed
                        if root_was_withdrawn:
                            root.withdraw()
                        
                        if not login_result:
                            print("User canceled login")
                            return
                        
                    # Proceed with capture
                    safe_capture()
                
                app_state.floating_icon = FloatingIcon(
                    capture_callback=authenticated_capture,
                    monitor_select_callback=safe_change_monitor_by_index,
                    get_selected_monitor=get_selected_monitor,
                    master=root  # Pass root as parent
                )
                print("Visual control icon created")
                app_state.floating_icon.create_window()

        # Create system tray icon
        def setup_tray_icon():
            # Try to load the icon from assets, or create a simple one if not found
            try:
                # Check if we're running as a frozen executable
                if getattr(sys, 'frozen', False):
                    # If frozen (PyInstaller), use the path relative to the executable
                    base_path = os.path.dirname(sys.executable)
                    icon_path = os.path.join(base_path, 'assets', 'icon.ico')
                else:
                    # If running from source, use the relative path
                    icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'icon.ico')
                
                print(f"Looking for icon at: {icon_path}")
                if os.path.exists(icon_path):
                    icon_image = Image.open(icon_path)
                    print("Successfully loaded icon from file")
                else:
                    print(f"Icon not found at {icon_path}, creating default icon")
                    # Create a simple icon if the icon file is not found
                    icon_image = create_tray_icon_image(64, 64, (60, 60, 60), (200, 200, 200))
            except Exception as e:
                print(f"Error loading icon: {e}")
                # Fallback to a simple icon
                icon_image = create_tray_icon_image(64, 64, (60, 60, 60), (200, 200, 200))
            
            # Create menu items for the tray icon
            menu = (
                pystray.MenuItem('Profile', lambda: safe_open_profile_in_browser()),
                pystray.MenuItem('Capture (Ctrl+Alt+C)', lambda: safe_capture()),
                pystray.MenuItem('Floating UI (Ctrl+Alt+V)', lambda: safe_toggle_floating_icon(), default=True ),
                pystray.MenuItem('Logout', lambda: safe_logout()),
                pystray.MenuItem('Exit', lambda: safe_exit())
            )
              # Create the tray icon with click handler to toggle floating icon
            app_state.tray_icon = pystray.Icon(
                "TextExtract", 
                icon_image, 
                f"{APP_NAME} v{__version__}", 
                menu,
            )
            
            # Run the tray icon in a separate thread
            tray_thread = threading.Thread(target=lambda: app_state.tray_icon.run(), daemon=True)
            tray_thread.start()
            
            print("System tray icon created")


        # Register hotkeys with thread-safe callbacks
        keyboard.add_hotkey('ctrl+alt+c', safe_capture)
        keyboard.add_hotkey('ctrl+alt+v', safe_toggle_floating_icon)

        # Create the initial floating icon
        create_floating_icon()
        
        # Setup the system tray icon
        setup_tray_icon()
        
        # Set up authentication checker to periodically verify token
        def check_auth_status():
            if is_authenticated():
                # Check profile every few minutes to catch token expiration
                try:
                    # Skip if already refreshing or if auth dialog is open
                    try:
                        # Don't refresh if we're already showing an auth dialog
                        if app_state.refreshing_token:
                            return
                        app_state.refreshing_token = True
                        
                        # Start token refresh
                        threading.Thread(
                            target=lambda: (
                                refresh_token(),
                                setattr(app_state, 'refreshing_token', False)
                            )
                        ).start()
                    except Exception as e:
                        print(f"Error refreshing token: {e}")
                        app_state.refreshing_token = False
                except Exception as e:
                    print(f"Error checking auth status: {e}")
                
            # Schedule the next check (every 5 minutes)
            if app_state.running:
                root.after(300000, check_auth_status)  # 5 minutes
                
        # Start auth checker after a delay
        if auth_success:
            root.after(60000, check_auth_status)  # Start after 1 minute
                
        # Start command processor
        root.after(100, process_commands)
        
        # Hide root window
        root.withdraw()
        
        # Hide from taskbar
        root.wm_attributes("-alpha", 0)
        
        # Enter Tkinter main loop
        root.mainloop()
        
        # Application has exited, clean up
        print("Application exiting, cleaning up...")
        app_state.running = False
        if app_state.floating_icon:
            app_state.floating_icon.destroy()
        if app_state.tray_icon:
            app_state.tray_icon.stop()
        if single_instance_socket:
            single_instance_socket.close()
        print("Cleanup complete. Goodbye!")
        
    except Exception as e:
        print(f"Critical error: {e}")
        print(traceback.format_exc())
        messagebox.showerror("Error", f"A critical error occurred:\n\n{str(e)}")
        
    return

if __name__ == "__main__":
    main()