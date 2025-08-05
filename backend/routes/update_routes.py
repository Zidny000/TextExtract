"""
Update API endpoints for TextExtract.
Uses GitHub Releases to host actual update files.
"""

from flask import Blueprint, jsonify, request
import requests
import logging
import os
import json
from datetime import datetime

# Create a logger
logger = logging.getLogger(__name__)

# Create a blueprint for update routes
update_routes = Blueprint('update_routes', __name__)

# Simple rate limiting mechanism
IP_REQUESTS = {}
RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds
RATE_LIMIT_MAX = 50  # Maximum requests per IP in the window

def check_rate_limit(ip):
    """Check if an IP has exceeded the rate limit"""
    current_time = datetime.now().timestamp()
    
    # Clear old entries first (garbage collection)
    for stored_ip in list(IP_REQUESTS.keys()):
        last_time = IP_REQUESTS[stored_ip]["timestamp"]
        if current_time - last_time > RATE_LIMIT_WINDOW:
            del IP_REQUESTS[stored_ip]
    
    # Check/update current IP
    if ip in IP_REQUESTS:
        data = IP_REQUESTS[ip]
        # If within window, increment count
        if current_time - data["timestamp"] < RATE_LIMIT_WINDOW:
            data["count"] += 1
            return data["count"] <= RATE_LIMIT_MAX
        else:
            # Reset if outside window
            IP_REQUESTS[ip] = {"count": 1, "timestamp": current_time}
            return True
    else:
        # New IP address
        IP_REQUESTS[ip] = {"count": 1, "timestamp": current_time}
        return True

# GitHub repository information
GITHUB_REPO_OWNER = "Zidny000"
GITHUB_REPO_NAME = "textextract-releases"
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}"

# Update cache with TTL to avoid hitting GitHub API rate limits
UPDATE_CACHE = {
    'last_updated': 0,
    'cache_ttl': 3600,  # 1 hour in seconds
    'data': None
}

def _fetch_releases_from_github():
    """Fetch release information from GitHub API"""
    try:
        # Set User-Agent to avoid GitHub API rate limiting issues
        headers = {
            'User-Agent': 'textextract-releases-UpdateService/1.0',
        }
        
        # Add GitHub token for authenticated requests if available
        github_token = os.environ.get('GITHUB_TOKEN')
        if github_token:
            headers['Authorization'] = f"Bearer {github_token}"
            logger.info("Using authenticated GitHub API request")
        else:
            logger.warning("No GITHUB_TOKEN environment variable set - using unauthenticated requests with lower rate limits")
        
        # Try to fetch releases from GitHub API
        try:
            response = requests.get(f"{GITHUB_API_BASE}/releases", headers=headers, timeout=10)
            response.raise_for_status()
            releases = response.json()
            logger.info(f"Successfully fetched {len(releases)} releases from GitHub API")
            return releases
        except requests.exceptions.HTTPError as http_err:
            if response.status_code == 403 and 'rate limit exceeded' in response.text.lower():
                logger.error("GitHub API rate limit exceeded")
                # Fall back to cached data if available, otherwise use static fallback
                if UPDATE_CACHE['data']:
                    logger.info("Using cached release data due to rate limit")
                    return UPDATE_CACHE['data']
                else:
                    logger.info("Using fallback release data")
                    return _get_fallback_release_data()
            else:
                logger.error(f"HTTP error when fetching releases: {http_err}")
                raise
    except Exception as e:
        logger.error(f"Error fetching releases from GitHub: {e}")
        # Try to use fallback data
        return _get_fallback_release_data()

def _get_fallback_release_data():
    """Get fallback release data when GitHub API is unavailable"""
    try:
        # First try to load from a local file
        fallback_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'latest_release.json')
        if os.path.exists(fallback_file):
            try:
                with open(fallback_file, 'r') as f:
                    data = json.load(f)
                logger.info(f"Loaded fallback release data from {fallback_file}")
                return data if isinstance(data, list) else [data]
            except Exception as e:
                logger.error(f"Error loading fallback release data: {e}")
        
        # If no file or error loading, use hardcoded data as last resort
        logger.info("Using hardcoded fallback release data")
        return [{
            "tag_name": "v1.0.0",
            "published_at": "2024-05-20T00:00:00Z",
            "body": "Initial release of TextExtract with automatic update functionality.",
            "draft": False,
            "prerelease": False,
            "assets": [{
                "name": "TextExtract-1.0.0-windows.exe",
                "browser_download_url": "https://github.com/Zidny000/textextract-releases/releases/download/v1.0.0/TextExtract-Setup-1.0.0.exe",
                "size": 15000000  # Approximate size in bytes
            }]
        }]
    except Exception as e:
        logger.error(f"Error getting fallback release data: {e}")
        return []

