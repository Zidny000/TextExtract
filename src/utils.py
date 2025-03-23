import os
import sys
import subprocess
import tempfile
import glob
from config import save_ocr_settings, DEFAULT_LANGUAGE

def ensure_tesseract_installed():
    """Check if Tesseract is installed and accessible."""
    try:
        # Try to import pytesseract
        import pytesseract
        
        # Try to get the tesseract version
        try:
            version = pytesseract.get_tesseract_version()
            print(f"Tesseract {version} is installed and accessible.")
            return True
        except Exception as e:
            print(f"pytesseract is installed but Tesseract executable is not found: {e}")
            
            # On Windows, check common installation paths
            if sys.platform.startswith('win'):
                # Look for bundled tesseract first
                bundled_tesseract_path = os.path.abspath(os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                    "bundled_tesseract", "tesseract.exe"
                ))
                
                if os.path.exists(bundled_tesseract_path):
                    print(f"Found bundled Tesseract at: {bundled_tesseract_path}")
                    pytesseract.pytesseract.tesseract_cmd = bundled_tesseract_path
                    return True
                    
                # Check common installation paths
                common_paths = [
                    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                ]
                
                for path in common_paths:
                    if os.path.exists(path):
                        print(f"Found Tesseract at: {path}")
                        pytesseract.pytesseract.tesseract_cmd = path
                        return True
                
                print("Tesseract not found. Please install it from: https://github.com/UB-Mannheim/tesseract/wiki")
                return False
            else:
                # On Linux/Mac, suggest installation commands
                if sys.platform.startswith('linux'):
                    print("Please install Tesseract with: sudo apt-get install tesseract-ocr")
                elif sys.platform.startswith('darwin'):
                    print("Please install Tesseract with: brew install tesseract")
                return False
                
    except ImportError:
        # pytesseract is not installed, attempt to install it
        try:
            print("Installing pytesseract... This may take a few moments.")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pytesseract"])
            print("pytesseract installed successfully!")
            
            # Now check if the Tesseract executable is available
            import pytesseract
            try:
                version = pytesseract.get_tesseract_version()
                print(f"Tesseract {version} is installed and accessible.")
                return True
            except Exception:
                # Suggest Tesseract installation based on platform
                if sys.platform.startswith('win'):
                    print("Please install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki")
                elif sys.platform.startswith('linux'):
                    print("Please install Tesseract with: sudo apt-get install tesseract-ocr")
                elif sys.platform.startswith('darwin'):
                    print("Please install Tesseract with: brew install tesseract")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"Failed to install pytesseract: {e}")
            print("Try installing manually with: pip install pytesseract")
            return False

def get_tesseract_language_dir():
    """Get the directory where Tesseract language data is stored."""
    try:
        import pytesseract
        
        # Try to get the Tesseract executable path
        tesseract_cmd = pytesseract.pytesseract.tesseract_cmd
        
        if tesseract_cmd and os.path.exists(tesseract_cmd):
            # Language data is typically in a "tessdata" directory
            # near the executable or in a standard location
            tesseract_dir = os.path.dirname(tesseract_cmd)
            
            # Check common relative paths
            for relative_path in ["tessdata", "../tessdata", "../../share/tessdata"]:
                lang_dir = os.path.join(tesseract_dir, relative_path)
                if os.path.exists(lang_dir):
                    return lang_dir
                    
            # On Windows, also check standard locations
            if sys.platform.startswith('win'):
                for base_path in [r'C:\Program Files\Tesseract-OCR', r'C:\Program Files (x86)\Tesseract-OCR']:
                    lang_dir = os.path.join(base_path, "tessdata")
                    if os.path.exists(lang_dir):
                        return lang_dir
                        
        # Fallback: check bundled location
        bundled_dir = os.path.abspath(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "bundled_tesseract", "tessdata"
        ))
        
        if os.path.exists(bundled_dir):
            return bundled_dir
            
        return None
    except ImportError:
        return None

def check_tesseract_language_installed(lang_code):
    """Check if a specific Tesseract language is installed."""
    # Convert language code to Tesseract format
    tesseract_lang = map_to_tesseract_lang(lang_code)
    
    # Get the language data directory
    lang_dir = get_tesseract_language_dir()
    
    if not lang_dir:
        return False
        
    # Check if the language file exists
    lang_file = os.path.join(lang_dir, f"{tesseract_lang}.traineddata")
    
    return os.path.exists(lang_file)

def map_to_tesseract_lang(lang_code):
    """Map language code to Tesseract language code format."""
    # Mapping from language codes to Tesseract language codes
    lang_mapping = {
        'en': 'eng',   # English
        'ch': 'chi_sim',  # Simplified Chinese
        'ja': 'jpn',   # Japanese
        'ko': 'kor',   # Korean
        'fr': 'fra',   # French
        'de': 'deu',   # German
        'es': 'spa',   # Spanish
        'it': 'ita',   # Italian
        'pt': 'por',   # Portuguese
        'ru': 'rus',   # Russian
        'ar': 'ara',   # Arabic
        'hi': 'hin',   # Hindi
        'vi': 'vie',   # Vietnamese
    }
    
    return lang_mapping.get(lang_code, 'eng')  # Default to English if not found

def get_supported_languages():
    """Get list of supported languages for Tesseract OCR."""
    # Common languages supported by Tesseract
    tesseract_langs = [
        "en",  # English (eng)
        "fr",  # French (fra)
        "de",  # German (deu)
        "es",  # Spanish (spa)
        "it",  # Italian (ita)
        "pt",  # Portuguese (por)
        "ru",  # Russian (rus)
        "ch",  # Simplified Chinese (chi_sim)
        "ja",  # Japanese (jpn)
        "ko",  # Korean (kor)
        "ar",  # Arabic (ara)
        "hi",  # Hindi (hin)
        "vi",  # Vietnamese (vie)
    ]
    
    # Filter to only languages that are actually installed
    available_langs = []
    for lang in tesseract_langs:
        if check_tesseract_language_installed(lang):
            available_langs.append(lang)
    
    return available_langs
