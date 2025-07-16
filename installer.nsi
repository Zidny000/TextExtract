; TextExtract Installer Script
; NSIS (Nullsoft Scriptable Install System) script

; Define the name of the installer
Name "TextExtract"
OutFile "TextExtract_Setup.exe"

; Default installation directory
InstallDir "$PROGRAMFILES\TextExtract"

; Request application privileges
RequestExecutionLevel admin

; Include Modern UI and additional libraries
!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"  ; For ${If} statements
!include "nsProcess.nsh"  ; Add this line to include nsProcess functions for process management

; Define the interface settings
!define MUI_ABORTWARNING
!define MUI_ICON "assets\icon.ico"
!define MUI_UNICON "assets\icon.ico"
!define PRODUCT_NAME "TextExtract"
!define PRODUCT_VERSION "1.0.0"
!define PRODUCT_PUBLISHER "TextExtract"
!define PRODUCT_WEB_SITE "https://textextract.app"
!define APP_EXE "TextExtract.exe"

; Custom pages (OCR download page removed)
; Removed OCRModelDownloadPage as it's no longer needed

; Standard pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "README.md"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch TextExtract now"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\README.md"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "Read application documentation"
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Language
!insertmacro MUI_LANGUAGE "English"

; Function to kill the running TextExtract process before uninstallation
Function un.TerminateTextExtractProcess
    DetailPrint "Looking for running TextExtract process..."
    ${nsProcess::FindProcess} "TextExtract.exe" $R0
    
    ${If} $R0 == 0
        DetailPrint "TextExtract.exe is running. Terminating process..."
        ${nsProcess::KillProcess} "TextExtract.exe" $R0
        
        ${If} $R0 == 0
            DetailPrint "Process successfully terminated."
        ${Else}
            DetailPrint "Failed to terminate process (error code: $R0). Waiting a few seconds..."
            Sleep 2000
            ${nsProcess::KillProcess} "TextExtract.exe" $R0
        ${EndIf}
    ${Else}
        DetailPrint "TextExtract.exe is not running."
    ${EndIf}
    
    ${nsProcess::Unload}
FunctionEnd

; Installer Version Information
VIProductVersion "${PRODUCT_VERSION}.0"
VIAddVersionKey "ProductName" "${PRODUCT_NAME}"
VIAddVersionKey "CompanyName" "${PRODUCT_PUBLISHER}"
VIAddVersionKey "LegalCopyright" "© ${PRODUCT_PUBLISHER}"
VIAddVersionKey "FileDescription" "TextExtract Screen Text OCR Tool"
VIAddVersionKey "FileVersion" "${PRODUCT_VERSION}"

; Variables (OCR-related variables removed)
; Removed DownloadModels, Dialog, Label1, Label2, CheckBox variables as they're no longer needed

; Custom functions for OCR models (removed - no longer needed)
; OCRModelDownloadPage and OCRModelDownloadPageLeave functions removed
; as the application no longer uses local OCR models

; Function to download models (removed - no longer using PaddleOCR)
; This function has been removed as the application no longer uses local OCR models

; Sections
Section "TextExtract (required)" SecMain
    SectionIn RO
    SetOutPath "$INSTDIR"
    
    ; Copy all files from the dist/TextExtract directory
    File /r "dist\TextExtract\*.*"    ; Copy additional files
    File "TextExtract_Install_Helper.bat"
    File "README.md"
    
    ; Create log directory in AppData
    CreateDirectory "$APPDATA\TextExtract"
    
    ; Create program menu shortcuts
    CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
    CreateShortcut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\assets\icon.ico"
    CreateShortcut "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
    CreateShortcut "$SMPROGRAMS\${PRODUCT_NAME}\README.lnk" "$INSTDIR\README.md"
    CreateShortcut "$SMPROGRAMS\${PRODUCT_NAME}\Installation Helper.lnk" "$INSTDIR\TextExtract_Install_Helper.bat"
    
    ; Write uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    
    ; Add uninstall information to Add/Remove Programs
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "DisplayName" "${PRODUCT_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "Publisher" "${PRODUCT_PUBLISHER}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "NoRepair" 1
    
    ; Get installation size
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}" "EstimatedSize" "$0"
    
    ; Register application in Windows Search
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\${APP_EXE}" "" "$INSTDIR\${APP_EXE}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\${APP_EXE}" "Path" "$INSTDIR"
    
    ; Register application to appear in Windows Search
    WriteRegStr HKLM "Software\Classes\Applications\${APP_EXE}\shell\open\command" "" '"$INSTDIR\${APP_EXE}" "%1"'
    WriteRegStr HKLM "Software\Classes\Applications\${APP_EXE}\DefaultIcon" "" "$INSTDIR\${APP_EXE},0"
      ; Add app to Windows path (for command-line access)
    EnVar::AddValue "PATH" "$INSTDIR"
    
    ; OCR model download removed - no longer needed
SectionEnd

Section "Desktop Shortcut" SecDesktop
    CreateShortcut "$DESKTOP\${PRODUCT_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\assets\icon.ico"
SectionEnd

Section "Start with Windows" SecStartup
    CreateShortcut "$SMSTARTUP\${PRODUCT_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\assets\icon.ico"
SectionEnd

; Descriptions
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} "The main program files (required)."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Create a shortcut on the desktop."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecStartup} "Start TextExtract automatically when Windows starts."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; Uninstaller
Section "Uninstall"
    ; First, terminate any running instance of TextExtract
    Call un.TerminateTextExtractProcess
    
    ; Wait a bit to ensure processes are fully terminated
    Sleep 1000
    
    ; Remove StartMenu shortcuts
    Delete "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk"
    Delete "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall.lnk"
    Delete "$SMPROGRAMS\${PRODUCT_NAME}\README.lnk"
    Delete "$SMPROGRAMS\${PRODUCT_NAME}\Installation Helper.lnk"
    RMDir "$SMPROGRAMS\${PRODUCT_NAME}"
    
    ; Remove desktop and startup shortcuts
    Delete "$DESKTOP\${PRODUCT_NAME}.lnk"
    Delete "$SMSTARTUP\${PRODUCT_NAME}.lnk"
    
    ; Remove registry keys
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\${APP_EXE}"
    DeleteRegKey HKLM "Software\Classes\Applications\${APP_EXE}"
    DeleteRegKey HKCU "Software\${PRODUCT_NAME}"
    
    ; Remove app from Windows path
    EnVar::DeleteValue "PATH" "$INSTDIR"
    
    ; Make extra sure the application is not running
    ExecWait 'taskkill /F /IM TextExtract.exe'
    Sleep 500
    
    ; Remove log directory
    RMDir /r "$APPDATA\TextExtract"
    
    ; Remove files and directories
    RMDir /r "$INSTDIR"
SectionEnd