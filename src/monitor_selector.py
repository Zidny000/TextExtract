# src/monitor_selector.py
import tkinter as tk
from tkinter import messagebox
from screeninfo import get_monitors
import traceback

class MonitorSelector:
    def __init__(self, master=None):
        self.master = master
        self.root = None
        self.selected_monitor = None
        self.monitors = []
        
        try:
            self.monitors = get_monitors()
            print(f"Found {len(self.monitors)} monitors")
            
            if master:
                self.root = tk.Toplevel(master)
                self.root.transient(master)
            else:
                self.root = tk.Tk()
                
            self.root.title("Select Monitor")
            self.root.attributes("-topmost", True)
            
            # Set window size and position
            self.root.geometry("300x200")
            
            # Center the window on screen
            self.root.update_idletasks()
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            x = (self.root.winfo_screenwidth() // 2) - (width // 2)
            y = (self.root.winfo_screenheight() // 2) - (height // 2)
            self.root.geometry(f'{width}x{height}+{x}+{y}')
            
        except Exception as e:
            print(f"Error initializing MonitorSelector: {e}")
            print(traceback.format_exc())
            if self.root:
                self.root.destroy()
            raise

    def on_monitor_click(self, monitor_index):
        try:
            if 0 <= monitor_index < len(self.monitors):
                self.selected_monitor = self.monitors[monitor_index]
                print(f"Selected monitor {monitor_index}: {self.selected_monitor.width}x{self.selected_monitor.height}")
            else:
                print(f"Invalid monitor index: {monitor_index}")
            
            if self.root:
                self.root.destroy()
                
        except Exception as e:
            print(f"Error selecting monitor: {e}")
            print(traceback.format_exc())
            if self.root:
                self.root.destroy()

    def start(self):
        try:
            if not self.monitors:
                print("No monitors found")
                if self.root:
                    self.root.destroy()
                return None
                
            if len(self.monitors) == 1:
                self.selected_monitor = self.monitors[0]
                print(f"Only one monitor found, auto-selecting: {self.selected_monitor.width}x{self.selected_monitor.height}")
                if self.root:
                    self.root.destroy()
                return self.selected_monitor

            # Create buttons for each monitor
            for idx, monitor in enumerate(self.monitors):
                btn_text = f"Monitor {idx + 1}\n{monitor.width}x{monitor.height}"
                if monitor.x != 0 or monitor.y != 0:
                    btn_text += f"\nPosition: {monitor.x},{monitor.y}"
                
                btn = tk.Button(
                    self.root,
                    text=btn_text,
                    command=lambda idx=idx: self.on_monitor_click(idx),
                    width=20,
                    height=3
                )
                btn.pack(fill=tk.X, padx=10, pady=5)
            
            # Add a cancel button
            cancel_btn = tk.Button(
                self.root,
                text="Cancel",
                command=lambda: self.on_monitor_click(-1),
                width=20,
                height=2
            )
            cancel_btn.pack(fill=tk.X, padx=10, pady=5)
            
            # Ensure the window is visible and properly focused
            self.root.deiconify()
            self.root.focus_force()
            self.root.lift()
            self.root.update()
            
            # Handle window interaction
            if self.master:
                self.root.grab_set()
                self.root.wait_window()
            else:
                self.root.mainloop()
                
        except Exception as e:
            print(f"Error in MonitorSelector.start(): {e}")
            print(traceback.format_exc())
            if self.root:
                try:
                    self.root.destroy()
                except:
                    pass
            return None
            
        return self.selected_monitor