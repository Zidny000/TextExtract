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

; Define the interface settings
!define MUI_ABORTWARNING
!define MUI_ICON "assets\icon.ico"
!define MUI_UNICON "assets\icon.ico"
!define PRODUCT_NAME "TextExtract"
!define PRODUCT_VERSION "1.0.0"
!define PRODUCT_PUBLISHER "TextExtract"
!define PRODUCT_WEB_SITE "https://textextract.app"
!define APP_EXE "TextExtract.exe"

; Custom pages
Page custom OCRModelDownloadPage OCRModelDownloadPageLeave

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

; Installer Version Information
VIProductVersion "${PRODUCT_VERSION}.0"
VIAddVersionKey "ProductName" "${PRODUCT_NAME}"
VIAddVersionKey "CompanyName" "${PRODUCT_PUBLISHER}"
VIAddVersionKey "LegalCopyright" "© ${PRODUCT_PUBLISHER}"
VIAddVersionKey "FileDescription" "TextExtract Screen Text OCR Tool"
VIAddVersionKey "FileVersion" "${PRODUCT_VERSION}"

; Variables
Var DownloadModels
Var Dialog
Var Label1
Var Label2
Var CheckBox

; Custom function for downloading OCR models page
Function OCRModelDownloadPage
    !insertmacro MUI_HEADER_TEXT "Download OCR Models" "Choose whether to download OCR models during installation."
    
    ; Create dialog
    nsDialogs::Create 1018
    Pop $Dialog
    ${If} $Dialog == error
        Abort
    ${EndIf}
    
    ; Add labels
    ${NSD_CreateLabel} 0 0 100% 24u "TextExtract uses PaddleOCR for text recognition."
    Pop $Label1
    
    ${NSD_CreateLabel} 0 30u 100% 50u "The first time the application runs, it needs to download OCR models (about 100MB). You can pre-download these models now during installation to improve the first-use experience."
    Pop $Label2
    
    ; Add checkbox
    ${NSD_CreateCheckBox} 0 90u 100% 10u "Download OCR models now (recommended)"
    Pop $CheckBox
    ${NSD_Check} $CheckBox ; checked by default
    
    nsDialogs::Show
FunctionEnd

Function OCRModelDownloadPageLeave
    ${NSD_GetState} $CheckBox $DownloadModels
FunctionEnd

; Function to download models
Function DownloadOCRModels
    DetailPrint "Downloading OCR models (this may take a few minutes)..."
    
    ; Run the model download script
    nsExec::ExecToLog '"$INSTDIR\python\python.exe" "$INSTDIR\download_models.py"'
    Pop $0
    
    DetailPrint "Download process finished with exit code: $0"
    ${If} $0 == 0
        DetailPrint "OCR models downloaded successfully."
    ${Else}
        DetailPrint "Model download may not have completed successfully. Models will be downloaded at first run."
        MessageBox MB_OK|MB_ICONINFORMATION "OCR models will be downloaded automatically the first time you use the application. This may cause a slight delay on first use."
    ${EndIf}
FunctionEnd

; Sections
Section "TextExtract (required)" SecMain
    SectionIn RO
    SetOutPath "$INSTDIR"
    
    ; Copy all files from the dist/TextExtract directory
    File /r "dist\TextExtract\*.*"
    
    ; Copy additional files
    File "TextExtract_Install_Helper.bat"
    File "download_models.py"
    
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
    
    ; Download OCR models if selected
    ${If} $DownloadModels == ${BST_CHECKED}
        Call DownloadOCRModels
    ${EndIf}
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
    
    ; Remove log directory
    RMDir /r "$APPDATA\TextExtract"
    
    ; Remove files and directories
    RMDir /r "$INSTDIR"
SectionEnd 