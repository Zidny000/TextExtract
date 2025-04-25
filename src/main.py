import ctypes
import keyboard
import threading
import queue
import os
import sys
import winreg
import socket
from monitor_selector import MonitorSelector
from overlay import ScreenOverlay
from ocr import extract_text_from_area
from config import save_selected_monitor, load_selected_monitor
from visual_control import FloatingIcon
import tkinter as tk
from screeninfo import get_monitors
import pystray
from PIL import Image, ImageDraw
import time
import tkinter.messagebox as messagebox
from threading import Thread
import traceback  # Add traceback for better error reporting
import auth  # Import our auth module

# Add the parent directory to sys.path if running as a script
if __name__ == "__main__" and not getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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
    from src.ui.dialogs.auth_dialog import AuthDialog
    print("Creating separate login window...")
    
    # Create a temporary window specifically for hosting the login dialog
    login_window = tk.Toplevel(parent_window)
    login_window.title("Authentication")
    login_window.geometry("300x200")
    login_window.update_idletasks()
    
    # Center the window
    width = login_window.winfo_width()
    height = login_window.winfo_height()
    x = (login_window.winfo_screenwidth() // 2) - (width // 2)
    y = (login_window.winfo_screenheight() // 2) - (height // 2)
    login_window.geometry(f'{width}x{height}+{x}+{y}')
    
    # Make it visible but keep it minimal
    login_window.attributes('-alpha', 1.0)
    login_window.attributes('-topmost', True)
    login_window.update()
    
    label = tk.Label(login_window, text="Initializing login...")
    label.pack(pady=20)
    
    def start_login():
        # Remove the label
        label.pack_forget()
        
        # Create a progress indicator
        progress_label = tk.Label(login_window, text="Loading authentication dialog...")
        progress_label.pack(pady=20)
        login_window.update()
        
        # Create and show auth dialog using our visible window as parent
        auth_dialog = AuthDialog(login_window, "Welcome to TextExtract")
        result = auth_dialog.show()
        
        # Close the temporary window
        login_window.destroy()
        return result
    
    # Start login after a short delay to ensure window is visible
    return login_window.after(500, start_login)

def main():
    print("\n\n==== STARTING APPLICATION ====")
    print(f"Python version: {sys.version}")
    print(f"Current directory: {os.getcwd()}")
    
    try:
        print("Testing auth module availability...")
        print(f"Auth module imported: {auth is not None}")
        print(f"Is authenticated function exists: {hasattr(auth, 'is_authenticated')}")
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
            authenticated = auth.is_authenticated()
            print(f"Authentication status: {authenticated}")
            
            if authenticated:
                print("User already authenticated, continuing...")
                auth_success = True
                # Destroy splash screen
                splash.destroy()
            else:
                print("User not authenticated, showing login dialog...")
                # Update splash screen
                tk.Label(splash, text="Please login to continue...").pack(pady=10)
                splash.update()
                
                # Close splash after a delay and show login dialog
                def transition_to_login():
                    splash.destroy()
                    # Show the login dialog using our dedicated function
                    login_result = show_login_dialog(root)
                    if login_result:
                        print("Login completed successfully")
                        auth_success = True
                    else:
                        print("Authentication required to use the application. User canceled login.")
                        # Instead of immediately exiting, we'll continue with limited functionality
                        messagebox.showwarning("Limited Functionality", 
                                             "You're continuing without authentication. Some features will be unavailable.")
                
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
            def fetch_profile_thread():
                print("Fetching user profile in background...")
                try:
                    profile, message = auth.get_user_profile()
                    if profile:
                        app_state.user_profile = profile
                        print(f"Logged in as: {profile['user'].get('email', 'Unknown')}")
                        print(f"Remaining requests today: {profile['usage'].get('remaining_requests', 'Unknown')}")
                    else:
                        print(f"Could not fetch profile: {message}")
                except Exception as e:
                    print(f"Error fetching profile: {str(e)}")
                    print(traceback.format_exc())
            
            Thread(target=fetch_profile_thread, daemon=True).start()
        
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
                    elif command == "show_profile":
                        show_profile()
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
        
        def show_profile():
            """Show user profile dialog"""
            print("Showing user profile dialog...")
            
            # Use a separate function for UI operations to ensure thread safety
            def show_profile_ui():
                if not auth.is_authenticated():
                    # Show login dialog
                    from src.ui.dialogs.auth_dialog import AuthDialog
                    login_dialog = AuthDialog(root, "Authentication Required")
                    if not login_dialog.show():
                        return
                
                # Temporarily disable floating icon if visible
                if app_state.floating_icon and app_state.floating_icon.is_visible:
                    app_state.floating_icon.is_responding = False
                
                # Temporarily make root visible to help with focus issues
                root.update_idletasks()
                
                # Show loading indicator
                loading_window = tk.Toplevel(root)
                loading_window.title("Loading")
                loading_window.geometry("250x100")
                loading_window.resizable(False, False)
                loading_window.transient(root)
                
                # Center the window
                loading_window.update_idletasks()
                width = loading_window.winfo_width()
                height = loading_window.winfo_height()
                x = (loading_window.winfo_screenwidth() // 2) - (width // 2)
                y = (loading_window.winfo_screenheight() // 2) - (height // 2)
                loading_window.geometry(f'{width}x{height}+{x}+{y}')
                
                loading_label = tk.Label(loading_window, text="Loading profile data...")
                loading_label.pack(pady=30)
                
                # Define a function to fetch profile data in a separate thread
                def fetch_profile_thread():
                    try:
                        profile, message = auth.get_user_profile()
                        
                        # Schedule UI update in the main thread
                        def update_ui():
                            try:
                                # Close loading window
                                loading_window.destroy()
                                
                                if profile:
                                    app_state.user_profile = profile
                                    # Display the profile dialog
                                    # Import here to avoid circular imports
                                    from src.ui.dialogs.profile_dialog import create_user_profile_dialog
                                    
                                    # First check if there's already a profile dialog open
                                    for widget in root.winfo_children():
                                        if isinstance(widget, tk.Toplevel) and widget.title() == "User Profile":
                                            widget.destroy()
                                    
                                    # Now create and show the profile dialog
                                    profile_dialog = create_user_profile_dialog(
                                        root, 
                                        profile,
                                        on_profile_update=None,
                                        on_logout=lambda: safe_logout()
                                    )
                                    
                                    # Add a special callback when the dialog closes to re-enable floating icon
                                    original_on_close = profile_dialog.on_close
                                    def on_close_with_cleanup():
                                        result = original_on_close()
                                        # Re-enable floating icon
                                        if app_state.floating_icon and app_state.floating_icon.is_visible:
                                            app_state.floating_icon.is_responding = True
                                        return result
                                    
                                    profile_dialog.on_close = on_close_with_cleanup
                                    
                                    # Make sure it's visible and has focus
                                    root.after(100, lambda: profile_dialog.dialog.lift())
                                    root.after(200, lambda: profile_dialog.dialog.focus_force())
                                    
                                    # Check if dialog actually appears
                                    def check_dialog():
                                        if hasattr(profile_dialog, 'dialog') and profile_dialog.dialog.winfo_exists():
                                            print("Profile dialog is visible")
                                        else:
                                            print("Profile dialog failed to appear")
                                            # Re-enable floating icon if dialog failed to appear
                                            if app_state.floating_icon and app_state.floating_icon.is_visible:
                                                app_state.floating_icon.is_responding = True
                                    
                                    root.after(500, check_dialog)
                                else:
                                    messagebox.showerror("Error", f"Could not fetch user profile: {message}")
                                    # Re-enable floating icon
                                    if app_state.floating_icon and app_state.floating_icon.is_visible:
                                        app_state.floating_icon.is_responding = True
                            except Exception as e:
                                print(f"Error in update_ui: {e}")
                                print(traceback.format_exc())
                                messagebox.showerror("Error", f"An error occurred: {str(e)}")
                                # Re-enable floating icon
                                if app_state.floating_icon and app_state.floating_icon.is_visible:
                                    app_state.floating_icon.is_responding = True
                    
                        root.after(0, update_ui)
                    except Exception as e:
                        print(f"Error fetching profile: {e}")
                        print(traceback.format_exc())
                        
                        def show_error():
                            try:
                                loading_window.destroy()
                            except:
                                pass
                            messagebox.showerror("Error", f"An error occurred: {str(e)}")
                            # Re-enable floating icon
                            if app_state.floating_icon and app_state.floating_icon.is_visible:
                                app_state.floating_icon.is_responding = True
                    
                        root.after(0, show_error)
                
                # Start profile fetching in background thread
                Thread(target=fetch_profile_thread, daemon=True).start()
            
            # Ensure UI operations run in the main thread
            if threading.current_thread() is threading.main_thread():
                show_profile_ui()
            else:
                root.after(0, show_profile_ui)
        
        def logout_user():
            """Logout the current user"""
            print("Processing logout request...")
            
            # Use a separate function for UI operations to ensure thread safety
            def logout_ui():
                # Confirm logout
                if messagebox.askyesno("Confirm Logout", "Are you sure you want to logout?"):
                    # Perform logout in a separate thread
                    def logout_thread():
                        try:
                            success, message = auth.logout()
                            
                            # Schedule UI update in main thread
                            def update_ui():
                                if success:
                                    # Show login dialog
                                    from src.ui.dialogs.auth_dialog import AuthDialog
                                    login_dialog = AuthDialog(root, "Login Required")
                                    if not login_dialog.show():
                                        # User canceled login, exit the app
                                        exit_application()
                                    else:
                                        # User logged in, refresh profile
                                        Thread(target=fetch_profile_thread, daemon=True).start()
                        except Exception as e:
                            print(f"Error during logout: {e}")
                            print(traceback.format_exc())
                            
                            def show_error():
                                messagebox.showerror("Error", f"An error occurred during logout: {str(e)}")
                            
                            root.after(0, show_error)
                    
                    # Start logout process in background thread
                    Thread(target=logout_thread, daemon=True).start()
            
            # Ensure UI operations run in the main thread
            if threading.current_thread() is threading.main_thread():
                logout_ui()
            else:
                root.after(0, logout_ui)

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
        
        def safe_change_monitor():
            root.after(0, lambda: app_state.command_queue.put(("change_monitor", None)))
        
        def safe_toggle_floating_icon():
            root.after(0, lambda: app_state.command_queue.put(("toggle_floating_icon", None)))
        
        def safe_show_profile():
            # Execute in the main thread using after() to avoid freezing
            root.after(0, lambda: app_state.command_queue.put(("show_profile", None)))
        
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
                app_state.floating_icon = FloatingIcon(
                    capture_callback=safe_capture,
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
                # Add a default menu item that will be triggered on left-click
                pystray.MenuItem('Show Control Panel', lambda: safe_toggle_floating_icon(), default=True),
                pystray.MenuItem('Capture Text (Ctrl+Alt+C)', lambda: safe_capture()),
                pystray.MenuItem('Select Monitor (Ctrl+Alt+M)', lambda: safe_change_monitor()),
                pystray.MenuItem('Show Control Panel (Ctrl+Alt+V)', lambda: safe_toggle_floating_icon()),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem('My Profile', lambda: safe_show_profile()),
                pystray.MenuItem('Logout', lambda: safe_logout()),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(f'About {APP_NAME} v{__version__}', lambda: show_about_dialog()),
                pystray.MenuItem('Exit', lambda: safe_exit())
            )
            
            # Create the tray icon
            app_state.tray_icon = pystray.Icon("TextExtract", icon_image, f"{APP_NAME} v{__version__}", menu)
            
            # Run the tray icon in a separate thread
            tray_thread = threading.Thread(target=lambda: app_state.tray_icon.run(), daemon=True)
            tray_thread.start()
            
            print("System tray icon created")

        def show_about_dialog():
            """Show an about dialog with version information"""
            about_window = tk.Toplevel(root)
            about_window.title(f"About {APP_NAME}")
            about_window.geometry("300x200")
            about_window.resizable(False, False)
            about_window.attributes('-topmost', True)
            
            # Try to set the icon
            try:
                if getattr(sys, 'frozen', False):
                    icon_path = os.path.join(os.path.dirname(sys.executable), 'assets', 'icon.ico')
                else:
                    icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'icon.ico')
                
                if os.path.exists(icon_path):
                    about_window.iconbitmap(icon_path)
            except:
                pass  # Ignore icon errors
            
            # Add version information
            tk.Label(about_window, text=f"{APP_NAME}", font=("Arial", 14, "bold")).pack(pady=(20, 5))
            tk.Label(about_window, text=f"Version {__version__}").pack(pady=5)
            tk.Label(about_window, text="Screen Text Extraction Tool").pack(pady=5)
            
            # Copyright information
            try:
                from version import __copyright__
                copyright_text = __copyright__
            except ImportError:
                copyright_text = f"© 2023-2024 {APP_NAME}"
            
            tk.Label(about_window, text=copyright_text, font=("Arial", 8)).pack(pady=(20, 5))
            
            # Close button
            tk.Button(about_window, text="OK", command=about_window.destroy, width=10).pack(pady=10)
            
            # Center the window
            about_window.update_idletasks()
            width = about_window.winfo_width()
            height = about_window.winfo_height()
            x = (about_window.winfo_screenwidth() // 2) - (width // 2)
            y = (about_window.winfo_screenheight() // 2) - (height // 2)
            about_window.geometry(f'{width}x{height}+{x}+{y}')

        # Register hotkeys with thread-safe callbacks
        keyboard.add_hotkey('ctrl+alt+c', safe_capture)
        keyboard.add_hotkey('ctrl+alt+m', safe_change_monitor)
        keyboard.add_hotkey('ctrl+alt+v', safe_toggle_floating_icon)

        # Create the initial floating icon
        create_floating_icon()
        
        # Setup the system tray icon
        setup_tray_icon()
        
        # Start the command processor
        process_commands()
        
        # Start the Tkinter main loop - this blocks until the application exits
        root.mainloop()
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        print(traceback.format_exc())
        with open("error_log.txt", "w") as f:
            f.write(f"Error: {str(e)}\n")
            f.write(traceback.format_exc())
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()