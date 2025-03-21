# src/overlay.py
import tkinter as tk
from tkinter import Canvas
from screeninfo import get_monitors

class ScreenOverlay:
    def __init__(self, monitor, master):
        self.monitor = monitor
        # Use a Toplevel window so that there's no conflict with the main Tk instance.
        self.top = tk.Toplevel(master)
        self.top.overrideredirect(True)
        self.top.attributes("-alpha", 0.3, "-topmost", True)
        self.top.configure(bg="black")
        
        # Position overlay on the selected monitor
        self.top.geometry(
            f"{self.monitor.width}x{self.monitor.height}+{self.monitor.x}+{self.monitor.y}"
        )
        
        # Create single canvas instance with proper configuration
        self.canvas = Canvas(
            self.top,
            cursor="cross",
            bg="black",
            highlightthickness=0,
            width=self.monitor.width,
            height=self.monitor.height,
            bd=0  # Remove border
        )
        self.canvas.configure(background="black")  # Ensure background is black
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)  # Remove padding
        
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        self.current_rect = None
        self.selection_canceled = False

        # Bind mouse events
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        
        # Bind ESC key to close overlay
        self.top.bind("<Escape>", self.on_escape)
        # Make sure the window can receive keyboard focus
        self.top.focus_set()

    def on_mouse_down(self, event):
        # Store canvas-relative coordinates
        self.start_x = event.x
        self.start_y = event.y
        
        # Create initial rectangle
        if self.current_rect:
            self.canvas.delete(self.current_rect)
        self.current_rect = self.canvas.create_rectangle(
            self.start_x, self.start_y,
            self.start_x, self.start_y,
            outline="red",
            width=2
        )

    def on_mouse_drag(self, event):
        if not self.current_rect:
            return
            
        # Update rectangle with current mouse position
        self.end_x = event.x
        self.end_y = event.y
        
        self.canvas.coords(
            self.current_rect,
            self.start_x, self.start_y,
            self.end_x, self.end_y
        )

    def on_mouse_up(self, event):
        self.end_x = event.x
        self.end_y = event.y
        self.top.destroy()

    def get_selection_coordinates(self):
        if self.selection_canceled or None in (self.start_x, self.start_y, self.end_x, self.end_y):
            return None, None, None, None
            
        # Convert canvas coordinates to screen coordinates
        screen_start_x = min(self.start_x, self.end_x) + self.monitor.x
        screen_start_y = min(self.start_y, self.end_y) + self.monitor.y
        screen_end_x = max(self.start_x, self.end_x) + self.monitor.x
        screen_end_y = max(self.start_y, self.end_y) + self.monitor.y
        
        return (
            screen_start_x,
            screen_start_y,
            screen_end_x,
            screen_end_y
        )

    def on_escape(self, event):
        """Handle ESC key press"""
        self.selection_canceled = True
        self.top.destroy()

    def start(self):
        # Make sure the window is visible and has focus
        self.top.deiconify()
        self.top.focus_force()
        self.top.lift()  # Ensure it's on top
        self.top.update()  # Force window manager to apply changes
        
        try:
            # Run the Toplevel's event loop until it's closed
            self.top.wait_window()
        except Exception as e:
            print(f"Error in overlay: {e}")
            self.selection_canceled = True