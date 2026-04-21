#!/usr/bin/env python3
"""
Long-running enrichment script: fetches Behind the Name API data for all SSA names.
Priority order: all tags.json names first (by SSA popularity), then remaining SSA names.
Rate: 4,000 requests/day = 1 request every 21.6 seconds.

Run in background:  python3 fetch_all_namedata.py &
Interrupt safely:   Ctrl-C  (progress is saved after every request)
"""

import json
import time
import urllib.request
import urllib.parse
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta

API_KEY  = "wi835199366"
DELAY    = 86400 / 4000        # 21.6 seconds — respects 4,000/day limit
OUT_FILE = "namedata.json"

# ── 1. Aggregate SSA counts ───────────────────────────────────────────────────
counts = defaultdict(lambda: {"m": 0, "f": 0})
for year in range(2015, 2025):
    path = f"ssa-data/yob{year}.txt"
    if not os.path.exists(path):
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

all_ssa = set(counts.keys())
print(f"SSA names loaded: {len(all_ssa):,}")

def total(name):
    return counts[name]["m"] + counts[name]["f"]

# ── 2. Load tags for priority ordering ───────────────────────────────────────
with open("tags.json") as fh:
    tags = json.load(fh)

tagged_names = set(n for lst in tags.values() for n in lst)

# ── 3. Load existing results ──────────────────────────────────────────────────
if os.path.exists(OUT_FILE):
    with open(OUT_FILE) as fh:
        results = json.load(fh)
    print(f"Existing results loaded: {len(results):,}")
else:
    results = {}

already = set(results.keys())

# ── 4. Build priority queue ───────────────────────────────────────────────────
# Tier 1: all tagged names (any tags.json key), by SSA popularity
tier1 = sorted(tagged_names - already, key=lambda n: -total(n))
# Tier 2: all remaining SSA names by popularity
tier2 = sorted((all_ssa - tagged_names) - already, key=lambda n: -total(n))

todo = tier1 + tier2
total_todo = len(todo)

days = total_todo * DELAY / 86400
eta = datetime.now() + timedelta(seconds=total_todo * DELAY)
print(f"\nQueue: {len(tier1)} tagged  +  {len(tier2)} others  =  {total_todo} total")
print(f"At 4000/day this will take ~{days:.1f} days  (ETA {eta.strftime('%a %b %d %H:%M')} if uninterrupted)\n")

# ── 5. Fetch loop ─────────────────────────────────────────────────────────────
def save():
    with open(OUT_FILE, "w") as fh:
        json.dump(results, fh, indent=2)

for i, name in enumerate(todo):
    encoded = urllib.parse.quote(name.lower())
    url = f"https://www.behindthename.com/api/lookup.json?name={encoded}&key={API_KEY}"

    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            raw = json.loads(resp.read().decode())
            data = raw[0] if isinstance(raw, list) and raw else raw
            results[name] = data
            usages = " · ".join(u["usage_full"] for u in data.get("usages", []))
            tier = "T" if name in tagged_names else " "
            print(f"[{tier}] {i+1:>5}/{total_todo}  {name:<22} {data.get('gender','?')}  {usages}")
    except KeyboardInterrupt:
        print("\nInterrupted — saving progress…")
        save()
        sys.exit(0)
    except Exception as e:
        print(f"[ ] {i+1:>5}/{total_todo}  {name:<22} ERROR: {e}")
        results[name] = {"error": str(e)}

    save()

    if i < len(todo) - 1:
        time.sleep(DELAY)

print(f"\nAll done. {len(results):,} entries in {OUT_FILE}")
