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
# See git history to read the problems this script had.
# The most pressing issues have been fixed and the script can be used to populate the YAML.
# This script doesn't do anything else than printing information, so it's fairly safe to use.
#
# The tree is now /<product>/<series>/<type>/<serial>: cdimage ADT-1907
# (bdf842cb, "nest devel-series daily images under <series>/ for every
# project") moved the development series into a per-series subdirectory too,
# so every product looks like the already-released ones. Pass the series to
# scan as the first argument, e.g. `./fetch-serials.py resolute`.

import argparse
import re
import sys

import requests
from bs4 import BeautifulSoup

# Configuration
BASE_URL = "https://cdimage.ubuntu.com"
ALLOWED_TYPES = {"daily", "daily-live", "daily-preinstalled", "daily-minimal"}
# Directories at the root that are not products (or that have their own
# channel-based layout, like ubuntu-core) and so have no <series>/<type>/ tree.
SKIP_PRODUCTS = {"include", "netboot", "releases", "streams", "experimental"}


def get_links(url):
    """
    Fetches the HTML content of a directory listing and returns a list of
    subdirectory names (ending with '/').
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        links = []
        for link in soup.find_all("a"):
            href = link.get("href")
            # Apache directory listings provide relative links.
            # We look for directories (ending in /) and ignore parent links.
            if (
                href
                and href.endswith("/")
                and not href.startswith("?")
                and href not in ["/", "../"]
            ):
                links.append(href.rstrip("/"))
        return links
    except requests.exceptions.RequestException:
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
    match = re.match(r"^(\d{8})(?:\.(\d+))?$", serial_str)
    if match:
        date_part = int(match.group(1))
        # If no suffix version is present, assume 0
        version_part = int(match.group(2)) if match.group(2) else 0
        return (date_part, version_part)
    return None


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "series",
        help="series to scan, e.g. 'resolute' or 'stonking'",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    series = args.series

    print(f"Browsing {BASE_URL} for latest {series} serials...\n")
    print(f"{'Product':<25} | {'Type':<20} | {'Latest Serial':<12} | {'URL'}")
    print("-" * 100)

    found = False

    # Step 1: Browse root to find all products
    products = get_links(BASE_URL + "/")

    for product in products:
        # Skip common non-product directories to save time/errors
        if product in SKIP_PRODUCTS:
            continue

        # Step 2: Every product now keeps its dailies under <series>/, so a
        # product that never built this series simply has no such directory.
        if series not in get_links(f"{BASE_URL}/{product}/"):
            continue

        series_url = f"{BASE_URL}/{product}/{series}/"

        # Step 3: Browse the series directory to find types
        for type_name in get_links(series_url):
            if type_name not in ALLOWED_TYPES:
                continue

            type_url = f"{series_url}{type_name}/"

            # Step 4: Browse the type directory to find serials
            build_dirs = get_links(type_url)

            valid_serials = []
            for build_dir in build_dirs:
                # 'current' and 'pending' are often symlinks, but we want the actual serial date
                serial = parse_serial(build_dir)
                if serial:
                    valid_serials.append(
                        {
                            "original": build_dir,
                            "serial": serial,
                            "url": f"{type_url}{build_dir}",
                        }
                    )

            if valid_serials:
                # Sort by the serial tuple (Date, Version) in descending order
                valid_serials.sort(key=lambda x: x["serial"], reverse=True)
                latest_build = valid_serials[0]
                found = True

                print(
                    f"{product:<25} | {type_name:<20} | {latest_build['original']:<13} | {latest_build['url']}"
                )
    print("-" * 100)
    if not found:
        print(
            f"No dailies found for series '{series}'. Check the name against "
            f"the per-product listings on {BASE_URL}/."
        )
        sys.exit(1)
    print(
        "Please go check each link and verify all images while populating the milestone YAML file with the candidate serials"
    )
    print(
        "NOTE: this prints the *newest* build per product/type, which is not "
        "necessarily the *validated* one. Take the serials from the ISO "
        "tracker and use this only to cross-check that they exist."
    )


if __name__ == "__main__":
    main()
