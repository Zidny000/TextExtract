@echo off
echo Checking for NSIS installation...
echo.

REM Check for NSIS in common installation paths
if exist "C:\Program Files (x86)\NSIS\makensis.exe" (
    echo Found NSIS at: C:\Program Files (x86)\NSIS\makensis.exe
    goto :found
)

if exist "C:\Program Files\NSIS\makensis.exe" (
    echo Found NSIS at: C:\Program Files\NSIS\makensis.exe
    goto :found
)

REM Check if NSIS is in PATH
makensis /VERSION >nul 2>&1
if %errorlevel% == 0 (
    echo Found NSIS in PATH
    goto :found
)

echo NSIS not found!
echo.
echo To create a proper Windows installer, you need to install NSIS:
echo 1. Download NSIS from: https://nsis.sourceforge.io/Download
echo 2. Install NSIS (recommended to install in default location)
echo 3. Run this script again to verify installation
echo.
echo Without NSIS, the build.py script will only create the executable files.
pause
exit /b 1

:found
echo.
echo NSIS is properly installed!
echo You can now run 'python build.py' to create both the executable and installer.
echo.
pause
