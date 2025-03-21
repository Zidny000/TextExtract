# src/monitor_selector.py
import tkinter as tk
from screeninfo import get_monitors

class MonitorSelector:
    def __init__(self, master=None):
        self.master = master
        if master:
            self.root = tk.Toplevel(master)
        else:
            self.root = tk.Tk()
        self.root.title("Select Monitor")
        self.root.attributes("-topmost", True)
        self.selected_monitor = None
        self.monitors = get_monitors()

    def on_monitor_click(self, monitor_index):
        self.selected_monitor = self.monitors[monitor_index]
        self.root.destroy()

    def start(self):
        if len(self.monitors) == 1:
            self.selected_monitor = self.monitors[0]
            self.root.destroy()
            return self.selected_monitor

        for idx, monitor in enumerate(self.monitors):
            btn_text = f"Monitor {idx + 1}\n{monitor.width}x{monitor.height}"
            if monitor.x < 0 or monitor.y < 0:
                btn_text += f"\nPosition: {monitor.x},{monitor.y}"
            btn = tk.Button(
                self.root,
                text=btn_text,
                command=lambda idx=idx: self.on_monitor_click(idx)
            )
            btn.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Ensure the window is visible and properly focused
        self.root.deiconify()
        self.root.focus_force()
        self.root.lift()  # Ensure it's on top
        self.root.update()  # Force window manager to apply changes
        
        # If using a parent window, wait for this window to close
        if self.master:
            self.root.transient(self.master)
            self.root.grab_set()
            self.root.wait_window()
        else:
            self.root.mainloop()
            
        return self.selected_monitor