# Design: Multi-country datasets, country dropdown, favorites export/import

**Date:** 2026-05-22

## Overview

Three features plus a reorganization:
1. Reorganize data files under a `data/` root
2. Replace the US/Scotland toggle with a country dropdown
3. Add France, England & Wales, and New Zealand as new datasets
4. Add export and import for the favorites list

---

## 1. Data folder reorganization

Move all dataset files under a unified `data/` directory:

```
data/
  us/
    yob1880.txt … yob2024.txt    (moved from ssa-data/)
  scotland/
    names.csv                     (moved from scottish-names-1974-2024/full-list-1974-2024.csv)
  france/
    names.csv                     (new)
  england-wales/
    names.csv                     (new)
  new-zealand/
    names.csv                     (new)
```

All country data files use a shared normalized CSV format:

```
Year,Sex,Name,Count
1974,Boy,Aaron,17
1974,Girl,Abigail,43
```

Scotland's existing file already uses this format (with a `Rank` column that can be ignored). The Scotland file is renamed to `names.csv` but otherwise unchanged.

Update path references in:
- `index.html` (US fetch paths `ssa-data/yob*.txt` → `data/us/yob*.txt`; Scottish fetch path)
- `fetch_all_namedata.py` (reads `ssa-data/yob*.txt`)
- `fetch_namedata.py` (reads `ssa-data/yob*.txt` if applicable)

---

## 2. Country dropdown

Replace the custom toggle (`.dataset-toggle`, `.dataset-switch`) with a `<select>` element in the header, placed between the `<h1>` and the year range control.

### HTML

```html
<select id="datasetSelect">
  <option value="us">🇺🇸 United States</option>
  <option value="england-wales">🏴󠁧󠁢󠁥󠁮󠁧󠁿 England &amp; Wales</option>
  <option value="france">🇫🇷 France</option>
  <option value="new-zealand">🇳🇿 New Zealand</option>
  <option value="scotland">🏴󠁧󠁢󠁳󠁣󠁴󠁿 Scotland</option>
</select>
```

Ordering: US first, then the rest alphabetical.

### CSS

Reuse existing `.letter-group select` styles (same border, border-radius, padding, font-size, background). Remove all `.dataset-toggle`, `.dataset-switch`, `.dataset-switch-thumb`, `.dataset-toggle-label` CSS.

### JavaScript

- `DATASETS` config gains a `label` field per entry (data path is implicit: `data/{key}/names.csv`).
- Remove `updateDatasetUI()` toggle logic; replace with `document.getElementById('datasetSelect').value = activeDataset`.
- Wire `change` event on `#datasetSelect` to call `switchDataset(this.value)`.
- Remove click listeners on `#datasetSwitch`, `#labelUS`, `#labelScottish`.
- Settings persistence: `dataset` key in `SETTINGS_KEY` already saved; restore by setting `datasetSelect.value`.

### Updated DATASETS config

```js
const DATASETS = {
  us: {
    label: 'United States',
    minYear: 1880, maxYear: 2024, defaultStart: 2015, defaultEnd: 2024,
    footer: '<a href="https://www.ssa.gov/oact/babynames/" …>Social Security Administration</a>',
  },
  'england-wales': {
    label: 'England & Wales',
    minYear: 1996, maxYear: 2023, defaultStart: 2015, defaultEnd: 2023,
    footer: '<a href="https://www.ons.gov.uk/…" …>Office for National Statistics</a>',
  },
  france: {
    label: 'France',
    minYear: 1900, maxYear: 2023, defaultStart: 2015, defaultEnd: 2023,
    footer: '<a href="https://www.insee.fr/…" …>INSEE</a>',
  },
  'new-zealand': {
    label: 'New Zealand',
    minYear: 1900, maxYear: 2023, defaultStart: 2015, defaultEnd: 2023,
    footer: '<a href="https://www.stats.govt.nz/…" …>Stats NZ</a>',
  },
  scotland: {
    label: 'Scotland',
    minYear: 1974, maxYear: 2024, defaultStart: 2015, defaultEnd: 2024,
    footer: '<a href="https://www.nrscotland.gov.uk/…" …>National Records of Scotland</a>',
  },
};
```

