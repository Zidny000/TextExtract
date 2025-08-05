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
        if os.environ.get('GITHUB_TOKEN'):
            headers['Authorization'] = f"Bearer {os.environ.get('GITHUB_TOKEN')}"
        
        # Fetch releases from GitHub API
        response = requests.get(f"{GITHUB_API_BASE}/releases", headers=headers)
        response.raise_for_status()
        
        releases = response.json()
        return releases
    except Exception as e:
        logger.error(f"Error fetching releases from GitHub: {e}")
        return []

def get_cached_releases():
    """Get releases from cache or GitHub API with caching"""
    current_time = datetime.now().timestamp()
    
    # If cache is expired or empty, refresh it
    if (current_time - UPDATE_CACHE['last_updated'] > UPDATE_CACHE['cache_ttl'] or 
        UPDATE_CACHE['data'] is None):
        
        releases = _fetch_releases_from_github()
        
        if releases:
            UPDATE_CACHE['data'] = releases
            UPDATE_CACHE['last_updated'] = current_time
            
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
    try:
        # Get the client version and platform from query parameters
        client_version = request.args.get('version', '1.0.0')
        client_platform = request.args.get('platform', 'windows')
        
        # Get GitHub releases (cached)
        releases = get_cached_releases()
        
        if not releases:
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
