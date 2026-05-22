#!/usr/bin/env python3
"""Download kkoopmans/anglosphere-baby-names and fan out per-country CSVs.

Source: https://github.com/kkoopmans/anglosphere-baby-names
License: GPL-3.0 (underlying data is open government statistics)

Pass a local all-names-long.csv as argv[1] to skip the download.
"""
import csv
import io
import os
import sys
import urllib.request

URL = "https://raw.githubusercontent.com/kkoopmans/anglosphere-baby-names/main/all-names-long.csv"

# Maps country value in CSV → output directory key
COUNTRIES = {
    "Australia":          "australia",
    "Canada":             "canada",
    "England and Wales":  "england-wales",
    "Ireland":            "ireland",
    "Northern Ireland":   "northern-ireland",
    "New Zealand":        "new-zealand",
}

if len(sys.argv) > 1:
    print(f"Reading local file: {sys.argv[1]}")
    with open(sys.argv[1], encoding='utf-8-sig') as f:
        content = f.read()
else:
    print(f"Downloading {URL} ...")
    try:
        req = urllib.request.Request(URL, headers={'User-Agent': 'baby-namer/1.0'})
        with urllib.request.urlopen(req, timeout=120) as resp:
            content = resp.read().decode('utf-8-sig')
        print(f"Downloaded {len(content):,} chars")
    except Exception as e:
        print(f"\nDownload failed: {e}")
        print(f"\nManual steps:")
        print(f"  1. Download https://raw.githubusercontent.com/kkoopmans/anglosphere-baby-names/main/all-names-long.csv")
        print(f"  2. Run: python3 process_anglosphere.py path/to/all-names-long.csv")
        sys.exit(1)

# Parse into per-country buckets
buckets = {key: [] for key in COUNTRIES.values()}

reader = csv.DictReader(io.StringIO(content))
print(f"Columns: {reader.fieldnames}")

for row in reader:
    country = row.get('country', '').strip()
    if country not in COUNTRIES:
        continue
    key = COUNTRIES[country]

    try:
        year  = int(row['year'])
        count = int(row['frequency'])
    except (ValueError, KeyError):
        continue

    sex_raw = row.get('sex', '').strip().upper()
    if sex_raw == 'M':
        sex = 'Boy'
    elif sex_raw == 'F':
        sex = 'Girl'
    else:
        print(f"WARNING: unexpected sex value {sex_raw!r}, skipping row")
        continue

    name = row.get('name', '').strip().title()
    if not name:
        continue

    buckets[key].append((year, sex, name, count))

# Write one CSV per country
for country_name, key in COUNTRIES.items():
    rows = sorted(buckets[key], key=lambda r: (r[0], r[1], r[2]))
    if not rows:
        print(f"WARNING: no rows for {country_name}")
        continue

    out_dir = f"data/{key}"
    os.makedirs(out_dir, exist_ok=True)
    out_path = f"{out_dir}/names.csv"

    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Year', 'Sex', 'Name', 'Count'])
        w.writerows(rows)

    years = sorted({r[0] for r in rows})
    print(f"{country_name}: {len(rows):,} rows, {min(years)}–{max(years)}, {len({r[2] for r in rows}):,} unique names → {out_path}")
