"""
Base dialog module that provides a foundation for all application dialogs.

This module defines a BaseDialog class that implements common dialog functionality
and appearance, allowing specific dialog types to inherit from it.
"""

import tkinter as tk
from tkinter import ttk
import logging

logger = logging.getLogger(__name__)

class BaseDialog:
    """
    Base dialog class that provides common functionality for all dialogs.
    
    Features:
    - Customizable title, size, and position
    - Standard close button and escape key binding
    - Support for modal and non-modal operation
    - Consistent styling across all dialogs
    """
    
    def __init__(
        self,
        parent,
        title="Dialog",
        width=400,
        height=300,
        modal=True,
        resizable=(False, False),
        position=None
    ):
        """
        Initialize a new BaseDialog.
        
        Args:
            parent: The parent window
            title: Dialog title
            width: Dialog width in pixels
            height: Dialog height in pixels
            modal: Whether the dialog should be modal
            resizable: Tuple of (horizontal, vertical) resizable flags
            position: Optional position tuple (x, y) or None for center
        """
        self.parent = parent
        self.title = title
        self.width = width
        self.height = height
        self.modal = modal
        
        # Create the toplevel widget
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.minsize(width, height)
        
        # Set dialog to be modal if requested
        if modal:
            self.window.transient(parent)
            self.window.grab_set()
        
        # Set resizable properties
        self.window.resizable(resizable[0], resizable[1])
        
        # Position the window (centered by default)
        self._position_window(position)
        
        # Set up the window close event
        self.window.protocol("WM_DELETE_WINDOW", self.hide)
        
        # Bind escape key to close
        self.window.bind("<Escape>", lambda e: self.hide())
        
        # Create main container frames
        self._create_container_frames()
        
        # Create UI elements (to be implemented by subclasses)
        self._create_ui()
        
        # Set initial focus
        self.window.focus_set()
    
    def _position_window(self, position=None):
        """
        Position the dialog window.
        
        Args:
            position: Optional tuple (x, y) for position or None for center
        """
        self.window.update_idletasks()
        
        if position:
            x, y = position
        else:
            # Center in parent
            parent_x = self.parent.winfo_x()
            parent_y = self.parent.winfo_y()
            parent_width = self.parent.winfo_width()
            parent_height = self.parent.winfo_height()
            
            x = parent_x + (parent_width // 2) - (self.width // 2)
            y = parent_y + (parent_height // 2) - (self.height // 2)
        
        # Ensure dialog is fully visible on screen
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        x = max(0, min(x, screen_width - self.width))
        y = max(0, min(y, screen_height - self.height))
        
        self.window.geometry(f"{self.width}x{self.height}+{x}+{y}")
    
    def _create_container_frames(self):
        """Create the main container frames."""
        # Main content frame
        self.content_frame = ttk.Frame(self.window, padding=10)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Button frame (at the bottom)
        self.button_frame = ttk.Frame(self.window, padding=(10, 5, 10, 10))
        self.button_frame.pack(fill=tk.X)
    
    def _create_ui(self):
        """
        Create the UI elements.
        
        This method should be overridden by subclasses.
        """
        pass
    
    def show(self):
        """
        Show the dialog.
        
        If the dialog is modal, this will wait for it to be closed.
        """
        # Bring to front
        self.window.lift()
        self.window.attributes('-topmost', True)
        self.window.after_idle(self.window.attributes, '-topmost', False)
        
        # For modal dialogs, wait for the window
        if self.modal:
            self.parent.wait_window(self.window)
    
    def hide(self):
        """Hide the dialog."""
        # Release grab if modal
        if self.modal:
            try:
                self.window.grab_release()
            except tk.TclError:
                # Window might already be destroyed
                pass
        
        # Hide the window
        self.window.withdraw()
    
    def destroy(self):
        """Destroy the dialog."""
        try:
            self.window.destroy()
        except tk.TclError:
            # Window might already be destroyed
            pass 