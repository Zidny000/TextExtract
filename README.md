# TextExtract - Screen Text Extraction Tool

TextExtract is a screen text extraction tool using OCR (Optical Character Recognition) to capture text from anywhere on your screen. Perfect for copying text from applications, images, videos, or any other screen content that doesn't allow normal text selection.

## Features

- **Quick Text Extraction**: Select any area on your screen and extract text using OCR technology
- **Multi-Monitor Support**: Works with multi-monitor setups, allowing you to choose which monitor to capture from
- **Visual Control Panel**: Easy-to-use floating control panel for quick access to features
- **System Tray Integration**: Stays out of your way in the system tray until you need it
- **Keyboard Shortcuts**: Quick access using convenient keyboard shortcuts
- **Desktop Integration**: Proper Windows desktop integration with Start Menu entries and desktop shortcuts
- **Google Vision API**: Powered by Google's advanced OCR technology for accurate text extraction

## SaaS Deployment

This application uses a SaaS (Software as a Service) model with embedded Google Vision API credentials. As a developer deploying this application:

1. Create a Google Cloud account if you don't have one at [https://cloud.google.com/](https://cloud.google.com/)
2. Create a new Google Cloud project
3. Enable the Vision API for your project: Go to APIs & Services > Library > Search for "Vision API" > Enable
4. Create a service account: Go to APIs & Services > Credentials > Create Credentials > Service Account
5. Create a JSON key for your service account: Click on your service account > Keys > Add Key > Create New Key > JSON
6. Download the JSON key file
7. You can embed the credentials in three ways:
   - Set the `GOOGLE_VISION_CREDENTIALS` environment variable with the contents of the JSON file before building
   - Encode the JSON as base64 and set `GOOGLE_VISION_CREDENTIALS=base64:<encoded-json>` to hide the raw credentials
   - Edit `src/config.py` and add your base64-encoded credentials directly to the `HARDCODED_CREDENTIALS` variable (most secure for distribution)

The third option is recommended for distribution as it permanently embeds the credentials in the compiled application, ensuring users don't need to set up their own credentials or environment variables.

Users of your application won't need to set up their own Google Vision API credentials as they'll use your embedded credentials.

## Installation

### Windows Installer (Recommended)

1. Download the latest installer (`TextExtract_Setup.exe`) from the [Releases](https://github.com/yourrepository/TextExtract/releases) page
2. Run the installer and follow the on-screen instructions
3. Choose installation options (desktop shortcut, start with Windows)
4. Once installed, TextExtract will be available from the Start Menu, desktop shortcut (if selected), or by searching in Windows Search

### Manual Installation (Advanced)

If you prefer not to use the installer:

1. Download the latest ZIP package from the [Releases](https://github.com/yourrepository/TextExtract/releases) page
2. Extract the ZIP file to a location of your choice
3. Run `TextExtract.exe` to start the application
4. Optionally run `create_shortcuts.bat` to create desktop and startup shortcuts

## Usage

- **Launch**: Start TextExtract from the Start Menu, desktop shortcut, or by searching in Windows
- **Capture Text**: Press `Ctrl+Alt+C` to start a capture, select the area with your mouse
- **Change Monitor**: Press `Ctrl+Alt+M` to select which monitor to capture from
- **Show Control Panel**: Press `Ctrl+Alt+V` to show the visual control panel
- **System Tray**: Right-click the TextExtract icon in the system tray to access menu options

## Keyboard Shortcuts

- `Ctrl+Alt+C`: Capture text from the screen
- `Ctrl+Alt+M`: Change the monitor selection
- `Ctrl+Alt+V`: Show/hide the visual control panel

## Building from Source

### Prerequisites

- Python 3.7 or higher
- Required packages listed in `requirements.txt`
- NSIS (Nullsoft Scriptable Install System) for building the installer
- Google Vision API credentials (see SaaS Deployment section)

### Build Steps

1. Clone the repository:
   ```
   git clone https://github.com/yourrepository/TextExtract.git
   cd TextExtract
   ```

2. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Prepare your Google Vision credentials using the provided utility script:
   ```
   python prepare_credentials.py path/to/your/credentials.json --base64 --export
   ```
   Use the output to set the GOOGLE_VISION_CREDENTIALS environment variable or store it securely for later use.

5. Build the installer:
   ```
   build_installer.bat
   ```

6. The installer will be created in the project directory as `TextExtract_Setup.exe`

## Uninstallation

TextExtract can be uninstalled like any standard Windows application:

1. Go to Windows Settings > Apps > Apps & features
2. Find "TextExtract" in the list and click "Uninstall"
3. Follow the uninstallation wizard

Alternatively:
1. Open the Control Panel > Programs > Programs and Features
2. Select "TextExtract" and click "Uninstall"

## License

TextExtract is released under the MIT License. See the [LICENSE](LICENSE) file for details.

## Credits

- [Google Vision API](https://cloud.google.com/vision) for advanced OCR capabilities
- [PyInstaller](https://pyinstaller.org) for application packaging
- [NSIS](https://nsis.sourceforge.io) for the installer system

---

© 2023-2024 TextExtract. All rights reserved.
