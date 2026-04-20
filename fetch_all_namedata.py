#!/usr/bin/env python3
"""
Long-running enrichment script: fetches Behind the Name API data for all SSA names.
Priority order: jewish → water → everything else (by SSA popularity).
Rate: 360 requests/hour = 1 request every 10 seconds.

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
DELAY    = 3600 / 360          # 10.0 seconds per request
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

jewish_names = set(tags.get("jewish", []))
water_names  = set(tags.get("water",  []))

# ── 3. Load existing results ──────────────────────────────────────────────────
if os.path.exists(OUT_FILE):
    with open(OUT_FILE) as fh:
        results = json.load(fh)
    print(f"Existing results loaded: {len(results):,}")
else:
    results = {}

already = set(results.keys())

# ── 4. Build priority queue ───────────────────────────────────────────────────
# Tier 1: jewish names (by SSA popularity, include ones not in SSA data too)
tier1 = sorted(jewish_names - already, key=lambda n: -total(n))
# Tier 2: water names not already covered
tier2 = sorted((water_names - jewish_names) - already, key=lambda n: -total(n))
# Tier 3: all remaining SSA names
tier3 = sorted((all_ssa - jewish_names - water_names) - already, key=lambda n: -total(n))

todo = tier1 + tier2 + tier3
total_todo = len(todo)

print(f"\nQueue: {len(tier1)} jewish  +  {len(tier2)} water  +  {len(tier3)} others  =  {total_todo} total")
eta = datetime.now() + timedelta(seconds=total_todo * DELAY)
print(f"At 360/hr this will take ~{total_todo/360:.1f} hrs  (ETA {eta.strftime('%a %H:%M')} if uninterrupted)\n")

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
            tier = "J" if name in jewish_names else ("W" if name in water_names else " ")
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
