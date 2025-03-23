#!/usr/bin/env python
"""
Tesseract OCR Integration Test Script for TextExtract

This script tests the integration of Tesseract OCR with the TextExtract application.
It verifies pytesseract and Tesseract are installed and working.
"""

import os
import sys
import tempfile
import subprocess

print(f"Python version: {sys.version}")

# Make sure Pillow is installed
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Installing Pillow (PIL)...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
    from PIL import Image, ImageDraw, ImageFont

# Check if pytesseract is installed
try:
    import pytesseract
    print(f"pytesseract package is installed")
except ImportError:
    print("ERROR: pytesseract is not installed")
    print("Installing pytesseract...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pytesseract"])
        print("pytesseract installed successfully")
        import pytesseract
    except subprocess.CalledProcessError as e:
        print(f"Failed to install pytesseract: {e}")
        print("You may need to install it manually:")
        print("pip install pytesseract")
        sys.exit(1)
    except ImportError:
        print("Failed to import pytesseract even after installation attempt")
        sys.exit(1)

# Check Tesseract installation
def check_tesseract_installation():
    # First, try to get the Tesseract version
    try:
        tesseract_version = pytesseract.get_tesseract_version()
        print(f"Tesseract version: {tesseract_version}")
        print("✅ Tesseract is installed and accessible")
        return True
    except Exception as e:
        print(f"ERROR: Failed to get Tesseract version: {e}")
        
    # On Windows, check common installation paths
    if sys.platform.startswith('win'):
        print("Checking for Tesseract installation on Windows...")
        
        # Define common paths where Tesseract might be installed
        common_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        ]
        
        # Check for bundled Tesseract
        script_dir = os.path.dirname(os.path.abspath(__file__))
        bundled_path = os.path.join(script_dir, "bundled_tesseract", "tesseract.exe")
        if os.path.exists(bundled_path):
            print(f"Found bundled Tesseract at: {bundled_path}")
            pytesseract.pytesseract.tesseract_cmd = bundled_path
            return True
        
        # Check common installation paths
        for path in common_paths:
            if os.path.exists(path):
                print(f"Found Tesseract at: {path}")
                pytesseract.pytesseract.tesseract_cmd = path
                return True
        
        print("Tesseract executable not found in common locations.")
        print("Please install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki")
        print("Or specify the path to tesseract.exe manually by setting:")
        print("pytesseract.pytesseract.tesseract_cmd = r'path_to_tesseract.exe'")
        return False
    else:
        # On Linux/Mac, try to run the command to check if it's installed
        try:
            result = subprocess.run(["tesseract", "--version"], 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE,
                                     text=True)
            if result.returncode == 0:
                print(f"Tesseract found: {result.stdout.splitlines()[0]}")
                return True
            else:
                print("Tesseract command failed.")
        except FileNotFoundError:
            print("Tesseract executable not found in PATH.")
            
        # Provide installation instructions based on OS
        if sys.platform.startswith('linux'):
            print("On Ubuntu/Debian, install Tesseract with:")
            print("sudo apt-get install tesseract-ocr")
            print("sudo apt-get install libtesseract-dev")
        elif sys.platform.startswith('darwin'):
            print("On macOS, install Tesseract with Homebrew:")
            print("brew install tesseract")
        
        return False

# Create a test image with text
def create_test_image():
    # Create an image with white background
    img = Image.new('RGB', (400, 150), color='white')
    d = ImageDraw.Draw(img)
    
    # Try to use a common font
    try:
        if os.name == 'nt':  # Windows
            font = ImageFont.truetype("arial.ttf", 36)
        else:  # Linux/Mac
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    except Exception as e:
        print(f"Font loading error: {e}")
        # If font not found, use default
        font = None
    
    # Draw text
    d.text((20, 50), "Hello, Tesseract OCR!", fill='black', font=font)
    
    # Save the image to a temporary file
    temp_file = os.path.join(tempfile.gettempdir(), "tesseract_test.png")
    img.save(temp_file)
    print(f"Created test image at: {temp_file}")
    
    return temp_file

# Test Tesseract OCR functionality
def test_tesseract():
    # First check if Tesseract is properly installed
    if not check_tesseract_installation():
        print("❌ Tesseract installation check failed.")
        return
    
    try:
        # Create test image
        test_image = create_test_image()
        
        print("Running OCR on test image...")
        
        # Try different page segmentation modes if needed
        configs = ['--psm 6']  # Assume a single block of text
        
        for config in configs:
            text = pytesseract.image_to_string(Image.open(test_image), config=config)
            print(f"\nOCR Result with {config}:")
            print(text)
            
            if text and "Hello" in text:
                print("\n✅ Tesseract OCR test successful!")
                break
        else:
            print("\n❌ OCR returned unclear results")
            print("You might need to check Tesseract language packages are installed.")
        
        # Get information about the image
        try:
            print("\nDetailed OCR Data:")
            data = pytesseract.image_to_data(Image.open(test_image), output_type=pytesseract.Output.DICT)
            for i, text in enumerate(data['text']):
                if text.strip():
                    conf = int(data['conf'][i])
                    print(f"Word: {text}, Confidence: {conf}%")
        except Exception as e:
            print(f"Could not get detailed OCR data: {e}")
        
        # Clean up
        if os.path.exists(test_image):
            os.remove(test_image)
            
    except Exception as e:
        print(f"\n❌ Error during OCR test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 50)
    print("Tesseract OCR Integration Test")
    print("=" * 50)
    print()
    
    # Test Tesseract OCR functionality
    test_tesseract() 