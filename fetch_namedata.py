#!/usr/bin/env python3
"""
Fetch Behind the Name API data for the top N Jewish names by SSA popularity.
Saves results to namedata.json.
Rate: 1.7 req/s (one request every ~588ms).
"""

import json
import time
import urllib.request
import urllib.parse
import os
from collections import defaultdict

API_KEY  = "wi835199366"
DELAY    = 1.0 / 1.7          # ~0.588s between requests
TOP_N    = 100
OUT_FILE = "namedata.json"

# ── 1. Aggregate SSA counts ───────────────────────────────────────────────────
counts = defaultdict(lambda: {"m": 0, "f": 0})
for year in range(2015, 2025):
    path = f"ssa-data/yob{year}.txt"
    if not os.path.exists(path):
        print(f"  warn: {path} not found, skipping")
        continue
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            name, gender, n = line.split(",")
            if gender == "M":
                counts[name]["m"] += int(n)
            else:
                counts[name]["f"] += int(n)

print(f"Loaded SSA data: {len(counts):,} unique names")

# ── 2. Load Jewish names ──────────────────────────────────────────────────────
with open("tags.json") as fh:
    tags = json.load(fh)

jewish_names = tags["jewish"]

def total(name):
    return counts[name]["m"] + counts[name]["f"]

ranked = sorted(jewish_names, key=lambda n: -total(n))
top = ranked[:TOP_N]

print(f"\nTop {TOP_N} Jewish names (by SSA total births 2015–2024):")
for i, name in enumerate(top, 1):
    t = total(name)
    print(f"  {i:3d}. {name:<20} {t:>8,}")

# ── 3. Fetch API ──────────────────────────────────────────────────────────────
# Load existing results so we can resume if interrupted
if os.path.exists(OUT_FILE):
    with open(OUT_FILE) as fh:
        results = json.load(fh)
    print(f"\nResuming — {len(results)} already fetched")
else:
    results = {}

todo = [n for n in top if n not in results]
print(f"Fetching {len(todo)} names at 1.7 req/s …\n")

for i, name in enumerate(todo):
    encoded = urllib.parse.quote(name.lower())
    url = f"https://www.behindthename.com/api/lookup.json?name={encoded}&key={API_KEY}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            raw = json.loads(resp.read().decode())
            # API returns a list of matching name objects
            data = raw[0] if isinstance(raw, list) and raw else raw
            results[name] = data
            usages = ", ".join(u["usage_full"] for u in data.get("usages", []))
            print(f"  [{i+1}/{len(todo)}] {name:<20} gender={data.get('gender','?')}  {usages}")
    except Exception as e:
        print(f"  [{i+1}/{len(todo)}] {name:<20} ERROR: {e}")
        results[name] = {"error": str(e)}

    # Save after every fetch so we can resume
    with open(OUT_FILE, "w") as fh:
        json.dump(results, fh, indent=2)

    if i < len(todo) - 1:
        time.sleep(DELAY)

print(f"\nDone. {len(results)} entries saved to {OUT_FILE}")
