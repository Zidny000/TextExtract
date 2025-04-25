"""
Thread Manager for safely executing GUI operations across threads.
This module provides utilities to ensure that UI operations are always executed
on the main thread, avoiding threading-related issues with tkinter.
"""

import threading
import tkinter as tk
import logging
import traceback
from typing import Any, Callable, Optional, Dict, List, Tuple
import queue
import time

# Configure logger
logger = logging.getLogger(__name__)

class ThreadManager:
    """
    Manages the execution of UI operations across threads to ensure thread safety.
    """
    
    def __init__(self, root: tk.Tk):
        """
        Initialize the ThreadManager.
        
        Args:
            root: The root Tkinter window
        """
        self.root = root
        self.task_queue = queue.Queue()
        self.is_running = True
        self.worker_threads: Dict[str, threading.Thread] = {}
        
        # Start the task processor
        self._start_task_processor()
    
    def _start_task_processor(self):
        """Start the task processor to handle queued UI tasks."""
        def process_tasks():
            try:
                # Process all available tasks
                while not self.task_queue.empty():
                    task, args, kwargs = self.task_queue.get_nowait()
                    try:
                        task(*args, **kwargs)
                    except Exception as e:
                        logger.error(f"Error executing UI task: {e}")
                        logger.error(traceback.format_exc())
                    finally:
                        self.task_queue.task_done()
            except queue.Empty:
                pass
            
            # Schedule the next execution if still running
            if self.is_running and not self.root.winfo_ismapped():
                self.root.after(50, process_tasks)
            elif self.is_running:
                self.root.after(50, process_tasks)
        
        # Start the task processor
        self.root.after(50, process_tasks)
    
    def run_on_main_thread(self, func: Callable, *args, **kwargs) -> None:
        """
        Execute a function on the main thread.
        
        Args:
            func: The function to execute
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
        """
        # If already on main thread, execute directly
        if threading.current_thread() is threading.main_thread():
            try:
                func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error executing function on main thread: {e}")
                logger.error(traceback.format_exc())
        else:
            # Queue the task for execution on the main thread
            self.task_queue.put((func, args, kwargs))
    
    def run_in_background(self, func: Callable, *args, 
                         callback: Optional[Callable] = None,
                         error_callback: Optional[Callable] = None,
                         thread_name: Optional[str] = None,
                         **kwargs) -> threading.Thread:
        """
        Execute a function in a background thread.
        
        Args:
            func: The function to execute
            *args: Positional arguments to pass to the function
            callback: Optional callback to execute on the main thread with the function result
            error_callback: Optional callback to execute on the main thread if an error occurs
            thread_name: Optional name for the thread (for tracking purposes)
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            threading.Thread: The created background thread
        """
        # Generate a thread name if none provided
        if thread_name is None:
            thread_name = f"bg-{func.__name__}-{time.time()}"
        
        # Define the worker function
        def worker():
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Execute callback if provided
                if callback:
                    self.run_on_main_thread(callback, result)
                
                return result
            except Exception as e:
                logger.error(f"Error in background thread {thread_name}: {e}")
                logger.error(traceback.format_exc())
                
                # Execute error callback if provided
                if error_callback:
                    self.run_on_main_thread(error_callback, e)
                
                return None
            finally:
                # Remove thread from tracking
                if thread_name in self.worker_threads:
                    del self.worker_threads[thread_name]
        
        # Create and start the thread
        thread = threading.Thread(target=worker, name=thread_name, daemon=True)
        thread.start()
        
        # Track the thread
        self.worker_threads[thread_name] = thread
        
        return thread
    
    def shutdown(self):
        """Stop the thread manager and clean up."""
        logger.info("Shutting down ThreadManager")
        self.is_running = False
        
        # Wait for all tasks to complete
        self.task_queue.join()
        
        # Clear any remaining tasks
        while not self.task_queue.empty():
            try:
                self.task_queue.get_nowait()
                self.task_queue.task_done()
            except queue.Empty:
                break

# Global thread manager instance
_thread_manager: Optional[ThreadManager] = None

def init_thread_manager(root: tk.Tk) -> ThreadManager:
    """
    Initialize the global thread manager.
    
    Args:
        root: The root Tkinter window
        
    Returns:
        ThreadManager: The created thread manager instance
    """
    global _thread_manager
    if _thread_manager is None:
        _thread_manager = ThreadManager(root)
    return _thread_manager

def get_thread_manager() -> ThreadManager:
    """
    Get the global thread manager instance.
    
    Returns:
        ThreadManager: The thread manager instance
        
    Raises:
        RuntimeError: If the thread manager has not been initialized
    """
    if _thread_manager is None:
        raise RuntimeError("Thread manager not initialized. Call init_thread_manager first.")
    return _thread_manager

def run_on_main_thread(func: Callable, *args, **kwargs) -> None:
    """
    Execute a function on the main thread.
    
    Args:
        func: The function to execute
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Raises:
        RuntimeError: If the thread manager has not been initialized
    """
    get_thread_manager().run_on_main_thread(func, *args, **kwargs)

def run_in_background(func: Callable, *args, 
                     callback: Optional[Callable] = None,
                     error_callback: Optional[Callable] = None,
                     thread_name: Optional[str] = None,
                     **kwargs) -> threading.Thread:
    """
    Execute a function in a background thread.
    
    Args:
        func: The function to execute
        *args: Positional arguments to pass to the function
        callback: Optional callback to execute on the main thread with the function result
        error_callback: Optional callback to execute on the main thread if an error occurs
        thread_name: Optional name for the thread (for tracking purposes)
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        threading.Thread: The created background thread
        
    Raises:
        RuntimeError: If the thread manager has not been initialized
    """
    return get_thread_manager().run_in_background(
        func, *args, callback=callback, error_callback=error_callback, 
        thread_name=thread_name, **kwargs
    ) 