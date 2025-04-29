# Backend CORS Configuration Fix

To properly handle CORS in your Flask backend, follow these steps:

## 1. Update your `app.py` file

Replace the current simple CORS initialization:

```python
from flask_cors import CORS
# ...
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
```

With a more specific configuration:

```python
from flask_cors import CORS
# ...
app = Flask(__name__)

# Configure CORS with specific allowed origins
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:3000", "https://yourdomain.com"], 
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-CSRF-TOKEN", "X-Device-ID"],
        "supports_credentials": True,  # Important for cookies/auth
        "max_age": 86400  # Cache preflight requests for 1 day
    }
})
```

Make sure to replace `"https://yourdomain.com"` with your actual production domain.

## 2. Add the frontend URL to environment variables (optional but recommended)

Add to your `.env` file:
```
FRONTEND_URL=http://localhost:3000
PRODUCTION_URL=https://yourdomain.com
```

Then modify your CORS setup to use these:

```python
# Get allowed origins from environment
allowed_origins = [
    os.environ.get("FRONTEND_URL", "http://localhost:3000")
]

# Add production URL if in production environment
if os.environ.get("ENVIRONMENT") == "production" and os.environ.get("PRODUCTION_URL"):
    allowed_origins.append(os.environ.get("PRODUCTION_URL"))

# Configure CORS with specific allowed origins
CORS(app, resources={
    r"/*": {
        "origins": allowed_origins,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-CSRF-TOKEN", "X-Device-ID"],
        "supports_credentials": True,
        "max_age": 86400
    }
})
```

## 3. Ensure your server responds properly to preflight OPTIONS requests

Flask-CORS should handle this automatically, but make sure your API routes do not accidentally override the OPTIONS method handlers.

## 4. Test with your frontend

After making these changes, restart your backend server and test the logout functionality from your frontend. The CORS errors should be resolved.

## 5. Additional security considerations

- Review your CSRF protection to ensure it works well with your CORS policy
- Consider adding rate limiting for logout requests to prevent abuse
- If you're using cookies for authentication (not just JWT), make sure to set appropriate SameSite attributes 