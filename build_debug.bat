@echo off
echo Building TextExtract Application (Console Mode for Debugging)
echo ======================================================

echo Cleaning previous build artifacts...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

pyinstaller --clean ...

$env:USE_PRODUCTION_API = "True"

echo Building executable with PyInstaller (console mode)...
pyinstaller --noconfirm --onedir ^
  --name=TextExtract_Debug ^
  --icon=assets/icon.ico ^
  src/main.py

if %errorlevel% neq 0 (
  echo Build failed!
  exit /b %errorlevel%
)

echo Build completed successfully!
echo The debug executable is located in the dist\TextExtract_Debug directory.

echo Done!
pause
