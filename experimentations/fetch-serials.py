#!/usr/bin/python3
#
# This script was generated using Gemini (model "Thinking with 3 Pro", whatever that means 🤷)
# Here is the prompt I used:
# BEGIN PROMPT
# * There is the https://cdimage.ubuntu.com/ server with the following directory tree:
#   /<product>/<type/<serial>
# * `<type>` can be any value in the following: daily, daily-live, daily-preinstalled, daily-minimal
# * `<serial>` is usually a date in the form 20251201, but sometimes is 20251201.1
# * Please write a Python script that browse this server and gets the latest serial for each product/type combination 
# END PROMPT
#
# This version 2 with updated prompt is slightly better than previous one, but still has some weirdnesses:
#   * `import sys`, but not using it? That module must be way too common in the training data it's now mandatory to write Python 😂
#   * Line 77: why did it think that `dists` and `pool` where existing folders? Good idea to skip known bad directories though.
#   * Lines 80, 87: we still have bad URL concatenation
#   * Line 95: `parsed` variable: what's that naming?
# At least now the output is looking more like what I need, so let's start with that and humanly iterate.

import requests
from bs4 import BeautifulSoup
import re
import sys

# Configuration
BASE_URL = "https://cdimage.ubuntu.com"
ALLOWED_TYPES = {'daily', 'daily-live', 'daily-preinstalled', 'daily-minimal'}

def get_links(url):
    """
    Fetches the HTML content of a directory listing and returns a list of 
    subdirectory names (ending with '/').
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        links = []
        for link in soup.find_all('a'):
            href = link.get('href')
            # Apache directory listings provide relative links.
            # We look for directories (ending in /) and ignore parent links.
            if href and href.endswith('/') and not href.startswith('?') and href not in ['/', '../']:
                links.append(href.rstrip('/'))
        return links
    except requests.exceptions.RequestException as e:
        # Silently fail for 404s or permission errors on specific folders
        # print(f"Skipping {url}: {e}", file=sys.stderr)
        return []

def parse_serial(serial_str):
    """
    Parses a serial string into a tuple (date, version) for accurate sorting.
    Example: '20251201'   -> (20251201, 0)
    Example: '20251201.1' -> (20251201, 1)
    """
    # Regex to match YYYYMMDD and optional .Version
    match = re.match(r'^(\d{8})(?:\.(\d+))?$', serial_str)
    if match:
        date_part = int(match.group(1))
        # If no suffix version is present, assume 0
        version_part = int(match.group(2)) if match.group(2) else 0
        return (date_part, version_part)
    return None

def main():
    print(f"Browsing {BASE_URL} for latest serials...\n")
    print(f"{'Product':<25} | {'Type':<20} | {'Latest Serial'}")
    print("-" * 65)

    # Step 1: Browse root to find all products
    products = get_links(BASE_URL + "/")
    
    for product in products:
        # Skip common non-product directories to save time/errors
        if product in ['releases', 'dists', 'pool']:
            continue

        product_url = f"{BASE_URL}/{product}/"
        
        # Step 2: Browse the product directory to find types
        types = get_links(product_url)
        
        for type_name in types:
            if type_name in ALLOWED_TYPES:
                type_url = f"{product_url}{type_name}/"
                
                # Step 3: Browse the type directory to find serials
                subdirs = get_links(type_url)
                
                valid_serials = []
                for subdir in subdirs:
                    # 'current' and 'pending' are often symlinks, but we want the actual serial date
                    parsed = parse_serial(subdir)
                    if parsed:
                        valid_serials.append({'original': subdir, 'parsed': parsed})
                
                if valid_serials:
                    # Sort by the parsed tuple (Date, Version) in descending order
                    valid_serials.sort(key=lambda x: x['parsed'], reverse=True)
                    latest_serial = valid_serials[0]['original']
                    
                    print(f"{product:<25} | {type_name:<20} | {latest_serial}")

if __name__ == "__main__":
    main()