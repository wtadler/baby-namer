#!/usr/bin/env python3
"""Download and normalize NZ baby name data to data/new-zealand/names.csv.

Primary source: kkoopmans/anglosphere-baby-names on GitHub (MIT license),
which aggregates Stats NZ data (catalogue.data.govt.nz/dataset/baby-name-popularity-over-time)
into a tidy CSV covering 1935-2023.

Pass a local CSV as argv[1] to skip the download.
"""
import csv
import io
import os
import sys
import urllib.request

OUT = "data/new-zealand/names.csv"
# Aggregated anglosphere dataset containing New Zealand records (1935-2023)
URL = "https://raw.githubusercontent.com/kkoopmans/anglosphere-baby-names/main/all-names-long.csv"

os.makedirs("data/new-zealand", exist_ok=True)

if len(sys.argv) > 1:
    print(f"Reading local file: {sys.argv[1]}")
    with open(sys.argv[1], encoding='utf-8-sig') as f:
        content = f.read()
else:
    print(f"Downloading from GitHub (kkoopmans/anglosphere-baby-names)...")
    try:
        req = urllib.request.Request(URL, headers={'User-Agent': 'baby-namer/1.0'})
        with urllib.request.urlopen(req, timeout=120) as resp:
            content = resp.read().decode('utf-8')
        print(f"Downloaded {len(content):,} chars")
    except Exception as e:
        print(f"\nDownload failed: {e}")
        print(f"\nManual steps:")
        print(f"  1. Go to https://github.com/kkoopmans/anglosphere-baby-names")
        print(f"  2. Download all-names-long.csv")
        print(f"  3. Run: python3 process_new_zealand.py path/to/all-names-long.csv")
        sys.exit(1)

reader = csv.DictReader(io.StringIO(content))
headers = reader.fieldnames or []
print(f"Columns: {headers}")

# Expect: year, sex, country, name, frequency, proportion
rows = []
sex_map = {'F': 'Girl', 'M': 'Boy'}

for row in reader:
    if row.get('country') != 'New Zealand':
        continue
    name = row['name'].strip().title()
    sex_raw = row['sex'].strip()
    try:
        year = int(row['year'].strip())
        count = int(row['frequency'].strip())
    except ValueError:
        continue
    sex = sex_map.get(sex_raw, sex_raw)
    rows.append((year, sex, name, count))

if not rows:
    print("ERROR: no New Zealand rows found. Check that the file contains a 'country' column with 'New Zealand' values.")
    sys.exit(1)

rows.sort(key=lambda r: (r[0], r[1], r[2]))

with open(OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['Year', 'Sex', 'Name', 'Count'])
    w.writerows(rows)

years = sorted({r[0] for r in rows})
print(f"Written {len(rows):,} rows to {OUT}")
print(f"Year range: {min(years)}-{max(years)}, unique names: {len({r[2] for r in rows}):,}")
print(f"Sex mapping: {sex_map}")
