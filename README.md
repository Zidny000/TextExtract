# TextExtract - Screen Text Extraction Tool

TextExtract is a screen text extraction tool using OCR (Optical Character Recognition) to capture text from anywhere on your screen. Perfect for copying text from applications, images, videos, or any other screen content that doesn't allow normal text selection.

## Features

- **Quick Text Extraction**: Select any area on your screen and extract text using OCR technology
- **Multi-Monitor Support**: Works with multi-monitor setups, allowing you to choose which monitor to capture from
- **Visual Control Panel**: Easy-to-use floating control panel for quick access to features
- **System Tray Integration**: Stays out of your way in the system tray until you need it
- **Keyboard Shortcuts**: Quick access using convenient keyboard shortcuts
- **Desktop Integration**: Proper Windows desktop integration with Start Menu entries and desktop shortcuts
- **Subscription Plans**: Free and premium tiers with flexible payment options (PayPal and Stripe)
- **User Account Management**: Web portal for managing your subscription and profile

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

4. Build the installer:
   ```
   build_installer.bat
   ```

5. The installer will be created in the project directory as `TextExtract_Setup.exe`

## Uninstallation

TextExtract can be uninstalled like any standard Windows application:

1. Go to Windows Settings > Apps > Apps & features
2. Find "TextExtract" in the list and click "Uninstall"
3. Follow the uninstallation wizard

Alternatively:
1. Open the Control Panel > Programs > Programs and Features
2. Select "TextExtract" and click "Uninstall"

## Subscription Plans

TextExtract offers different subscription tiers to meet your needs:

- **Free Tier**: Basic access with limited monthly OCR requests and device connections
- **Basic Tier**: Increased monthly OCR requests, multiple device support, and priority processing

### Payment Options

TextExtract supports the following payment methods:
- **Stripe**: Secure credit card payments
- **PayPal**: Convenient PayPal account payments

All payments are processed securely through our trusted payment processors. Subscription management is available through the web portal.

## License

TextExtract is released under the MIT License. See the [LICENSE](LICENSE) file for details.

## Credits

- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) for optical character recognition
- [PyInstaller](https://pyinstaller.org) for application packaging
- [NSIS](https://nsis.sourceforge.io) for the installer system
- [Stripe](https://stripe.com) for payment processing
- [PayPal](https://paypal.com) for payment processing
- [Together.ai](https://together.ai) for advanced OCR capabilities

---

© 2023-2025 TextExtract. All rights reserved.