def get_cached_releases():
    """Get releases from cache or GitHub API with caching"""
    current_time = datetime.now().timestamp()
    
    # If cache is expired or empty, refresh it
    if (current_time - UPDATE_CACHE['last_updated'] > UPDATE_CACHE['cache_ttl'] or 
        UPDATE_CACHE['data'] is None):
        
        # Attempt to fetch new data
        releases = _fetch_releases_from_github()
        
        # Only update cache if we got valid data
        if releases:
            UPDATE_CACHE['data'] = releases
            UPDATE_CACHE['last_updated'] = current_time
            
            # Save the latest release data to a file for fallback purposes
            try:
                # Ensure data directory exists
                data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
                os.makedirs(data_dir, exist_ok=True)
                
                # Write latest release to a JSON file
                with open(os.path.join(data_dir, 'latest_release.json'), 'w') as f:
                    json.dump(releases, f, indent=2)
                logger.debug("Successfully saved latest release data to file for fallback")
            except Exception as e:
                logger.warning(f"Failed to save release data to file: {e}")
    
    # Return cached data or empty list if cache is empty
    return UPDATE_CACHE['data'] or []

def parse_version(version_str):
    """Parse a version string into a tuple for comparison"""
    # Strip 'v' prefix if present
    if version_str.startswith('v'):
        version_str = version_str[1:]
        
    # Split by dots and convert to integers
    try:
        return tuple(map(int, version_str.split('.')))
    except (ValueError, AttributeError):
        return (0, 0, 0)  # Default for invalid versions

def is_newer_version(version1, version2):
    """Compare two version strings and return True if version1 is newer than version2"""
    v1 = parse_version(version1)
    v2 = parse_version(version2)
    return v1 > v2

@update_routes.route('/api/updates/latest', methods=['GET'])
def get_latest_update():
    """Get information about the latest available update"""
    # Get request details for better logging
    client_ip = request.remote_addr
    client_agent = request.user_agent.string if request.user_agent else "Unknown"
    
    try:
        # Check rate limiting
        if not check_rate_limit(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return jsonify({
                "available": False,
                "message": "Rate limit exceeded. Please try again later.",
                "error": "rate_limit_exceeded"
            }), 429
        
        # Log the update check request
        logger.info(f"Update check: IP={client_ip}, Agent={client_agent}")
        
        # Get the client version and platform from query parameters
        client_version = request.args.get('version', '1.0.0')
        client_platform = request.args.get('platform', 'windows')
        client_channel = request.args.get('channel', 'stable')
        
        logger.info(f"Client details: Version={client_version}, Platform={client_platform}, Channel={client_channel}")
        
        # Get GitHub releases (cached)
        releases = get_cached_releases()
        
        if not releases:
            logger.warning("No releases found in cache or from GitHub API")
            return jsonify({
                "available": False,
                "message": "No releases found"
            }), 200
            
        # Find the latest non-prerelease, non-draft release
        latest_release = None
        for release in releases:
            # Skip drafts and prereleases
            if release.get('draft', False) or release.get('prerelease', False):
                continue
                
            latest_release = release
            break
        
        if not latest_release:
            return jsonify({
                "available": False,
                "message": "No stable releases found"
            }), 200
            
        # Get the release version (strip 'v' prefix if present)
        latest_version = latest_release['tag_name']
        if latest_version.startswith('v'):
            latest_version = latest_version[1:]
            
        # Check if update is needed
        if not is_newer_version(latest_version, client_version):
            return jsonify({
                "available": False,
                "message": "You already have the latest version"
            }), 200
            
        # Find the appropriate asset for the client platform
        asset = None
        for a in latest_release.get('assets', []):
            if client_platform.lower() in a['name'].lower() and a['name'].endswith('.exe'):
                asset = a
                break
                
        if not asset:
            return jsonify({
                "available": False,
                "message": f"No compatible installer found for {client_platform}"
            }), 200
            
        print(f"Latest version: {latest_version}, Client version: {client_version}")
        # Return update information
        return jsonify({
            "available": True,
            "version": latest_version,
            "release_date": latest_release['published_at'],
            "download_url": asset['browser_download_url'],
            "file_size": asset['size'],
            "release_notes": latest_release['body'],
            "force_update": "CRITICAL" in latest_release['body'].upper(),
            "silent_install": True,
            "requires_admin": False,
            "min_version_required": "1.0.0"  # You can update this based on release notes
        }), 200
            
    except Exception as e:
        logger.error(f"Error retrieving update information: {e}")
        return jsonify({
            "error": str(e),
            "available": False
        }), 500

# Save update information to a local JSON file for analytics (optional)
@update_routes.route('/api/updates/track', methods=['POST'])
def track_update():
    """Track update information for analytics"""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400
            
        # Add timestamp
        data['timestamp'] = datetime.now().isoformat()
        
        # Save to file (in a production environment, you'd use a database)
        updates_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'updates')
        os.makedirs(updates_dir, exist_ok=True)
        
        # Generate a unique filename
        filename = f"update_track_{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.urandom(4).hex()}.json"
        filepath = os.path.join(updates_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(data, f)
            
        return jsonify({"success": True}), 200
        
    except Exception as e:
        logger.error(f"Error tracking update: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
