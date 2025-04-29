import os
import json
import base64
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
from database import db_init
from routes import register_routes

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["*"], 
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-CSRF-TOKEN", "X-Device-ID"],
        "supports_credentials": True,  # Important for cookies/auth
        "max_age": 86400  # Cache preflight requests for 1 day
    }
})  # Enable CORS for all routes
bcrypt = Bcrypt(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Setup rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["10000 per day", "1000 per hour"],
    storage_uri="memory://"
)

# Initialize database
try:
    db_init()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Database initialization error: {str(e)}")
    
# Register all application routes
register_routes(app)

# Legacy non-authenticated OCR endpoint - will be deprecated
@app.route('/api/ocr-legacy', methods=['POST'])
@limiter.limit("10 per minute")  # Add rate limiting
def ocr_legacy():
    """Legacy OCR endpoint that doesn't require authentication - to be deprecated"""
    from together import Together
    
    # Load Together.ai API key from environment
    TOGETHER_API_KEY = os.environ.get("TOGETHER_API_KEY")
    if not TOGETHER_API_KEY:
        logger.error("Together.ai API key not found. Please set the TOGETHER_API_KEY environment variable.")
        return jsonify({"error": "API key configuration error"}), 500
    
    # Initialize Together client
    together_client = Together(api_key=TOGETHER_API_KEY)
    
    try:
        # Get data from request
        data = request.json
        if not data or 'image' not in data:
            return jsonify({"error": "No image data provided"}), 400
        
        # Get the base64 encoded image
        img_base64 = data['image']
        
        # Get language if provided
        language = data.get('language', 'en')
        
        # Validate the client app ID if you implement app authentication
        app_id = request.headers.get('X-App-ID')
        if not app_id or app_id != "textextract-desktop-app":
            logger.warning(f"Unauthorized access attempt: {app_id}")
            return jsonify({"error": "Unauthorized"}), 401
        
        # Log the request (without the image data for privacy)
        logger.info(f"Legacy OCR request received: lang={language}, app_id={app_id}")
        
        # Prepare the prompt for text extraction
        prompt = "Extract and return only the exact text visible in this image without any modifications, reformatting, additional explanations, or extra characters. Preserve the text exactly as it appears, including all punctuation, spacing, and formatting. Do not add or enclose the text within any additional symbols such as triple backticks (```) or other formatting markers. Output only the raw text as it appears in the image."
        
        # Create the message with the image
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_base64}"
                        }
                    }
                ]
            }
        ]
        
        # Call the Together API with Llama-4-Scout-17B-16E-Instruct model
        response = together_client.chat.completions.create(
            model="meta-llama/Llama-4-Scout-17B-16E-Instruct",
            messages=messages,
            max_tokens=1024,
            temperature=0.1,  # Lower temperature for more focused output
            top_p=0.9
        )
        
        # Extract the text from the response
        text = response.choices[0].message.content.strip()
        
        # Show deprecation warning
        return jsonify({
            "text": text,
            "warning": "This endpoint is deprecated and will be removed in the future. Please use the authenticated API endpoint."
        })
        
    except Exception as e:
        logger.error(f"Error processing OCR request: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Root route for health check
@app.route('/', methods=['GET'])
def root():
    return jsonify({
        "service": "TextExtract OCR API", 
        "status": "running",
        "version": "1.0.0"
    })

if __name__ == '__main__':
    # For development only - use a production WSGI server in production
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 