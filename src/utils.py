import os
import sys
import subprocess
import tempfile
import glob
from config import save_ocr_settings, DEFAULT_LANGUAGE

def ensure_paddle_installed():
    """Check if Paddle (base package) is installed and install it if needed."""
    # Check Python version for compatibility
    py_version = sys.version_info
    
    if py_version.major == 3 and 7 <= py_version.minor <= 10:
        print(f"Python {py_version.major}.{py_version.minor} is compatible with PaddlePaddle.")
    else:
        print(f"Warning: Python {py_version.major}.{py_version.minor} may not be fully compatible with PaddlePaddle.")
        print("PaddlePaddle works best with Python 3.7-3.10.")
    
    try:
        import paddle
        paddle_version = paddle.__version__
        print(f"PaddlePaddle {paddle_version} is already installed.")
        
        # Check if version is correct
        if paddle_version != "2.6.2":
            try:
                print(f"Updating PaddlePaddle from {paddle_version} to 2.6.2...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "paddlepaddle==2.6.2", "--force-reinstall"])
                print("PaddlePaddle updated successfully!")
            except subprocess.CalledProcessError as e:
                print(f"Warning: Failed to update PaddlePaddle: {e}")
                print("Continuing with current version.")
        return True
    except ImportError:
        # Paddle is not installed, attempt to install it
        try:
            print("Installing PaddlePaddle 2.6.2... This may take a few minutes.")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "paddlepaddle==2.6.2"])
            print("PaddlePaddle installed successfully!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to install PaddlePaddle: {e}")
            print("Try installing manually with: pip install paddlepaddle==2.6.2")
            return False

def ensure_paddleocr_installed():
    """Check if PaddleOCR is installed and install it if needed."""
    # First make sure Paddle is installed
    if not ensure_paddle_installed():
        print("Cannot install PaddleOCR because PaddlePaddle installation failed.")
        return False
        
    try:
        import paddleocr
        paddleocr_version = paddleocr.__version__
        print(f"PaddleOCR {paddleocr_version} is already installed.")
        
        # Check if version is what we want
        if paddleocr_version != "2.10.0":
            try:
                print(f"Updating PaddleOCR from {paddleocr_version} to 2.10.0...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "paddleocr==2.10.0", "--force-reinstall"])
                print("PaddleOCR updated successfully!")
            except subprocess.CalledProcessError as e:
                print(f"Warning: Failed to update PaddleOCR: {e}")
                print("Continuing with current version.")
        return True
    except ImportError:
        # PaddleOCR is not installed, attempt to install it
        try:
            print("Installing PaddleOCR 2.10.0... This may take a few minutes.")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "paddleocr==2.10.0"])
            print("PaddleOCR installed successfully!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to install PaddleOCR: {e}")
            print("This may be because PaddlePaddle installation is incomplete or incompatible.")
            return False

def get_paddleocr_model_dir():
    """Get the directory where PaddleOCR stores its models."""
    try:
        import paddle
        home_dir = os.path.expanduser('~')
        # PaddleOCR stores models in ~/.paddleocr
        return os.path.join(home_dir, '.paddleocr')
    except ImportError:
        return None

def check_paddleocr_models_downloaded():
    """Check if PaddleOCR models are already downloaded."""
    model_dir = get_paddleocr_model_dir()
    if not model_dir or not os.path.exists(model_dir):
        return False
        
    # Check for detection models
    det_models = glob.glob(os.path.join(model_dir, '**/ch_PP-OCRv3_det_infer'), recursive=True)
    if not det_models:
        return False
        
    # Check for recognition models based on the current language
    lang_mapping = {
        'en': 'en_PP-OCRv3_rec_infer',
        'ch': 'ch_PP-OCRv3_rec_infer',
        'fr': 'french_mobile_v2.0_rec_infer',
        'german': 'german_mobile_v2.0_rec_infer',
        'korean': 'korean_mobile_v2.0_rec_infer',
        'japan': 'japan_mobile_v2.0_rec_infer'
    }
    
    expected_rec_model = lang_mapping.get(DEFAULT_LANGUAGE, 'en_PP-OCRv3_rec_infer')
    rec_models = glob.glob(os.path.join(model_dir, f'**/{expected_rec_model}'), recursive=True)
    if not rec_models:
        return False
        
    # All required models are present
    return True

def download_paddleocr_models(lang=DEFAULT_LANGUAGE):
    """Force download of PaddleOCR models for the specified language."""
    try:
        # Import PaddleOCR
        from paddleocr import PaddleOCR
        
        # Initialize PaddleOCR which will download models
        ocr = PaddleOCR(use_angle_cls=True, lang=lang, show_log=True, use_gpu=False)
        
        # Create a small test image and run inference to ensure models are downloaded
        from PIL import Image
        import numpy as np
        
        # Create a blank test image
        img = Image.new('RGB', (100, 30), color='white')
        test_image_path = os.path.join(tempfile.gettempdir(), 'textextract_test.png')
        img.save(test_image_path)
        
        # Run inference which will trigger model download if not already downloaded
        result = ocr.ocr(test_image_path)
        
        # Clean up
        if os.path.exists(test_image_path):
            os.remove(test_image_path)
            
        return True
    except Exception as e:
        print(f"Error downloading PaddleOCR models: {e}")
        return False

def get_supported_languages():
    """Get list of supported languages for PaddleOCR."""
    paddleocr_langs = [
        "en", "fr", "german", "es", "it", "pt", "ru", "japan", "korean", 
        "ch", "chinese_cht", "arabic", "hi", "ug", "fa", "ur", "serbian", 
        "oc", "mr", "ne", "eu", "am", "mn", "vi"
    ]
    
    return paddleocr_langs
