#!/usr/bin/env python3
"""
Scrape Behind the Name cultural category pages and output name lists
for adding to tags.json.

Usage:
    python3 fetch_cultural_tags.py              # list all categories + URL slugs
    python3 fetch_cultural_tags.py arabic       # scrape and print names for one category
    python3 fetch_cultural_tags.py --all        # scrape all categories, write cultural_tags.json

Rate: 1 request/2 seconds (polite crawl, no API key needed).
"""

import sys
import time
import json
import re
import urllib.request

DELAY = 2.0
BASE  = "https://www.behindthename.com"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8", errors="replace")


def get_categories():
    """Return list of (label, slug) from the glossary page."""
    html = fetch(f"{BASE}/glossary/view/name")
    matches = re.findall(r'href="/names/usage/([^"]+)"[^>]*>([^<]+)<', html)
    seen = set()
    categories = []
    for slug, label in matches:
        label = label.strip()
        if slug not in seen and label:
            seen.add(slug)
            categories.append((label, slug))
    return categories


def scrape_category(slug):
    """Return sorted list of name strings for a BTN usage category."""
    names = set()
    page = 1
    while True:
        url = f"{BASE}/names/usage/{slug}/{page}"
        html = fetch(url)
        found = re.findall(r'<a class="nl"[^>]*>([^<]+)</a>', html)
        if not found:
            break
        names.update(n.strip() for n in found)
        if f'/names/usage/{slug}/{page + 1}' not in html:
            break
        page += 1
        time.sleep(DELAY)
    return sorted(names)


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        cats = get_categories()
        print(f"Found {len(cats)} cultural categories:\n")
        for label, slug in cats:
            print(f"  {slug:<30} {label}")

    elif args[0] == "--all":
        cats = get_categories()
        print(f"Scraping {len(cats)} categories...\n")
        result = {}
        for label, slug in cats:
            print(f"  Fetching {slug}...", end=" ", flush=True)
            names = scrape_category(slug)
            result[slug] = names
            print(f"{len(names)} names")
            time.sleep(DELAY)
        with open("cultural_tags.json", "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nWritten to cultural_tags.json")

    else:
        slug = args[0]
        print(f"Scraping category: {slug}")
        names = scrape_category(slug)
        print(f"Found {len(names)} names:")
        for n in names:
            print(f"  {n}")
