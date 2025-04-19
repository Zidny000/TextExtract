#!/usr/bin/env python
"""
Prepare Google Vision API credentials for SaaS deployment

This script helps developers prepare their Google Vision API credentials for embedding in the TextExtract application.
It takes a Google Cloud service account JSON key file and encodes it as a string that can be set as an environment
variable for the application.
"""

import argparse
import base64
import json
import os
import sys

def encode_credentials(json_file_path, use_base64=False):
    """Encode credentials from a JSON file, optionally as base64"""
    try:
        with open(json_file_path, 'r') as f:
            credentials_json = json.load(f)
            
        # Format the credentials as a string
        credentials_str = json.dumps(credentials_json)
        
        if use_base64:
            # Base64 encode the string
            encoded = base64.b64encode(credentials_str.encode('utf-8')).decode('utf-8')
            result = f"base64:{encoded}"
        else:
            result = credentials_str
            
        return result
    except Exception as e:
        print(f"Error encoding credentials: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Prepare Google Vision API credentials for TextExtract SaaS deployment")
    parser.add_argument("json_file", help="Path to the Google Cloud service account JSON key file")
    parser.add_argument("--base64", action="store_true", help="Encode the credentials as base64 (recommended for security)")
    parser.add_argument("--export", action="store_true", help="Export as environment variable command (for shell scripts)")
    parser.add_argument("--hardcode", action="store_true", help="Generate code for hardcoding in config.py")
    parser.add_argument("--output", help="Write the encoded credentials to a file instead of stdout")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.json_file):
        print(f"Error: File {args.json_file} does not exist")
        sys.exit(1)
        
    # Always use base64 for hardcoded credentials
    use_base64 = args.base64 or args.hardcode
    
    encoded = encode_credentials(args.json_file, use_base64)
    if not encoded:
        sys.exit(1)
        
    if args.hardcode:
        # Format for direct inclusion in config.py
        result = f'HARDCODED_CREDENTIALS = "{encoded}"'
    elif args.export:
        # Format as export command for shell scripts
        if os.name == 'nt':  # Windows
            result = f"set GOOGLE_VISION_CREDENTIALS={encoded}"
        else:  # Unix/Linux/Mac
            result = f"export GOOGLE_VISION_CREDENTIALS='{encoded}'"
    else:
        result = encoded
        
    if args.output:
        with open(args.output, 'w') as f:
            f.write(result)
        print(f"Credentials written to {args.output}")
    else:
        print(result)
        
    # Always show usage hint
    print("\nUsage instructions:")
    
    if args.hardcode:
        print("1. Copy the line above and replace the HARDCODED_CREDENTIALS line in src/config.py")
        print("2. This will permanently embed your credentials in the application")
    else:
        print("1. Set this as an environment variable before building the application:")
        if os.name == 'nt':  # Windows
            print(f"   set GOOGLE_VISION_CREDENTIALS=<credentials>")
        else:  # Unix/Linux/Mac
            print(f"   export GOOGLE_VISION_CREDENTIALS='<credentials>'")
        print("2. Or embed it directly in src/config.py")
        print("   Run with --hardcode to get the exact line to add to config.py")
    
if __name__ == "__main__":
    main() 