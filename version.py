"""
Version information for TextExtract.
This file is used to maintain the version information across the project.
"""

# Version information
__version__ = "1.0.0"
__author__ = "TextExtract"
__author_email__ = "contact@textextract.app"  # Replace with actual email if available
__license__ = "MIT"
__copyright__ = f"Copyright (c) 2025, {__author__}"
__website__ = "https://textextract1.onrender.com/"  # Replace with actual website if available
__description__ = "Screen text extraction tool using OCR"

# Build information
__build__ = "stable"  # Can be "dev", "alpha", "beta", "rc", "stable"
__build_date__ = "2024-05-20"  # Update with each release

# Application identifiers
APP_NAME = "TextExtract"
APP_ID = "com.textextract.app"  # Unique application identifier

# Windows registry specific
REGISTRY_PATH = r"Software\TextExtract"

# Update system configuration
ENABLE_AUTO_UPDATE = True
UPDATE_URL = "/api/updates/latest"  # API endpoint for update information (path only, domain added in updater)
UPDATE_CHECK_INTERVAL_HOURS = 24  # Check for updates once a day
UPDATE_CHANNEL = "stable"  # Can be "stable", "beta", or "dev" 