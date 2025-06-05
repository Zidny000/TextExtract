import os
import shutil
import subprocess
import sys
import re
import platform
from pathlib import Path
from version import __version__

def build_executable():
    print("Building TextExtract executable...")
    
    # Clean previous build artifacts
    if os.path.exists("build"):
        print("Cleaning build directory...")
        shutil.rmtree("build")
    if os.path.exists("dist"):
        print("Cleaning dist directory...")
        shutil.rmtree("dist")
     # PyInstaller command and options
    pyinstaller_cmd = [
        'pyinstaller',
        '--noconfirm',
        '--onedir',
        '--windowed',
        '--name=TextExtract',
        '--icon=assets/icon.ico',
        '--add-data=assets;assets',
        '--add-data=src;src',  # Include the src directory
    ]    # Add required hidden imports and modules for the application
    pyinstaller_cmd.extend([
        '--hidden-import=PIL',
        '--hidden-import=mss',
        '--hidden-import=requests',
        '--hidden-import=keyboard',
        '--hidden-import=pyperclip',
        '--hidden-import=tkinter',
        '--hidden-import=threading',
        '--hidden-import=queue',
        '--hidden-import=winreg',
        '--hidden-import=pystray'
    ])

    # Add the main.py file to the PyInstaller command
    pyinstaller_cmd.append('src/main.py')

    # Run PyInstaller with the arguments
    print("Running PyInstaller with arguments:", " ".join(pyinstaller_cmd))
    subprocess.run(pyinstaller_cmd, check=True)

    print("PyInstaller build completed successfully!")
    
    # Ensure assets directory exists in the dist folder
    os.makedirs("dist/TextExtract/assets", exist_ok=True)
    
    # Copy icon to assets directory if it exists
    if os.path.exists("assets/icon.ico"):
        print("Copying icon.ico to dist/TextExtract/assets")
        shutil.copy2("assets/icon.ico", "dist/TextExtract/assets/icon.ico")
      # No need for model download script as we're using API service for OCR now
    
    print("Build completed successfully!")
    print("The executable is located in the dist/TextExtract directory.")
    print("To distribute the application, zip the entire TextExtract folder.")
    
    # Copy the shortcut creation script to the dist folder
    if os.path.exists("create_shortcut.py"):
        shutil.copy2("create_shortcut.py", "dist/TextExtract/create_shortcut.py")
        print("Shortcut creation script copied to the dist folder.")
        print("Users can run create_shortcut.py to create desktop and startup shortcuts.")
        
    # Copy the batch file for creating shortcuts
    if os.path.exists("create_shortcuts.bat"):
        shutil.copy2("create_shortcuts.bat", "dist/TextExtract/create_shortcuts.bat")
        print("Shortcut creation batch file copied to the dist folder.")

if __name__ == "__main__":
    build_executable() 