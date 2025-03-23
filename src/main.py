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
from utils import ensure_tesseract_installed
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

# Function to check and initialize Tesseract OCR
def check_and_initialize_tesseract(root):
    """Check if Tesseract OCR is installed and accessible"""
    from tkinter import ttk
    import tempfile
    
    # Create a progress window
    progress_window = tk.Toplevel(root)
    progress_window.title("TextExtract - Initializing OCR")
    progress_window.geometry("400x150")
    progress_window.resizable(False, False)
    progress_window.transient(root)
    progress_window.grab_set()
    
    # Center the progress window
    progress_window.update_idletasks()
    x = root.winfo_rootx() + (root.winfo_width() - progress_window.winfo_width()) // 2
    y = root.winfo_rooty() + (root.winfo_height() - progress_window.winfo_height()) // 2
    progress_window.geometry(f"+{x}+{y}")
    
    # Create UI elements
    frame = ttk.Frame(progress_window, padding="20")
    frame.pack(fill=tk.BOTH, expand=True)
    
    status_var = tk.StringVar(value="Checking Tesseract OCR...")
    status_label = ttk.Label(frame, textvariable=status_var)
    status_label.pack(pady=(0, 10))
    
    progress = ttk.Progressbar(frame, orient=tk.HORIZONTAL, length=350, mode='indeterminate')
    progress.pack(pady=(0, 10))
    progress.start(10)
    
    # Update status
    def update_status(msg):
        status_var.set(msg)
        progress_window.update_idletasks()
    
    # Check if Tesseract is installed and accessible
    update_status("Checking Tesseract OCR installation...")
    
    # We'll use a thread to check Tesseract so the UI doesn't freeze
    check_thread = None
    check_success = [False]
    check_error = [None]
    
    def check_tesseract_thread():
        try:
            from utils import ensure_tesseract_installed, get_tesseract_language_dir, map_to_tesseract_lang
            
            # Check for Tesseract installation
            update_status("Verifying Tesseract installation...")
            if not ensure_tesseract_installed():
                update_status("Tesseract not found. Please install it.")
                check_error[0] = "Tesseract OCR could not be found or initialized. Please install Tesseract."
                return
                
            # Check if pytesseract can be imported
            update_status("Verifying pytesseract installation...")
            import pytesseract
            
            # Try to get Tesseract version
            try:
                version = pytesseract.get_tesseract_version()
                update_status(f"Found Tesseract version {version}")
            except Exception as e:
                check_error[0] = f"Tesseract is installed but could not be accessed: {str(e)}"
                return
                
            # Check for English language file
            update_status("Checking Tesseract language files...")
            lang_dir = get_tesseract_language_dir()
            if lang_dir:
                eng_file = os.path.join(lang_dir, "eng.traineddata")
                if not os.path.exists(eng_file):
                    check_error[0] = "English language file not found for Tesseract."
                    return
                update_status(f"Found language files at: {lang_dir}")
            else:
                check_error[0] = "Tesseract language directory not found."
                return
                
            # Verify functionality with a simple test
            update_status("Testing Tesseract OCR...")
            
            # Create a simple test image
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new('RGB', (200, 50), color='white')
            d = ImageDraw.Draw(img)
            
            # Try to use a common font
            try:
                if os.name == 'nt':  # Windows
                    font = ImageFont.truetype("arial.ttf", 24)
                else:  # Linux/Mac
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            except Exception:
                # If font not found, use default
                font = None
                
            # Draw text on the image
            d.text((10, 10), "Tesseract Test", fill='black', font=font)
            
            # Save to temp file
            img_path = os.path.join(tempfile.gettempdir(), 'tesseract_test.png')
            img.save(img_path)
            
            # Run OCR on the test image
            try:
                text = pytesseract.image_to_string(img, lang='eng')
                if text and "Test" in text:
                    update_status("Tesseract OCR is working correctly!")
                    check_success[0] = True
                else:
                    check_error[0] = "Tesseract didn't properly recognize the test image."
            except Exception as e:
                check_error[0] = f"Error during Tesseract test: {str(e)}"
            finally:
                # Clean up
                if os.path.exists(img_path):
                    os.remove(img_path)
                
        except ImportError as e:
            check_error[0] = f"Failed to import required packages: {str(e)}"
        except Exception as e:
            check_error[0] = f"Unexpected error: {str(e)}"
        finally:
            progress_window.after(100, lambda: check_status(check_thread))
    
    def check_status(thread):
        if thread.is_alive():
            # Still checking
            progress_window.after(100, lambda: check_status(thread))
        else:
            progress_window.destroy()
            if check_success[0]:
                return True
            else:
                messagebox.showerror(
                    "OCR Error",
                    f"Tesseract OCR check failed: {check_error[0]}\n\n"
                    "Please make sure Tesseract is installed on your system.\n"
                    "Windows: https://github.com/UB-Mannheim/tesseract/wiki\n"
                    "Linux: sudo apt-get install tesseract-ocr\n"
                    "macOS: brew install tesseract"
                )
                return False
    
    # Start the check thread
    check_thread = threading.Thread(target=check_tesseract_thread)
    check_thread.start()
    
    # Let the GUI run - when check completes, the window will close
    return True

