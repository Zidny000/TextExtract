@echo off
title TextExtract Installation Helper
color 0A

:menu
cls
echo ===========================================
echo   TextExtract Installation Helper
echo ===========================================
echo.
echo  1. Create Desktop Shortcut
echo  2. Add to Startup (Run at Windows startup)
echo  3. Remove from Startup
echo  4. Register File Associations
echo  5. Add to Windows PATH
echo  6. Create Start Menu shortcuts
echo  7. Uninstall TextExtract
echo  8. Exit
echo.
echo ===========================================
echo.

set /p choice=Enter your choice (1-8): 

if "%choice%"=="1" goto create_desktop
if "%choice%"=="2" goto add_startup
if "%choice%"=="3" goto remove_startup
if "%choice%"=="4" goto register_associations
if "%choice%"=="5" goto add_path
if "%choice%"=="6" goto create_startmenu
if "%choice%"=="7" goto uninstall
if "%choice%"=="8" goto end

echo Invalid choice. Please try again.
timeout /t 2 >nul
goto menu

:create_desktop
echo.
echo Creating Desktop shortcut...
powershell -command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut([System.Environment]::GetFolderPath('Desktop') + '\TextExtract.lnk'); $Shortcut.TargetPath = '%~dp0TextExtract.exe'; $Shortcut.WorkingDirectory = '%~dp0'; $Shortcut.IconLocation = '%~dp0assets\icon.ico'; $Shortcut.Save()"
echo Desktop shortcut created!
timeout /t 2 >nul
goto menu

:add_startup
echo.
echo Adding TextExtract to Windows startup...
powershell -command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut([System.Environment]::GetFolderPath('Startup') + '\TextExtract.lnk'); $Shortcut.TargetPath = '%~dp0TextExtract.exe'; $Shortcut.WorkingDirectory = '%~dp0'; $Shortcut.IconLocation = '%~dp0assets\icon.ico'; $Shortcut.Save()"
echo TextExtract will now start when Windows boots!
timeout /t 2 >nul
goto menu

:remove_startup
echo.
echo Removing TextExtract from Windows startup...
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\TextExtract.lnk" >nul 2>&1
echo TextExtract removed from startup!
timeout /t 2 >nul
goto menu

:register_associations
echo.
echo This functionality requires administrator privileges.
echo Please run this script as administrator to register file associations.
timeout /t 3 >nul
goto menu

:add_path
echo.
echo This functionality requires administrator privileges.
echo Please run this script as administrator to add TextExtract to PATH.
timeout /t 3 >nul
goto menu

:create_startmenu
echo.
echo Creating Start Menu shortcuts...
if not exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\TextExtract" mkdir "%APPDATA%\Microsoft\Windows\Start Menu\Programs\TextExtract"
powershell -command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%APPDATA%\Microsoft\Windows\Start Menu\Programs\TextExtract\TextExtract.lnk'); $Shortcut.TargetPath = '%~dp0TextExtract.exe'; $Shortcut.WorkingDirectory = '%~dp0'; $Shortcut.IconLocation = '%~dp0assets\icon.ico'; $Shortcut.Save()"
powershell -command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%APPDATA%\Microsoft\Windows\Start Menu\Programs\TextExtract\Uninstall TextExtract.lnk'); $Shortcut.TargetPath = '%~dp0TextExtract_Install_Helper.bat'; $Shortcut.Arguments = 'uninstall_silent'; $Shortcut.WorkingDirectory = '%~dp0'; $Shortcut.Save()"
echo Start Menu shortcuts created!
timeout /t 2 >nul
goto menu

:uninstall
cls
echo ===========================================
echo   Uninstall TextExtract
echo ===========================================
echo.
echo  This will remove TextExtract shortcuts and settings.
echo  The application files will need to be deleted manually.
echo.
echo  Proceed with uninstallation?
echo   Y - Yes, uninstall
echo   N - No, cancel and return to menu
echo.
echo ===========================================
echo.

set /p confirm=Confirm (Y/N): 

if /i "%confirm%"=="Y" goto confirm_uninstall
goto menu

:confirm_uninstall
echo.
echo Uninstalling TextExtract...
echo.

echo Removing Desktop shortcut...
del "%USERPROFILE%\Desktop\TextExtract.lnk" >nul 2>&1

echo Removing Start Menu shortcuts...
rd /s /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\TextExtract" >nul 2>&1

echo Removing from Startup...
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\TextExtract.lnk" >nul 2>&1

echo Removing Registry entries...
reg delete "HKCU\Software\TextExtract" /f >nul 2>&1

echo.
echo TextExtract has been uninstalled.
echo You may now delete the application files manually.
echo.
pause
goto end

:uninstall_silent
echo Silently uninstalling TextExtract...
del "%USERPROFILE%\Desktop\TextExtract.lnk" >nul 2>&1
rd /s /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\TextExtract" >nul 2>&1
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\TextExtract.lnk" >nul 2>&1
reg delete "HKCU\Software\TextExtract" /f >nul 2>&1
exit

:end
echo.
echo Thank you for using TextExtract!
timeout /t 2 >nul
exit 