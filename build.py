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
    
    # Get the current directory
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # PyInstaller command and options
    pyinstaller_cmd = [
        'pyinstaller',
        '--noconfirm',
        '--onedir',
        '--windowed',
        '--name=TextExtract',
        '--icon=assets/icon.ico',
        '--add-data=assets;assets',
        '--runtime-hook=runtime_hooks.py'
    ]

    # Add PaddleOCR data directories to the bundle
    paddleocr_dirs = []
    paddle_home = os.path.expanduser('~/.paddleocr')

    try:
        # Try to import paddleocr to find its installation path
        import paddleocr
        import paddle
        
        print(f"Found PaddlePaddle {paddle.__version__}")
        print(f"Found PaddleOCR {paddleocr.__version__}")
        
        # Verify correct versions
        if paddle.__version__ != "2.6.2":
            print(f"Warning: PaddlePaddle version {paddle.__version__} found, but 2.6.2 is recommended")
            if input("Install recommended version? (y/n): ").lower() == 'y':
                subprocess.check_call([sys.executable, "-m", "pip", "install", "paddlepaddle==2.6.2", "--force-reinstall"])
                import paddle
                print(f"Updated to PaddlePaddle {paddle.__version__}")
        
        if paddleocr.__version__ != "2.10.0":
            print(f"Warning: PaddleOCR version {paddleocr.__version__} found, but 2.10.0 is recommended")
            if input("Install recommended version? (y/n): ").lower() == 'y':
                subprocess.check_call([sys.executable, "-m", "pip", "install", "paddleocr==2.10.0", "--force-reinstall"])
                import paddleocr
                print(f"Updated to PaddleOCR {paddleocr.__version__}")
        
        paddle_dir = os.path.dirname(paddle.__file__)
        paddleocr_dir = os.path.dirname(paddleocr.__file__)
        
        # Add paddle and paddleocr module directories
        pyinstaller_cmd.extend([
            f'--add-data={paddle_dir};paddle',
            f'--add-data={paddleocr_dir};paddleocr'
        ])
        
        # Add PaddleOCR data directories if needed
        try:
            import paddleocr
            paddle_dir = os.path.dirname(paddleocr.__file__)
            paddleocr_data_dirs = [
                os.path.join(paddle_dir, 'ppocr', 'utils'),
                os.path.join(paddle_dir, 'ppocr', 'postprocess'),
                os.path.join(paddle_dir, 'ppocr', 'data')
            ]
            
            for data_dir in paddleocr_data_dirs:
                if os.path.exists(data_dir):
                    rel_path = os.path.relpath(data_dir, paddle_dir)
                    dest_path = os.path.join('paddleocr', rel_path)
                    pyinstaller_cmd.append(f'--add-data={data_dir};{dest_path}')
                    print(f"Added PaddleOCR data directory: {data_dir}")
                else:
                    print(f"Warning: PaddleOCR directory not found: {data_dir}")
            
            # Add model directories if downloaded
            model_dirs = [os.path.join(paddle_home, d) for d in os.listdir(paddle_home)] if os.path.exists(paddle_home) else []
            
            for model_dir in model_dirs:
                if os.path.isdir(model_dir):
                    rel_path = os.path.relpath(model_dir, os.path.dirname(paddle_home))
                    dest_path = os.path.join('paddleocr', rel_path)
                    pyinstaller_cmd.append(f'--add-data={model_dir};{dest_path}')
                    print(f"Added PaddleOCR model directory: {model_dir}")
                else:
                    print(f"Warning: PaddleOCR model directory not found: {model_dir}")
        except ImportError:
            print("PaddleOCR not installed, please install with pip install paddleocr==2.10.0")
            sys.exit(1)
            
        # Add hidden imports for paddle and paddleocr
        pyinstaller_cmd.extend([
            '--hidden-import=paddle',
            '--hidden-import=paddle.fluid',
            '--hidden-import=paddleocr',
            '--hidden-import=paddleocr.ppocr',
            '--hidden-import=paddleocr.tools'
        ])
        
    except ImportError:
        print("PaddleOCR is required for the build. Please install it first with:")
        print("pip install paddlepaddle==2.6.2 paddleocr==2.10.0")
        if input("Install now? (y/n): ").lower() == 'y':
            subprocess.check_call([sys.executable, "-m", "pip", "install", "paddlepaddle==2.6.2"])
            subprocess.check_call([sys.executable, "-m", "pip", "install", "paddleocr==2.10.0"])
            print("Dependencies installed. Please run the build script again.")
        sys.exit(1)

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
    
    # Copy model download script
    if os.path.exists("download_models.py"):
        print("Copying download_models.py to dist/TextExtract")
        shutil.copy2("download_models.py", "dist/TextExtract/download_models.py")
    else:
        print("Warning: download_models.py not found")
    
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