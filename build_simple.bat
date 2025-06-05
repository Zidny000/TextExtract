@echo off
echo Building TextExtract Application
echo ==============================

echo Cleaning previous build artifacts...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo Building executable with PyInstaller...
pyinstaller --noconfirm --onedir --windowed ^
  --name=TextExtract ^
  --icon=assets/icon.ico ^
  --add-data="assets;assets" ^
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