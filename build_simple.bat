@echo off
echo Building TextExtract Application
echo ==============================

echo Cleaning previous build artifacts...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo Creating necessary __init__.py files...
if not exist "src\__init__.py" echo # Package marker > "src\__init__.py"
if not exist "src\ui\__init__.py" echo # Package marker > "src\ui\__init__.py"
if not exist "src\ui\dialogs\__init__.py" echo # Package marker > "src\ui\dialogs\__init__.py" 
if not exist "src\utils\__init__.py" echo # Package marker > "src\utils\__init__.py"

echo Building executable with PyInstaller...
pyinstaller --noconfirm --onedir --windowed ^
  --name=TextExtract ^
  --icon=assets/icon.ico ^
  --add-data="assets;assets" ^
  --add-data="src;src" ^  --hidden-import=PIL ^
  --hidden-import=mss ^
  --hidden-import=requests ^
  --hidden-import=keyboard ^
  --hidden-import=pyperclip ^
  --hidden-import=tkinter ^
  --hidden-import=threading ^
  --hidden-import=queue ^
  --hidden-import=winreg ^
  --hidden-import=pystray ^
  --hidden-import=src ^
  --hidden-import=src.utils ^
  --hidden-import=src.utils.threading ^
  --hidden-import=src.utils.threading.thread_manager ^
  --runtime-hook=runtime_hooks.py ^
  src/main.py

if %errorlevel% neq 0 (
  echo Build failed!
  exit /b %errorlevel%
)

echo Build completed successfully!
echo The executable is located in the dist\TextExtract directory.

echo Copying additional files...
if exist "create_shortcut.py" copy "create_shortcut.py" "dist\TextExtract"
if exist "create_shortcuts.bat" copy "create_shortcuts.bat" "dist\TextExtract"

echo Done!
pause
