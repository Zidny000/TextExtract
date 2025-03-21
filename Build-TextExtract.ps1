# TextExtract Direct PowerShell Build Script
# This script builds TextExtract directly in PowerShell without using batch files

function Test-CommandExists {
    param ($command)
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = 'stop'
    try { if (Get-Command $command) { $true } }
    catch { $false }
    finally { $ErrorActionPreference = $oldPreference }
}

function Write-Header {
    param($title)
    Write-Host ""
    Write-Host $title -ForegroundColor Green
    Write-Host ("-" * $title.Length) -ForegroundColor Green
    Write-Host ""
}

# Set up the environment
$ErrorActionPreference = "Stop"
$scriptPath = $PSScriptRoot
if (-not $scriptPath) {
    $scriptPath = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition
}
$originalLocation = Get-Location
Set-Location -Path $scriptPath

try {
    # Main header
    Write-Header "TextExtract Windows Installer Builder (Pure PowerShell)"
    
    # Check if Python is available
    Write-Host "Checking if Python is available..." -ForegroundColor Cyan
    if (-not (Test-CommandExists python)) {
        Write-Host "Error: Python is not available in the system path." -ForegroundColor Red
        Write-Host "Please install Python and try again." -ForegroundColor Red
        exit 1
    }
    
    # Check if PyInstaller is installed
    Write-Host "Checking if PyInstaller is installed..." -ForegroundColor Cyan
    try {
        python -c "import PyInstaller" | Out-Null
    } catch {
        Write-Host "PyInstaller is not installed. Installing it now..." -ForegroundColor Yellow
        pip install pyinstaller
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Failed to install PyInstaller. Please install it manually." -ForegroundColor Red
            exit 1
        }
    }
    
    # Check for NSIS installation
    Write-Host "Checking for NSIS installation..." -ForegroundColor Cyan
    $nsisPath = $null
    if (Test-Path "${env:ProgramFiles(x86)}\NSIS\makensis.exe") {
        $nsisPath = "${env:ProgramFiles(x86)}\NSIS\makensis.exe"
    } elseif (Test-Path "$env:ProgramFiles\NSIS\makensis.exe") {
        $nsisPath = "$env:ProgramFiles\NSIS\makensis.exe"
    }
    
    if (-not $nsisPath) {
        Write-Host "Warning: NSIS (Nullsoft Scriptable Install System) is not installed." -ForegroundColor Yellow
        Write-Host "The executable will be built but the installer cannot be created." -ForegroundColor Yellow
        Write-Host "Please install NSIS from https://nsis.sourceforge.io/Download" -ForegroundColor Yellow
        
        $continueChoice = Read-Host "Do you want to continue with just building the executable? (Y/N)"
        if ($continueChoice -notmatch "^[yY]") {
            exit 1
        }
    } else {
        # Check if EnVar plugin is installed for NSIS
        if (-not (Test-Path "${env:ProgramFiles(x86)}\NSIS\Plugins\x86-unicode\EnVar.dll") -and
            -not (Test-Path "$env:ProgramFiles\NSIS\Plugins\x86-unicode\EnVar.dll")) {
            Write-Host "Warning: NSIS EnVar plugin is not installed." -ForegroundColor Yellow
            Write-Host "Please download and install it from https://nsis.sourceforge.io/EnVar_plug-in" -ForegroundColor Yellow
            
            $continueChoice = Read-Host "Do you want to continue anyway? (The installer may not function properly) (Y/N)"
            if ($continueChoice -notmatch "^[yY]") {
                exit 1
            }
        }
    }
    
    # Clean previous build artifacts
    Write-Host "Cleaning previous build artifacts..." -ForegroundColor Cyan
    if (Test-Path "build") {
        Remove-Item -Path "build" -Recurse -Force
    }
    if (Test-Path "dist") {
        Remove-Item -Path "dist" -Recurse -Force
    }
    
    # Install required Python packages
    Write-Host "Installing required Python packages..." -ForegroundColor Cyan
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install required packages." -ForegroundColor Red
        exit 1
    }
    
    # Build the executable
    Write-Header "Building the executable with PyInstaller"
    python build.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to build the executable." -ForegroundColor Red
        exit 1
    }
    
    # Check if dist directory was created successfully
    if (-not (Test-Path "dist\TextExtract")) {
        Write-Host "Error: The dist\TextExtract directory was not created." -ForegroundColor Red
        Write-Host "Build process failed." -ForegroundColor Red
        exit 1
    }
    
    # Compile the NSIS installer if NSIS is installed
    if ($nsisPath) {
        Write-Header "Building the installer with NSIS"
        & "$nsisPath" "installer.nsi"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Failed to build the installer." -ForegroundColor Red
            exit 1
        }
        
        if (Test-Path "TextExtract_Setup.exe") {
            Write-Host ""
            Write-Host "===============================" -ForegroundColor Green
            Write-Host "Installer created successfully!" -ForegroundColor Green
            Write-Host "The installer is located at:" -ForegroundColor Green
            Write-Host "$scriptPath\TextExtract_Setup.exe" -ForegroundColor Green
            Write-Host "===============================" -ForegroundColor Green
        } else {
            Write-Host "Failed to find the installer executable." -ForegroundColor Red
        }
    } else {
        Write-Host "Skipping installer creation as NSIS is not installed." -ForegroundColor Yellow
        Write-Host "The executable can be found in the dist\TextExtract directory." -ForegroundColor Cyan
    }
    
    Write-Host ""
    Write-Host "Build process completed successfully!" -ForegroundColor Green
    
} catch {
    Write-Host "An error occurred during the build process:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
} finally {
    # Restore original location
    Set-Location -Path $originalLocation
} 