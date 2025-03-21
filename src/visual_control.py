import tkinter as tk
from tkinter import Canvas
from screeninfo import get_monitors
import os
from PIL import Image, ImageTk

class FloatingIcon:
    def __init__(self, capture_callback, monitor_select_callback, get_selected_monitor, master=None):
        # Store the callbacks
        self.capture_callback = capture_callback
        self.monitor_select_callback = monitor_select_callback
        self.get_selected_monitor = get_selected_monitor
        self.master = master
        
        # State variables
        self.is_expanded = False
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.monitors = get_monitors()
        self.is_visible = False
        
        # Create the main window
        self.root = None
        self.icon_frame = None
        self.canvas = None
        self.monitor_frame = None
    
    def create_window(self):
        """Create the main window and UI elements"""
        if self.root:
            # If window already exists but is hidden, just show it
            try:
                self.root.deiconify()
                self.is_visible = True
                return
            except tk.TclError:
                # Window was destroyed, create a new one
                pass
                
        self.root = tk.Toplevel(self.master)
        self.root.title("Text Extractor")
        self.root.overrideredirect(True)  # No window border
        self.root.attributes("-topmost", True)  # Always on top
        self.root.configure(bg="#3A3A3A")  # Dark background to match image
        
        # Set protocol to properly handle window closure
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        # Set initial position (centered on primary monitor)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"80x40+{screen_width-100}+{screen_height-100}")
        
        # Create main frame for the icon
        self.icon_frame = tk.Frame(self.root, bg="#3A3A3A")  # Dark background
        self.icon_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create canvas for the icon
        self.canvas = Canvas(self.icon_frame, width=80, height=40, bg="#3A3A3A", 
                            highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Draw the icon
        self.draw_icon()
        
        # Bind events
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        
        # Create monitor selection frame (initially hidden)
        self.monitor_frame = tk.Frame(self.root, bg="#3A3A3A", padx=10, pady=10)
        
        # Exit button at the top right corner
        exit_btn = tk.Button(self.icon_frame, text="×", font=("Arial", 10), 
                            bg="#3A3A3A", fg="white", bd=0,
                            command=self.hide_window)
        exit_btn.place(x=60, y=0, width=20, height=20)
        
        self.is_visible = True
    
    def hide_window(self):
        """Hide the window without destroying it"""
        if self.root:
            self.root.withdraw()
            self.is_visible = False
    
    def show_window(self):
        """Show the window if it exists, or create it if it doesn't"""
        if not self.root:
            self.create_window()
        else:
            try:
                self.root.deiconify()
                self.is_visible = True
            except tk.TclError:
                # Window was destroyed, create a new one
                self.create_window()
    
    def destroy(self):
        """Properly destroy all resources"""
        if self.root:
            try:
                self.root.destroy()
                self.root = None
                self.canvas = None
                self.icon_frame = None
                self.monitor_frame = None
                self.is_visible = False
            except Exception as e:
                print(f"Error destroying floating icon: {e}")
    
    def draw_icon(self):
        """Draw the pill-shaped icon with circular button and arrow"""
        if not self.canvas:
            return
            
        self.canvas.delete("all")
        
        # Draw pill-shaped background
        self.canvas.create_rectangle(0, 0, 80, 40, fill="#3A3A3A", outline="", tags="background")
        self.canvas.create_arc(0, 0, 40, 40, start=90, extent=180, fill="#3A3A3A", outline="")
        self.canvas.create_arc(40, 0, 80, 40, start=270, extent=180, fill="#3A3A3A", outline="")
        
        # Draw circular capture button on left
        self.canvas.create_oval(5, 5, 35, 35, fill="#888888", outline="", tags="capture_btn")
        
        # Draw arrow button on right side
        arrow_x = 55
        arrow_y = 20
        arrow_size = 12
        
        if self.is_expanded:
            # Up arrow (when expanded)
            self.canvas.create_polygon(
                arrow_x, arrow_y - arrow_size/2,  # Top point
                arrow_x - arrow_size/2, arrow_y + arrow_size/2,  # Bottom left
                arrow_x + arrow_size/2, arrow_y + arrow_size/2,  # Bottom right
                fill="white", outline="", tags="arrow_btn"
            )
        else:
            # Down arrow (when collapsed)
            self.canvas.create_polygon(
                arrow_x, arrow_y + arrow_size/2,  # Bottom point
                arrow_x - arrow_size/2, arrow_y - arrow_size/2,  # Top left
                arrow_x + arrow_size/2, arrow_y - arrow_size/2,  # Top right
                fill="white", outline="", tags="arrow_btn"
            )
    
    def on_press(self, event):
        """Handle mouse press events"""
        x, y = event.x, event.y
        
        # Check if click is on capture button (left circle)
        if (5 <= x <= 35) and (5 <= y <= 35) and \
           ((x-20)**2 + (y-20)**2 <= 15**2):
            self.capture_callback()
            return
        
        # Check if click is on arrow button (right side)
        if (45 <= x <= 75) and (10 <= y <= 30):
            self.toggle_expand()
            return
        
        # Otherwise, start dragging
        self.dragging = True
        self.drag_start_x = event.x
        self.drag_start_y = event.y
    
    def on_drag(self, event):
        """Handle mouse drag events"""
        if not self.dragging:
            return
        
        # Calculate new position
        x = self.root.winfo_x() + (event.x - self.drag_start_x)
        y = self.root.winfo_y() + (event.y - self.drag_start_y)
        self.root.geometry(f"+{x}+{y}")
    
    def on_release(self, event):
        """Handle mouse release events"""
        self.dragging = False
    
    def toggle_expand(self):
        """Toggle between expanded and collapsed states"""
        if not self.root:
            return
            
        if self.is_expanded:
            # Collapse
            self.monitor_frame.pack_forget()
            self.root.geometry("80x40")
        else:
            # Expand and show monitor selection
            self.create_monitor_list()
            self.monitor_frame.pack(fill=tk.BOTH, expand=True)
            self.root.geometry("200x{}".format(60 + len(self.monitors) * 40))
        
        self.is_expanded = not self.is_expanded
        self.draw_icon()
    
    def create_monitor_list(self):
        """Create the list of monitors"""
        if not self.monitor_frame:
            return
            
        # Clear old widgets
        for widget in self.monitor_frame.winfo_children():
            widget.destroy()
        
        # Get current selected monitor
        selected_monitor = self.get_selected_monitor()
        
        # Add monitor buttons
        for idx, monitor in enumerate(self.monitors):
            # Determine if this monitor is selected
            is_selected = False
            if selected_monitor:
                is_selected = (monitor.x == selected_monitor.x and 
                              monitor.y == selected_monitor.y and
                              monitor.width == selected_monitor.width and
                              monitor.height == selected_monitor.height)
            
            # Create monitor button with appropriate colors
            bg_color = "#555555" if is_selected else "#444444"
            fg_color = "white" if is_selected else "#DDDDDD"
            
            frame = tk.Frame(self.monitor_frame, bg=bg_color, bd=1, relief=tk.GROOVE)
            frame.pack(fill=tk.X, pady=2)
            
            btn_text = f"Monitor {idx + 1}: {monitor.width}x{monitor.height}"
            btn = tk.Label(frame, text=btn_text, bg=bg_color, fg=fg_color, padx=5, pady=5)
            btn.pack(fill=tk.X)
            
            # Bind click event
            frame.bind("<Button-1>", lambda e, idx=idx: self.select_monitor(idx))
            btn.bind("<Button-1>", lambda e, idx=idx: self.select_monitor(idx))
    
    def select_monitor(self, monitor_index):
        """Select a monitor and update UI"""
        self.monitor_select_callback(monitor_index)
        self.create_monitor_list()  # Refresh to show new selection
    
    def start(self):
        """Start the floating icon window"""
        self.create_window()
        self.root.mainloop() 