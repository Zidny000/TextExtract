#!/usr/bin/env python
"""
PaddleOCR Integration Test Script for TextExtract

This script tests the integration of PaddleOCR with the TextExtract application.
It verifies PaddlePaddle 2.6.2 and PaddleOCR 2.10.0 are installed and working.
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

# Check if PaddlePaddle is installed
try:
    import paddle
    paddle_version = paddle.__version__
    print(f"PaddlePaddle version: {paddle_version}")
    
    if paddle_version != "2.6.2":
        print(f"WARNING: PaddlePaddle version {paddle_version} found, but 2.6.2 is recommended")
        if input("Do you want to install PaddlePaddle 2.6.2? (y/n) ").lower() == 'y':
            subprocess.check_call([sys.executable, "-m", "pip", "install", "paddlepaddle==2.6.2", "--force-reinstall"])
            # Re-import to get updated version
            import importlib
            importlib.reload(paddle)
            print(f"Updated PaddlePaddle version: {paddle.__version__}")
    else:
        print("✅ Correct PaddlePaddle version detected")
except ImportError:
    print("ERROR: PaddlePaddle is not installed")
    print("Installing PaddlePaddle 2.6.2...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "paddlepaddle==2.6.2"])
        print("PaddlePaddle installed successfully")
        import paddle
        print(f"PaddlePaddle version: {paddle.__version__}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install paddlepaddle: {e}")
        print("You may need to install it manually:")
        print("pip install paddlepaddle==2.6.2")
        sys.exit(1)
    except ImportError:
        print("Failed to import paddle even after installation attempt")
        sys.exit(1)

# Check if PaddleOCR is installed
try:
    import paddleocr
    paddleocr_version = paddleocr.__version__
    print(f"PaddleOCR version: {paddleocr_version}")
    
    if paddleocr_version != "2.10.0":
        print(f"WARNING: PaddleOCR version {paddleocr_version} found, but 2.10.0 is recommended")
        if input("Do you want to install PaddleOCR 2.10.0? (y/n) ").lower() == 'y':
            subprocess.check_call([sys.executable, "-m", "pip", "install", "paddleocr==2.10.0", "--force-reinstall"])
            # Re-import to get updated version
            import importlib
            importlib.reload(paddleocr)
            print(f"Updated PaddleOCR version: {paddleocr.__version__}")
    else:
        print("✅ Correct PaddleOCR version detected")
except ImportError:
    print("ERROR: PaddleOCR is not installed")
    print("Installing PaddleOCR 2.10.0...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "paddleocr==2.10.0"])
        print("PaddleOCR installed successfully")
        import paddleocr
        print(f"PaddleOCR version: {paddleocr.__version__}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install paddleocr: {e}")
        print("You may need to install it manually:")
        print("pip install paddleocr==2.10.0")
        sys.exit(1)

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
    d.text((20, 50), "Hello, PaddleOCR!", fill='black', font=font)
    
    # Save the image to a temporary file
    temp_file = os.path.join(tempfile.gettempdir(), "paddleocr_test.png")
    img.save(temp_file)
    print(f"Created test image at: {temp_file}")
    
    return temp_file

# Test PaddleOCR functionality
def test_paddleocr():
    try:
        from paddleocr import PaddleOCR
        
        # Create test image
        test_image = create_test_image()
        
        print("Initializing PaddleOCR (this will download models if not already downloaded)...")
        print("This may take several minutes on first run.")
        ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=True, use_gpu=False)
        
        print("Running OCR on test image...")
        result = ocr.ocr(test_image)
        
        # Display results
        if result and len(result) > 0:
            if isinstance(result[0], list):
                # New structure in PaddleOCR 2.10.0
                print("\nOCR Results:")
                for line in result[0]:
                    if len(line) >= 2:
                        print(f"Text: {line[1][0]}, Confidence: {line[1][1]:.4f}")
            else:
                # Older structure
                print("\nOCR Results:")
                for line in result:
                    for word_info in line:
                        if len(word_info) >= 2:
                            print(f"Text: {word_info[1][0]}, Confidence: {word_info[1][1]:.4f}")
            
            print("\n✅ PaddleOCR test successful!")
        else:
            print("\n❌ OCR returned no results")
            print("This can sometimes happen if the models are not fully downloaded.")
            print("Try running the script again.")
        
        # Clean up
        if os.path.exists(test_image):
            os.remove(test_image)
            
    except Exception as e:
        print(f"\n❌ Error during OCR test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 50)
    print("PaddleOCR Integration Test")
    print("=" * 50)
    print()
    
    # Test PaddleOCR functionality
    test_paddleocr() 