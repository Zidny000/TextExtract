# TextExtract Build Script with NSIS Installation
# This script will install NSIS if needed and then build the TextExtract installer

Write-Host "TextExtract Build Script" -ForegroundColor Green
Write-Host "======================" -ForegroundColor Green

# Function to check if running as administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Function to install NSIS
function Install-NSIS {
    Write-Host "Installing NSIS..." -ForegroundColor Yellow
    
    try {
        # Check if winget is available
        $winget = Get-Command winget -ErrorAction SilentlyContinue
        if ($winget) {
            Write-Host "Installing NSIS via winget..." -ForegroundColor Cyan
            winget install NSIS.NSIS --accept-package-agreements --accept-source-agreements
        } else {
            # Alternative: Download and install manually
            Write-Host "Winget not available. Please install NSIS manually:" -ForegroundColor Yellow
            Write-Host "1. Go to https://nsis.sourceforge.io/Download" -ForegroundColor White
            Write-Host "2. Download and install NSIS" -ForegroundColor White
            Write-Host "3. Run this script again" -ForegroundColor White
            Read-Host "Press Enter to continue after installing NSIS"
        }
    } catch {
        Write-Host "Error installing NSIS: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Please install NSIS manually from https://nsis.sourceforge.io/Download" -ForegroundColor Yellow
        exit 1
    }
}

# Function to check NSIS installation
function Test-NSIS {
    $nsisPath = @(
        "C:\Program Files (x86)\NSIS\makensis.exe",
        "C:\Program Files\NSIS\makensis.exe"
    )
    
    foreach ($path in $nsisPath) {
        if (Test-Path $path) {
            return $path
        }
    }
    
    # Check if in PATH
    try {
        $result = Get-Command makensis -ErrorAction SilentlyContinue
        if ($result) {
            return "makensis"
        }
    } catch {}
    
    return $null
}

# Main script
Write-Host "Checking prerequisites..." -ForegroundColor Cyan

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Please install Python first." -ForegroundColor Red
    exit 1
}

# Check NSIS
$nsisPath = Test-NSIS
if (-not $nsisPath) {
    Write-Host "❌ NSIS not found." -ForegroundColor Red
    
    if (Test-Administrator) {
        $choice = Read-Host "Would you like to install NSIS automatically? (y/n)"
        if ($choice -eq 'y' -or $choice -eq 'Y') {
            Install-NSIS
            # Refresh PATH and check again
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
            $nsisPath = Test-NSIS
        }
    } else {
        Write-Host "Run this script as Administrator to auto-install NSIS, or install manually:" -ForegroundColor Yellow
        Write-Host "https://nsis.sourceforge.io/Download" -ForegroundColor White
    }
    
    if (-not $nsisPath) {
        Write-Host "❌ NSIS installation failed or not found. Building executable only." -ForegroundColor Red
        $buildInstallerOnly = $false
    } else {
        Write-Host "✅ NSIS installed successfully!" -ForegroundColor Green
        $buildInstallerOnly = $true
    }
} else {
    Write-Host "✅ NSIS found: $nsisPath" -ForegroundColor Green
    $buildInstallerOnly = $true
}

# Ask user what to build
Write-Host "`nBuild Options:" -ForegroundColor Cyan
Write-Host "1. Build executable only (portable)" -ForegroundColor White
Write-Host "2. Build installer (recommended)" -ForegroundColor White
Write-Host "3. Build both" -ForegroundColor White

do {
    $choice = Read-Host "Choose option (1-3)"
} while ($choice -notin @('1', '2', '3'))

# Build executable if requested
if ($choice -eq '1' -or $choice -eq '3') {
    Write-Host "`nBuilding executable..." -ForegroundColor Yellow
    python build.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Build failed!" -ForegroundColor Red
        exit 1
    }
}

# Build installer if requested and NSIS is available
if (($choice -eq '2' -or $choice -eq '3') -and $nsisPath) {
    Write-Host "`nBuilding installer..." -ForegroundColor Yellow
    
    # First build executable if not already done
    if ($choice -eq '2') {
        python build.py
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Executable build failed!" -ForegroundColor Red
            exit 1
        }
    }
    
    # Then compile installer
    Write-Host "Compiling NSIS installer..." -ForegroundColor Cyan
    if ($nsisPath -eq "makensis") {
        & makensis installer.nsi
    } else {
        & $nsisPath installer.nsi
    }
    
    if ($LASTEXITCODE -eq 0 -and (Test-Path "TextExtract_Setup.exe")) {
        Write-Host "`n✅ Windows installer created successfully!" -ForegroundColor Green
        Write-Host "📦 Installer file: TextExtract_Setup.exe" -ForegroundColor Cyan
        Write-Host "`nTo properly install TextExtract:" -ForegroundColor Yellow
        Write-Host "1. Run TextExtract_Setup.exe as administrator" -ForegroundColor White
        Write-Host "2. This will:" -ForegroundColor White
        Write-Host "   - Install the application to Program Files" -ForegroundColor Gray
        Write-Host "   - Create desktop and Start Menu shortcuts" -ForegroundColor Gray
        Write-Host "   - Register the application in Windows" -ForegroundColor Gray
        Write-Host "   - Make it searchable in Windows Search" -ForegroundColor Gray
        Write-Host "   - Add it to Add/Remove Programs" -ForegroundColor Gray
    } else {
        Write-Host "❌ Installer creation failed!" -ForegroundColor Red
        exit 1
    }
} elseif ($choice -eq '2' -and -not $nsisPath) {
    Write-Host "❌ Cannot build installer without NSIS!" -ForegroundColor Red
    exit 1
}

Write-Host "`n🎉 Build completed successfully!" -ForegroundColor Green
Read-Host "Press Enter to exit"