def main():
    try:
        # Check for another running instance
        is_first_instance, instance_socket = ensure_single_instance()
        if not is_first_instance:
            print("Exiting duplicate instance")
            return
            
        # Single Tk root instance for the entire application
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        
        # Initialize AppState
        state = AppState()
        
        # Check for Tesseract OCR installation
        check_and_initialize_tesseract(root)
        
        print(f"{APP_NAME} v{__version__} started")
        print("- Ctrl+Alt+C: Capture from last selected monitor")
        print("- Ctrl+Alt+M: Change monitor selection")
        print("- Ctrl+Alt+V: Show visual control icon")
        print("- Floating icon available for visual control")
        print("- System tray icon available in the notification area")

        # Command processor for handling UI actions in the main thread
        def process_commands():
            try:
                while not state.command_queue.empty():
                    command, args = state.command_queue.get_nowait()
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
                    state.command_queue.task_done()
            except queue.Empty:
                pass
            
            # Schedule the next command processing if still running
            if state.running:
                root.after(100, process_commands)

        def capture_from_selected_monitor():
            if not state.selected_monitor:
                print("No monitor selected. Press Ctrl+Alt+M to select one.")
                return

            # Temporarily make root visible to help with focus issues
            root.update_idletasks()
            
            overlay = ScreenOverlay(state.selected_monitor, root)
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
                state.selected_monitor = new_monitor
                save_selected_monitor(new_monitor)
                print(f"Monitor changed to: {new_monitor.width}x{new_monitor.height}")

        def change_monitor_by_index(monitor_index):
            monitors = get_monitors()
            if 0 <= monitor_index < len(monitors):
                state.selected_monitor = monitors[monitor_index]
                save_selected_monitor(state.selected_monitor)
                print(f"Monitor changed to: {state.selected_monitor.width}x{state.selected_monitor.height}")

        def get_selected_monitor():
            return state.selected_monitor

        def exit_application():
            print("Exiting application...")
            state.running = False
            
            # Unhook all keyboard listeners
            keyboard.unhook_all()
            
            # Stop the tray icon if it exists
            if state.tray_icon:
                try:
                    state.tray_icon.stop()
                except Exception as e:
                    print(f"Error stopping tray icon: {e}")
            
            # Safely destroy any remaining UI elements
            if state.floating_icon and state.floating_icon.is_visible:
                try:
                    state.floating_icon.hide_window()
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
            if instance_socket:
                try:
                    instance_socket.close()
                except Exception as e:
                    print(f"Error closing socket: {e}")
            
            # Schedule the actual quit to happen after all pending events are processed
            root.after(100, root.quit)

        # Thread-safe versions of commands
        def safe_capture():
            state.command_queue.put(("capture", None))
        
        def safe_change_monitor():
            state.command_queue.put(("change_monitor", None))
        
        def safe_toggle_floating_icon():
            state.command_queue.put(("toggle_floating_icon", None))
        
        def safe_exit():
            state.command_queue.put(("exit", None))
        
        def safe_change_monitor_by_index(idx):
            state.command_queue.put(("change_monitor_by_index", [idx]))

        # Function to toggle the floating icon visibility
        def toggle_floating_icon():
            if state.floating_icon:
                if state.floating_icon.is_visible:
                    print("Visual control icon is already visible")
                else:
                    state.floating_icon.show_window()
                    print("Visual control icon shown")
            else:
                # Create the floating icon if it doesn't exist
                create_floating_icon()

        # Function to create the floating icon
        def create_floating_icon():
            if not state.floating_icon:
                state.floating_icon = FloatingIcon(
                    capture_callback=safe_capture,
                    monitor_select_callback=safe_change_monitor_by_index,
                    get_selected_monitor=get_selected_monitor,
                    master=root  # Pass root as parent
                )
                print("Visual control icon created")
                state.floating_icon.create_window()

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
            state.tray_icon = pystray.Icon("TextExtract", icon_image, f"{APP_NAME} v{__version__}", menu)
            
            # Run the tray icon in a separate thread
            tray_thread = threading.Thread(target=lambda: state.tray_icon.run(), daemon=True)
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
    except ImportError as e:
        print(f"Error importing a required module: {e}")
        messagebox.showerror("Import Error", 
                              f"Failed to import a required module: {e}\n"
                              "Please install all required dependencies:\n"
                              "pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error in main function: {e}")
        messagebox.showerror("Error", f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()