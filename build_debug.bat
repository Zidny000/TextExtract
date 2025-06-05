@echo off
echo Building TextExtract Application (Console Mode for Debugging)
echo ======================================================

echo Cleaning previous build artifacts...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo Creating necessary __init__.py files...
if not exist "src\__init__.py" echo # Package marker > "src\__init__.py"
if not exist "src\ui\__init__.py" echo # Package marker > "src\ui\__init__.py"
if not exist "src\ui\dialogs\__init__.py" echo # Package marker > "src\ui\dialogs\__init__.py" 
if not exist "src\utils\__init__.py" echo # Package marker > "src\utils\__init__.py"

echo Building executable with PyInstaller (console mode)...
pyinstaller --noconfirm --onedir ^
  --name=TextExtract_Debug ^
  --icon=assets/icon.ico ^
  --add-data="assets;assets" ^
  --add-data="src;src" ^
  --hidden-import=PIL ^
  --hidden-import=mss ^
  --hidden-import=requests ^
  --hidden-import=keyboard ^
  --hidden-import=pyperclip ^
  --hidden-import=tkinter ^
  --hidden-import=threading ^
  --hidden-import=queue ^
  --hidden-import=winreg ^
  --hidden-import=pystray ^
  --hidden-import=screeninfo ^
  --hidden-import=pytesseract ^
  --hidden-import=cv2 ^
  --hidden-import=numpy ^
  --hidden-import=src ^
  --hidden-import=src.auth ^
  --hidden-import=src.config ^
  --hidden-import=src.monitor_selector ^
  --hidden-import=src.ocr ^
  --hidden-import=src.overlay ^
  --hidden-import=src.visual_control ^
  --hidden-import=src.clipboard ^
  --hidden-import=src.imports ^
  --hidden-import=src.ui ^
  --hidden-import=src.ui.dialogs ^
  --hidden-import=src.ui.dialogs.auth_modal ^
  --hidden-import=src.utils ^
  --hidden-import=src.utils.threading ^
  --hidden-import=src.utils.threading.thread_manager ^
  --hidden-import=auth ^
  --hidden-import=config ^
  --hidden-import=monitor_selector ^
  --hidden-import=ocr ^
  --hidden-import=overlay ^
  --hidden-import=visual_control ^
  --hidden-import=clipboard ^
  --hidden-import=imports ^
  --runtime-hook=runtime_hooks.py ^
  src/main.py

if %errorlevel% neq 0 (
  echo Build failed!
  exit /b %errorlevel%
)

echo Build completed successfully!
echo The debug executable is located in the dist\TextExtract_Debug directory.

echo Done!
pause
