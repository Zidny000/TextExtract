"""
Base Dialog class for consistent dialog management throughout the application.
"""

import tkinter as tk
from tkinter import ttk
import logging
import traceback
from typing import Optional, Callable, Any, Dict, List, Tuple

from src.utils.threading.thread_manager import run_on_main_thread, run_in_background

# Configure logger
logger = logging.getLogger(__name__)

class BaseDialog:
    """
    Base class for all dialogs in the application.
    Provides common functionality and a consistent look and feel.
    """
    
    def __init__(self, parent: tk.Tk, title: str = "Dialog", 
                size: Tuple[int, int] = (400, 300),
                resizable: bool = False,
                modal: bool = True,
                topmost: bool = True,
                centered: bool = True,
                close_callback: Optional[Callable] = None):
        """
        Initialize the dialog.
        
        Args:
            parent: The parent window
            title: The dialog title
            size: The dialog size (width, height)
            resizable: Whether the dialog is resizable
            modal: Whether the dialog is modal (blocks interaction with parent)
            topmost: Whether the dialog should be topmost
            centered: Whether the dialog should be centered on the parent
            close_callback: Optional callback to execute when the dialog is closed
        """
        logger.debug(f"Creating {self.__class__.__name__}: {title}")
        
        self.parent = parent
        self.title = title
        self.size = size
        self.resizable = resizable
        self.modal = modal
        self.topmost = topmost
        self.centered = centered
        self.close_callback = close_callback
        
        # Dialog result
        self.result = None
        
        # Create the dialog in the main thread
        run_on_main_thread(self._create_dialog)
    
    def _create_dialog(self):
        """Create the dialog window."""
        try:
            # Create the dialog window
            self.dialog = tk.Toplevel(self.parent)
            self.dialog.title(self.title)
            self.dialog.geometry(f"{self.size[0]}x{self.size[1]}")
            self.dialog.resizable(self.resizable, self.resizable)
            
            # Make the dialog modal if requested
            if self.modal:
                self.dialog.transient(self.parent)
                self.dialog.grab_set()
            
            # Make the dialog topmost if requested
            if self.topmost:
                self.dialog.attributes('-topmost', True)
            
            # Center the dialog if requested
            if self.centered:
                self._center_dialog()
            
            # Set up close event handler
            self.dialog.protocol("WM_DELETE_WINDOW", self.on_close)
            
            # Create the dialog UI
            self._create_ui()
            
            # Focus the dialog
            self.dialog.focus_set()
            
            logger.debug(f"Dialog {self.__class__.__name__} created")
        except Exception as e:
            logger.error(f"Error creating dialog {self.__class__.__name__}: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def _center_dialog(self):
        """Center the dialog on the parent window."""
        try:
            # Update the dialog to ensure its size is calculated
            self.dialog.update_idletasks()
            
            # Get the dialog and parent window sizes
            width = self.dialog.winfo_width()
            height = self.dialog.winfo_height()
            
            # Calculate the center position
            x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (width // 2)
            y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (height // 2)
            
            # Ensure dialog is visible on screen
            x = max(0, min(x, self.dialog.winfo_screenwidth() - width))
            y = max(0, min(y, self.dialog.winfo_screenheight() - height))
            
            # Set the dialog position
            self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        except Exception as e:
            logger.warning(f"Error centering dialog: {e}")
            # Not critical, continue with default position
    
    def _create_ui(self):
        """
        Create the dialog UI. 
        Override this method to create a custom UI for each dialog.
        """
        # Base implementation - a frame with some padding
        self.main_frame = ttk.Frame(self.dialog, padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add a default close button
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        close_button = ttk.Button(button_frame, text="Close", command=self.on_close)
        close_button.pack(side=tk.RIGHT, padx=5)
    
    def on_close(self):
        """Handle dialog close event."""
        logger.debug(f"Closing dialog {self.__class__.__name__}")
        
        # Execute close callback if provided
        if self.close_callback:
            try:
                self.close_callback(self.result)
            except Exception as e:
                logger.error(f"Error executing close callback: {e}")
                logger.error(traceback.format_exc())
        
        # Release grab and destroy the dialog
        if self.modal:
            self.dialog.grab_release()
        
        self.dialog.destroy()
    
    def show(self):
        """
        Show the dialog and wait for it to be closed.
        
        Returns:
            Any: The dialog result
        """
        # If not on the main thread, return immediately
        # The dialog will still be shown
        if tk._default_root and tk._default_root.winfo_exists():
            if self.modal:
                # Wait for the dialog to be closed
                self.parent.wait_window(self.dialog)
            
        return self.result
    
    def set_result(self, result: Any):
        """
        Set the dialog result.
        
        Args:
            result: The dialog result
        """
        self.result = result
    
    def close(self, result: Any = None):
        """
        Close the dialog with the specified result.
        
        Args:
            result: The dialog result
        """
        if result is not None:
            self.set_result(result)
        
        run_on_main_thread(self.on_close)
    
    def run_in_background(self, func: Callable, *args, 
                      callback: Optional[Callable] = None,
                      error_callback: Optional[Callable] = None,
                      **kwargs):
        """
        Run a function in the background with UI feedback.
        
        Args:
            func: The function to run
            callback: Optional callback for successful completion
            error_callback: Optional callback for errors
            *args, **kwargs: Arguments to pass to the function
        """
        # Show a progress indicator
        self._show_progress()
        
        # Define callbacks to hide progress and handle the result
        def on_complete(result):
            self._hide_progress()
            if callback:
                callback(result)
        
        def on_error(error):
            self._hide_progress()
            if error_callback:
                error_callback(error)
            else:
                self._show_error(str(error))
        
        # Run the function in the background
        return run_in_background(
            func, *args, 
            callback=on_complete,
            error_callback=on_error,
            **kwargs
        )
    
    def _show_progress(self):
        """Show a progress indicator. Override in subclasses for custom UI."""
        # Default implementation - disable all buttons in the dialog
        for widget in self.dialog.winfo_children():
            if isinstance(widget, (ttk.Button, tk.Button)):
                widget.configure(state=tk.DISABLED)
    
    def _hide_progress(self):
        """Hide the progress indicator. Override in subclasses for custom UI."""
        # Default implementation - re-enable all buttons in the dialog
        for widget in self.dialog.winfo_children():
            if isinstance(widget, (ttk.Button, tk.Button)):
                widget.configure(state=tk.NORMAL)
    
    def _show_error(self, message: str):
        """
        Show an error message. Override in subclasses for custom UI.
        
        Args:
            message: The error message
        """
        # Default implementation - show a message box
        tk.messagebox.showerror("Error", message, parent=self.dialog) 