Exact `maxYear` values for new datasets will be confirmed when data is downloaded.

---

## 3. New country datasets

### Shared normalized format

All non-US country files are stored as `data/{key}/names.csv` with columns:

```
Year,Sex,Name,Count
```

Where `Sex` is `Boy` or `Girl` (matching Scotland's existing format so the same JS loader works for all of them).

### France (INSEE Fichier des prénoms)

- **Source:** data.gouv.fr — "Fichier des prénoms depuis 1900"
- **Raw format:** `PREUSUEL,SEXE,ANNAIS,NOMBRE` (SEXE: 1=male, 2=female; rare names aggregated as `_PRENOMS_RARES_`; rare-year rows marked `XXXX`)
- **Processing script:** `process_france.py`
  - Downloads the national CSV
  - Filters out rows where `PREUSUEL == '_PRENOMS_RARES_'` or `ANNAIS == 'XXXX'`
  - Maps `SEXE` 1→`Boy`, 2→`Girl`
  - Title-cases names (INSEE stores them in ALL CAPS)
  - Writes `data/france/names.csv`

### England & Wales (ONS)

- **Source:** ONS — "Baby names in England and Wales"
- **Raw format:** Separate CSV files for boys and girls, one per year (1996–present), columns include name and count
- **Processing script:** `process_england_wales.py`
  - Downloads yearly boy and girl CSVs from ONS
  - Combines into a single `data/england-wales/names.csv` with `Year,Sex,Name,Count`

### New Zealand (Stats NZ)

- **Source:** data.govt.nz — "Baby name popularity over time"
- **Raw format:** Single CSV with columns for name, sex (male/female), year, and count
- **Processing script:** `process_new_zealand.py`
  - Downloads the CSV
  - Normalizes sex values to `Boy`/`Girl`
  - Writes `data/new-zealand/names.csv`

### JS loader

All non-US datasets share a single generic loader (`loadCountryData(key)`) that:
1. Fetches `data/{key}/names.csv`
2. Parses `Year,Sex,Name,Count` rows
3. Builds the same `Map<year, [{name, gender, count}]>` structure already used by `loadScottishData()`
4. Caches result in a `Map<datasetKey, parsedData>`

`loadScottishData()` is replaced by this generic loader. `loadRange()` dispatches to either the US per-year fetch or the generic loader.

---

## 4. Favorites export / import

### Export

- Button labeled `↑ Export` in the `.fav-info` bar, to the left of the favorites toggle.
- Visible only when `favoriteNames.size > 0`.
- On click: creates a JSON blob `["Emma", "Liam", …]` (plain array of strings) and triggers a download as `baby-namer-favorites.json`.

### Import

- Button labeled `↓ Import` in the `.fav-info` bar, between Export and the toggle.
- Always visible (so you can import into an empty list).
- On click: programmatically clicks a hidden `<input type="file" accept=".json">`.
- On file selection: reads the file, parses JSON, validates it's an array of strings, **merges** each name into `favoriteNames` (does not replace — safe for sharing with a partner).
- After merge: saves to `localStorage`, updates count, re-renders table.
- On parse error: shows a brief inline error message (e.g., `"Invalid favorites file"` replacing the count for 3 seconds).

### Layout (results bar)

```
1,247 names          8 favorites marked  [↑ Export]  [↓ Import]  |  [toggle] Favorites only
```

Export is hidden when 0 favorites. Import is always shown.

---

## Out of scope

- Geo-detection for default country (localStorage already persists the last-used dataset)
- Per-country name definition lookups (behindthename.com works regardless of dataset)
- Downloading new country data as part of the app bundle (data files are committed to the repo after running the processing scripts locally)
