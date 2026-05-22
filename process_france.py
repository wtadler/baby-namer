#!/usr/bin/env python3
"""Download and normalize INSEE Fichier des prénoms to data/france/names.csv.

Source page: https://www.insee.fr/fr/statistiques/8595130
The page offers a "Fichier national" CSV zip (nat<year>_csv.zip).
Pass a local zip as argv[1] to skip the download.
"""
import csv
import io
import os
import sys
import urllib.request
import zipfile

OUT = "data/france/names.csv"
URL = "https://www.insee.fr/fr/statistiques/fichier/8595130/nat2024_csv.zip"

os.makedirs("data/france", exist_ok=True)

if len(sys.argv) > 1:
    print(f"Reading local file: {sys.argv[1]}")
    with open(sys.argv[1], 'rb') as f:
        raw = f.read()
else:
    print(f"Downloading {URL} ...")
    try:
        req = urllib.request.Request(URL, headers={'User-Agent': 'baby-namer/1.0'})
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
        print(f"Downloaded {len(raw):,} bytes")
    except Exception as e:
        print(f"\nDownload failed: {e}")
        print(f"\nManual steps:")
        print(f"  1. Go to https://www.insee.fr/fr/statistiques/8595130")
        print(f"  2. Download the 'Fichier national' CSV zip")
        print(f"  3. Run: python3 process_france.py path/to/downloaded.zip")
        sys.exit(1)

with zipfile.ZipFile(io.BytesIO(raw)) as zf:
    # Prefer the national file (contains 'nat', not 'dpt')
    csv_files = [n for n in zf.namelist() if n.endswith('.csv') and 'nat' in n.lower() and 'dpt' not in n.lower()]
    if not csv_files:
        csv_files = [n for n in zf.namelist() if n.endswith('.csv')]
    csv_name = csv_files[0]
    print(f"Processing {csv_name} ...")
    content = zf.read(csv_name).decode('utf-8', errors='replace')

rows = []
reader = csv.DictReader(io.StringIO(content), delimiter=';')
for row in reader:
    # Column names vary by edition: try both cases
    name    = (row.get('PREUSUEL') or row.get('preusuel') or '').strip()
    sexe    = (row.get('SEXE')     or row.get('sexe')     or '').strip()
    annais  = (row.get('ANNAIS')   or row.get('annais')   or '').strip()
    nombre  = (row.get('NOMBRE')   or row.get('nombre')   or '').strip()

    if name.startswith('_PRENOMS_RARES') or annais == 'XXXX':
        continue
    try:
        year  = int(annais)
        count = int(nombre)
    except ValueError:
        continue

    sex = 'Boy' if sexe == '1' else 'Girl'
    rows.append((year, sex, name.title(), count))

rows.sort(key=lambda r: (r[0], r[1], r[2]))

with open(OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['Year', 'Sex', 'Name', 'Count'])
    w.writerows(rows)

years = sorted({r[0] for r in rows})
print(f"Written {len(rows):,} rows to {OUT}")
print(f"Year range: {min(years)}–{max(years)}, unique names: {len({r[2] for r in rows}):,}")
