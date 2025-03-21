import pyperclip
import time
import threading

# Create a lock for clipboard operations
clipboard_lock = threading.Lock()

def copy_to_clipboard(text):
    """
    Copy text to clipboard with thread safety and retry logic
    """
    if not text or text.strip() == "":
        print("No text to copy to clipboard")
        return False
        
    # Use a lock to prevent concurrent clipboard access
    with clipboard_lock:
        try:
            # Max retries for clipboard operations
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Clear clipboard first
                    pyperclip.copy('')
                    time.sleep(0.1)  # Small delay to ensure clipboard is cleared
                    
                    # Copy the text
                    pyperclip.copy(text)
                    time.sleep(0.2)  # Allow time for clipboard sync
                    
                    # Verify copy operation
                    clipboard_content = pyperclip.paste().strip()
                    if clipboard_content == text.strip():
                        print("✓ Copied to clipboard")
                        return True
                    else:
                        # Try again
                        time.sleep(0.3 * (attempt + 1))  # Increasing backoff delay
                        continue
                        
                except Exception as e:
                    # Specific exception, try again
                    print(f"Clipboard attempt {attempt+1} failed: {str(e)}")
                    time.sleep(0.3 * (attempt + 1))
                    
            # All retries failed
            print("Clipboard operation failed after multiple attempts")
            return False
                
        except Exception as e:
            print(f"Clipboard error: {str(e)}")
            return False