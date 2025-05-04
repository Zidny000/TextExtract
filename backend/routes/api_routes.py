import os
import time
import logging
import json
from flask import Blueprint, request, jsonify, g
from database.models import User, ApiRequest, Device
from database.db import supabase
from auth import login_required, extract_device_info
from together import Together

logger = logging.getLogger(__name__)
api_routes = Blueprint('api', __name__, url_prefix='/api')

# Initialize Together client
TOGETHER_API_KEY = os.environ.get("TOGETHER_API_KEY")
together_client = Together(api_key=TOGETHER_API_KEY)

@api_routes.route('/ocr', methods=['POST'])
@login_required
def ocr_proxy():
    """
    OCR endpoint that requires authentication
    """
    start_time = time.time()
    request_size = 0
    response_size = 0
    
    try:
        # Get data from request
        data = request.json
        if not data or 'image' not in data:
            return jsonify({"error": "No image data provided"}), 400
        
        # Get the base64 encoded image
        img_base64 = data['image']
        request_size = len(img_base64)
        
        # Get language if provided
        language = data.get('language', 'en')
        
        # Extract device info for tracking
        device_info = extract_device_info(request)
        device_id = request.headers.get("X-Device-ID")
        
        # Register or update device if ID is provided
        if device_id:
            Device.register(g.user_id, device_id, device_info)
        
        # Check if user can make another request based on their plan
        if not User.can_make_request(g.user_id):
            return jsonify({
                "error": "Daily API request limit reached",
                "limit": g.user.get("max_requests_per_day", 50)
            }), 429
        
        # Create an API request record for tracking
        api_request = ApiRequest.create(
            user_id=g.user_id,
            request_type="ocr",
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
            device_info=device_info
        )
        
        # Log the request (without the image data for privacy)
        logger.info(f"OCR request received: lang={language}, user_id={g.user_id}")
        
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
        response_size = len(text)
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Update the API request record with final status
        if api_request and 'id' in api_request:
            ApiRequest.update_status(
                api_request['id'],
                status="success",
                response_time_ms=response_time_ms,
                request_size_bytes=request_size,
                response_size_bytes=response_size
            )
        
        # Return the extracted text
        return jsonify({
            "text": text,
            "meta": {
                "processing_time_ms": response_time_ms,
                "remaining_requests": g.user.get("max_requests_per_day", 50) - User.get_monthly_request_count(g.user_id)
            }
        })
        
    except Exception as e:
        # Calculate error response time
        error_response_time_ms = int((time.time() - start_time) * 1000)
        
        # Update the API request record with error status
        if 'api_request' in locals() and api_request and 'id' in api_request:
            ApiRequest.update_status(
                api_request['id'],
                status="error",
                response_time_ms=error_response_time_ms,
                error_message=str(e),
                request_size_bytes=request_size
            )
        
        logger.error(f"Error processing OCR request: {str(e)}")
        return jsonify({
            "error": "Failed to process image",
            "details": str(e)
        }), 500

@api_routes.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint (no authentication required)
    """
    try:
        # Simple database check
        supabase.table("users").select("id", count="exact").limit(1).execute()
        
        return jsonify({
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": time.time()
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }), 500 