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
from config import save_selected_monitor, load_selected_monitor, check_google_vision_credentials
from visual_control import FloatingIcon
import tkinter as tk
from screeninfo import get_monitors
import pystray
from PIL import Image, ImageDraw
import time
import tkinter.messagebox as messagebox
from threading import Thread

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
        self.selected_monitor = load_selected_monitor()
        self.floating_icon = None
        self.tray_icon = None
        self.running = True
        self.command_queue = queue.Queue()
        self.register_app_in_registry()
        
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

def check_vision_api_credentials():
    """Check if Google Vision API credentials are properly set."""
    if not check_google_vision_credentials():
        messagebox.showerror(
            "API Credentials Error",
            "Google Vision API credentials are not properly configured. Please contact the application provider for support."
        )
        return False
    return True

def main():
    # Check for single instance
    can_run, single_instance_socket = ensure_single_instance()
    if not can_run:
        return

    # Create root window
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    
    # Check Google Vision API credentials
    if not check_vision_api_credentials():
        root.destroy()
        return

    # Initialize application state
    app_state = AppState()
    
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
        
        extracted_text = extract_text_from_area(x1, y1, x2, y2)
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
        app_state.command_queue.put(("capture", None))
    
    def safe_change_monitor():
        app_state.command_queue.put(("change_monitor", None))
    
    def safe_toggle_floating_icon():
        app_state.command_queue.put(("toggle_floating_icon", None))
    
    def safe_exit():
        app_state.command_queue.put(("exit", None))
    
    def safe_change_monitor_by_index(idx):
        app_state.command_queue.put(("change_monitor_by_index", [idx]))

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

if __name__ == "__main__":
    main()