#!/usr/bin/python3
#
# This script was generated using Gemini (model "Thinking with 3 Pro", whatever that means 🤷)
# Here is the prompt I used:
# BEGIN PROMPT
# * There is the https://cdimage.ubuntu.com/ server with the following directory tree:
#   /<product>/<type/<serial>
# * `<type>` can be any value in the following: daily, daily-live, daily-preinstalled, daily-minimal
# * `<serial>` is usually a date in the form 20251201, but sometimes is 20251201.1
# * Please write a Python script that browse this server and gets the latest serial for each product, along with its type
# END PROMPT
#
# We can see that its not too bad, but also has some weirdnesses:
#   * line 63, variable `ver_part` could have been named `version_part`. Why such a shortcut?
#   * lines 87 and 93, the `found_any_type` variable is set but never used. WTF?
#   * lines 85 and 107, what's that mess with the `best_type` variable? It's never compared, how is it the best? Just use `type_name`!
#   * In overall, URL concatenation with `+` is very bad practice. It happens to work by accident because it's carrying
#     both `product_dir` and `product_name`, but it's definitely not pretty.
#   * Don't get me started on error handling, and returning -1 instead of raising exceptions.

import requests
from bs4 import BeautifulSoup
import re

# Configuration
BASE_URL = "https://cdimage.ubuntu.com/"
TYPES = ['daily', 'daily-live', 'daily-preinstalled', 'daily-minimal']

def get_soup(url):
    """Fetches the URL and returns a BeautifulSoup object."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except requests.RequestException:
        return None

def get_directories(url):
    """Returns a list of subdirectories (names ending with /) from a given URL."""
    soup = get_soup(url)
    if not soup:
        return []
    
    dirs = []
    for link in soup.find_all('a'):
        href = link.get('href')
        # Filter for directories, ignoring parent directory links and sorting params
        if href and href.endswith('/') and not href.startswith('/') and not href.startswith('?') and href != '../':
            dirs.append(href)
    return dirs

def parse_serial(serial_str):
    """
    Parses a serial string (e.g., '20251201/' or '20251201.1/') into a comparable tuple.
    Returns (date_int, version_int). Version defaults to -1 if not present,
    assuming '20251201' is older than '20251201.1' if strict ordering is needed,
    but typically versionless comes before versioned.
    """
    clean_str = serial_str.rstrip('/')
    match = re.match(r'^(\d{8})(?:\.(\d+))?$', clean_str)
    if match:
        date_part = int(match.group(1))
        ver_part = int(match.group(2)) if match.group(2) else 0
        return (date_part, ver_part)
    return None

def main():
    print(f"Browsing {BASE_URL}...")
    
    # 1. Get list of potential products from the root
    product_candidates = get_directories(BASE_URL)
    
    results = []

    for product_dir in product_candidates:
        product_name = product_dir.rstrip('/')
        product_url = BASE_URL + product_dir
        
        # 2. Check which types exist for this product
        # Optimization: Fetch product page once and check for type directories
        available_types = get_directories(product_url)
        
        latest_serial_tuple = (-1, -1)
        best_serial_str = None
        best_type = None

        found_any_type = False

        for type_dir in available_types:
            type_name = type_dir.rstrip('/')
            
            if type_name in TYPES:
                found_any_type = True
                type_url = product_url + type_dir
                
                # 3. Get list of serials for this type
                serial_dirs = get_directories(type_url)
                
                for serial_dir in serial_dirs:
                    # Check if it looks like a date/serial
                    comp_val = parse_serial(serial_dir)
                    if comp_val:
                        # Compare to find the absolute latest for this product
                        if comp_val > latest_serial_tuple:
                            latest_serial_tuple = comp_val
                            best_serial_str = serial_dir.rstrip('/')
                            best_type = type_name
        
        if best_serial_str:
            results.append({
                'product': product_name,
                'type': best_type,
                'serial': best_serial_str
            })

    # Sort results by product name for clean output
    results.sort(key=lambda x: x['product'])

    # Print Report
    print(f"{'PRODUCT':<30} | {'TYPE':<20} | {'LATEST SERIAL'}")
    print("-" * 70)
    for res in results:
        print(f"{res['product']:<30} | {res['type']:<20} | {res['serial']}")

if __name__ == "__main__":
    main()
