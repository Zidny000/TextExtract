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
    ]
    
    # Add required hidden imports and modules for the application
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

def build_installer():
    """Build the NSIS installer after creating the executable"""
    print("\nBuilding Windows installer...")
    
    # Check if NSIS is available
    nsis_paths = [
        "C:\\Program Files (x86)\\NSIS\\makensis.exe",
        "C:\\Program Files\\NSIS\\makensis.exe",
        "makensis.exe"  # If NSIS is in PATH
    ]
    
    nsis_exe = None
    for path in nsis_paths:
        if os.path.exists(path) or path == "makensis.exe":
            try:
                # Test if the command works
                result = subprocess.run([path, "/VERSION"], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    nsis_exe = path
                    break
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                continue
    
    if not nsis_exe:
        print("NSIS not found. Please install NSIS (Nullsoft Scriptable Install System) to create the installer.")
        print("Download from: https://nsis.sourceforge.io/Download")
        print("The executable files are ready in the dist/TextExtract directory.")
        return False
    
    print(f"Found NSIS at: {nsis_exe}")
    
    # Ensure the installer.nsi file exists
    if not os.path.exists("installer.nsi"):
        print("installer.nsi file not found. Cannot create installer.")
        return False
    
    try:
        # Run NSIS to compile the installer
        print("Compiling NSIS installer...")
        result = subprocess.run([nsis_exe, "installer.nsi"], 
                              capture_output=True, text=True, check=True)
        
        print("NSIS compilation output:")
        print(result.stdout)
        
        if os.path.exists("TextExtract_Setup.exe"):
            print("\n✅ Windows installer created successfully!")
            print("📦 Installer file: TextExtract_Setup.exe")
            print("\nTo properly install TextExtract:")
            print("1. Run TextExtract_Setup.exe as administrator")
            print("2. This will:")
            print("   - Install the application to Program Files")
            print("   - Create desktop and Start Menu shortcuts")
            print("   - Register the application in Windows")
            print("   - Make it searchable in Windows Search")
            print("   - Add it to Add/Remove Programs")
            return True
        else:
            print("❌ Installer file was not created.")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ NSIS compilation failed: {e}")
        print("NSIS error output:")
        print(e.stderr)
        return False
    except Exception as e:
        print(f"❌ Error running NSIS: {e}")
        return False

def main():
    """Main build function"""
    try:
        # Build the executable first
        build_executable()
        
        print("\n" + "="*60)
        print("EXECUTABLE BUILD COMPLETED")
        print("="*60)
        
        # Then build the installer
        installer_success = build_installer()
        
        print("\n" + "="*60)
        print("BUILD SUMMARY")
        print("="*60)
        print("✅ Executable created in: dist/TextExtract/")
        
        if installer_success:
            print("✅ Windows installer created: TextExtract_Setup.exe")
            print("\n🚀 RECOMMENDED: Use the installer for proper Windows integration!")
        else:
            print("⚠️  Installer creation failed - executable only")
            print("\n📁 You can still use the files in dist/TextExtract/ as a portable app")
        
    except Exception as e:
        print(f"❌ Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()