# src/imports.py
"""
Helper module to handle imports properly in both frozen and non-frozen environments.
This module provides utility functions to import modules correctly regardless of whether
the application is running as a script or a frozen executable.
"""

import sys
import os
import importlib

def get_module(name, package=None):
    """
    Import a module correctly whether the application is frozen or not.
    
    Args:
        name: The module name to import
        package: Optional package name for relative imports
        
    Returns:
        The imported module
    """
    try:
        # First try direct import
        return importlib.import_module(name, package)
    except ImportError:
        # Then try from src package
        try:
            if package:
                return importlib.import_module(f"src.{package}.{name}")
            else:
                return importlib.import_module(f"src.{name}")
        except ImportError:
            # Last attempt with just the name
            return importlib.import_module(name)

def setup_import_path():
    """
    Set up the import path correctly for both frozen and non-frozen environments.
    """
    # Add the application directory to sys.path
    if getattr(sys, 'frozen', False):
        # We are running in a PyInstaller bundle
        bundle_dir = os.path.dirname(sys.executable)
        if bundle_dir not in sys.path:
            sys.path.insert(0, bundle_dir)
    else:
        # We are running in a normal Python environment
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if app_dir not in sys.path:
            sys.path.insert(0, app_dir)
