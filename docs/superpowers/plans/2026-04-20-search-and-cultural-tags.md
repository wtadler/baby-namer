# Search Improvements & Cultural Name Tags — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add boolean search to the Usage field, surface "Jewish" as a searchable usage tag (removing the checkbox), add thematic easter-egg name sets (`~water`, `~fire`, etc.), fix the API rate limit, and write a cultural-category scraper.

**Architecture:** All JS lives inline in `index.html`; a new `buildUsageMatcher()` function replaces the current substring check. Cultural/thematic tag sets live in `tags.json` and are injected as synthetic usages at load time. Python scripts handle data enrichment separately.

**Tech Stack:** Vanilla JS (no dependencies), Python 3 (stdlib only), Behind the Name REST API.

**Implementation order (non-scraping first):**
1. Boolean usage search (JS only)
2. Jewish → usage field injection + remove checkbox (JS only)
3. Thematic easter eggs (tags.json + JS)
4. API rate-limit fix (one-line Python change)
5. Cultural category scraper (new Python script)

---

## File Map

| File | Change |
|------|--------|
| `index.html` | Add `buildUsageMatcher()`, update `getFiltered()`, inject Jewish usages at init, remove `jewish` from `tagLabels`, update placeholder |
| `tags.json` | Add `fire`, `celestial`, `music` arrays |
| `fetch_all_namedata.py` | Update `DELAY` to 4000/day; simplify priority to all-tags-first |
| `fetch_cultural_tags.py` | New script — scrape glossary + category pages |

---

## Task 1: Boolean Usage Search

**Files:**
- Modify: `index.html` — add `buildUsageMatcher()` before `getFiltered()` (~line 748); update `getFiltered()` usage block (~lines 762–777)

No test framework exists in this project. Verification is done via browser console and the preview dev server.

- [ ] **Step 1: Add `buildUsageMatcher` function**

Insert this function immediately before `function getFiltered()` in `index.html`:

```javascript
function buildUsageMatcher(raw) {
  const q = raw.trim();
  if (!q) return null;

  const tokens = [];
  const re = /\(|\)|\bAND\b|\bOR\b|\bNOT\b|[^\s()]+/gi;
  let m;
  while ((m = re.exec(q)) !== null) {
    const t = m[0];
    tokens.push(['AND','OR','NOT','(', ')'].includes(t.toUpperCase()) ? t.toUpperCase() : t.toLowerCase());
  }

  let pos = 0;

  function parseExpr() {
    let node = parseTerm();
    while (pos < tokens.length && (tokens[pos] === 'AND' || tokens[pos] === 'OR')) {
      const op = tokens[pos++];
      const right = parseTerm();
      const l = node, r = right;
      node = op === 'AND'
        ? (usages) => l(usages) && r(usages)
        : (usages) => l(usages) || r(usages);
    }
    return node;
  }

  function parseTerm() {
    if (tokens[pos] === 'NOT') {
      pos++;
      const inner = parseAtom();
      return (usages) => !inner(usages);
    }
    return parseAtom();
  }

  function parseAtom() {
    if (tokens[pos] === '(') {
      pos++;
      const inner = parseExpr();
      if (tokens[pos] === ')') pos++;
      return inner;
    }
    if (pos < tokens.length && !['AND','OR','NOT',')'].includes(tokens[pos])) {
      const word = tokens[pos++];
      return (usages) => usages.some(u =>
        u.usage_full.toLowerCase().includes(word) ||
        u.usage_code.toLowerCase().includes(word)
      );
    }
    return () => true;
  }

  try {
    return parseExpr();
  } catch (e) {
    // fallback: original substring match
    const lower = q.toLowerCase();
    return (usages) => usages.some(u =>
      u.usage_full.toLowerCase().includes(lower) ||
      u.usage_code.toLowerCase().includes(lower)
    );
  }
}
```

- [ ] **Step 2: Update `getFiltered()` to use the new matcher**

Replace lines 762–777 in `getFiltered()`:

**Before:**
```javascript
  const checkedTags = [...document.querySelectorAll('.tag-checkbox:checked')].map(el => el.value);
  const usageQuery  = document.getElementById('usageBox').value.trim().toLowerCase();

  return allNames.filter(n => {
    if (n.pctM < minPct || n.pctM > maxPct) return false;
    if (first && n.name[0].toUpperCase() !== first) return false;
    if (last  && n.name[n.name.length - 1].toUpperCase() !== last) return false;
    if (re && !re.test(n.name)) return false;
    if (checkedTags.length && !checkedTags.every(tag => tagSets[tag]?.has(n.name))) return false;
    if (usageQuery) {
      const usages = nameData[n.name]?.usages ?? [];
      if (!usages.some(u =>
        u.usage_full.toLowerCase().includes(usageQuery) ||
        u.usage_code.toLowerCase().includes(usageQuery)
      )) return false;
    }
    return true;
  });
```

**After:**
```javascript
  const checkedTags = [...document.querySelectorAll('.tag-checkbox:checked')].map(el => el.value);
  const usageRaw    = document.getElementById('usageBox').value.trim();

  const themeMatch = usageRaw.match(/^~(\w+)$/);
  const themeSet   = themeMatch ? (tagSets[themeMatch[1].toLowerCase()] ?? new Set()) : null;
  const usageMatcher = themeSet ? null : buildUsageMatcher(usageRaw);

  return allNames.filter(n => {
    if (n.pctM < minPct || n.pctM > maxPct) return false;
    if (first && n.name[0].toUpperCase() !== first) return false;
    if (last  && n.name[n.name.length - 1].toUpperCase() !== last) return false;
    if (re && !re.test(n.name)) return false;
    if (checkedTags.length && !checkedTags.every(tag => tagSets[tag]?.has(n.name))) return false;
    if (themeSet)    return themeSet.has(n.name);
    if (usageMatcher) {
      const usages = nameData[n.name]?.usages ?? [];
      if (!usageMatcher(usages)) return false;
    }
    return true;
  });
```

- [ ] **Step 3: Update the usageBox placeholder**

Find `<input type="text" id="usageBox" placeholder="e.g. Hebrew, Biblical…"` and change the placeholder:

```html
<input type="text" id="usageBox" placeholder="e.g. Hebrew AND Biblical" spellcheck="false">
```

- [ ] **Step 4: Verify in browser**

Start the dev server (`npx wrangler dev` or open `index.html` directly). Open browser console and test:

```javascript
// Should return a function
buildUsageMatcher('Hebrew AND Biblical')

// Test with sample usages
const heb = [{usage_full:'Hebrew',usage_code:'heb'},{usage_full:'Biblical',usage_code:'eng-bibl'}];
const eng = [{usage_full:'English',usage_code:'eng'}];

console.assert(buildUsageMatcher('Hebrew AND Biblical')(heb) === true,  'heb+bibl should match');
console.assert(buildUsageMatcher('Hebrew AND Biblical')(eng) === false, 'eng-only should not match');
console.assert(buildUsageMatcher('Hebrew OR English')(eng)  === true,  'OR should match eng');
console.assert(buildUsageMatcher('NOT English')(heb)        === true,  'NOT should pass non-eng');
console.assert(buildUsageMatcher('NOT English')(eng)        === false, 'NOT should block eng');
console.assert(buildUsageMatcher('Hebrew AND (English OR French)')(heb) === false, 'needs eng/fre');
```

Also type `Hebrew AND Biblical` into the Usage field and confirm names filter correctly. Type `Hebrew OR Arabic` and confirm both cultures appear.

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "feat: boolean AND/OR/NOT search in Usage field"
```

---

## Task 2: Jewish → Usage Field Injection

**Files:**
- Modify: `index.html` — inject synthetic Jewish usage at init (~line 1179); remove `jewish` from `tagLabels` (~line 1176)

- [ ] **Step 1: Inject Jewish usage at init**

After line 1179 (`tagSets[key] = new Set(nameList)`), add injection logic. Find this block:

```javascript
    const tagLabels = { jewish: 'Jewish', water: 'Water' };
    for (const [key, nameList] of Object.entries(tagsRaw)) {
      tagSets[key] = new Set(nameList);
    }
```

Replace with:

```javascript
    const tagLabels = {};
    for (const [key, nameList] of Object.entries(tagsRaw)) {
      tagSets[key] = new Set(nameList);
    }

    // Inject synthetic "Jewish" usage for every name in the jewish list
    for (const name of (tagSets.jewish ?? [])) {
      if (!nameData[name]) nameData[name] = { usages: [] };
      if (!nameData[name].usages) nameData[name].usages = [];
      if (!nameData[name].usages.some(u => u.usage_code === 'jewish')) {
        nameData[name].usages.push({ usage_code: 'jewish', usage_full: 'Jewish' });
      }
    }
```

Note: `tagLabels` is now empty `{}`, which means the loop at lines 1195–1202 will generate no checkboxes — the Tags section becomes empty. The `tagSets` map is still fully populated and used for `~theme` lookups.

- [ ] **Step 2: Verify in browser**

Open browser console after load:

```javascript
// Abraham is in the jewish list but has no API jewish usage_code
// After injection it should have one
nameData['Abraham'].usages.some(u => u.usage_code === 'jewish')  // → true

// Typing "Jewish" in the Usage box should show Abraham, Isaac, etc.
// The Tags checkboxes panel should be empty
```

Type `Jewish` in the Usage field — confirm you see names like Abraham, Isaac, Aaron, Miriam. Confirm no checkboxes appear in the Tags section.

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat: inject Jewish usage tag from curated list, remove checkbox"
```

---

## Task 3: Thematic Easter Eggs

**Files:**
- Modify: `tags.json` — add `fire`, `celestial`, `music` arrays
- `index.html` already handles `~theme` after Task 1 (no additional JS needed)

- [ ] **Step 1: Add thematic lists to tags.json**

Read the current `tags.json` and add three new keys. The complete updated file:

```json
{
  "jewish": [ ... existing 644 names unchanged ... ],
  "water": [ ... existing 61 names unchanged ... ],
  "fire": [
    "Aidan", "Aiden", "Agni", "Aine", "Alinta", "Azar",
    "Blaze", "Brand", "Bren", "Brigid", "Brigitte",
    "Cole", "Cyrus",
    "Edan", "Ember",
    "Fiamma",
    "Hestia",
    "Ignatius",
    "Keahi", "Kenneth",
    "Nuri",
    "Pele", "Phoenix", "Prometheus",
    "Seraph", "Seraphina", "Surya",
    "Tana",
    "Vesta", "Vulcan"
  ],
  "celestial": [
    "Altair", "Andromeda", "Aquila", "Ara", "Astra", "Aurora",
    "Carina", "Castor", "Celeste",
    "Draco",
    "Electra", "Elio", "Estrella",
    "Helios",
    "Luna", "Lyra",
    "Nova",
    "Orion",
    "Perseus", "Phoebe",
    "Rigel",
    "Selene", "Sirius", "Sol", "Soleil", "Stella",
    "Vega", "Vesper"
  ],
  "music": [
    "Allegra", "Anthem", "Aria",
    "Cadence", "Calliope", "Carol", "Celesta", "Chantelle", "Chorus",
    "Fife",
    "Harmony",
    "Lyra", "Lyric",
    "Melody",
    "Piper",
    "Serenade", "Sonata",
    "Viola"
  ]
}
```

Keep the existing `jewish` and `water` arrays exactly as they are — only append the three new keys.

- [ ] **Step 2: Verify in browser**

Type `~fire` in the Usage field — confirm you see names like Ember, Phoenix, Aidan. Type `~celestial` — confirm Aurora, Orion, Luna appear. Type `~water` — confirm the existing water list still works. Type `~bogus` — confirm zero results (not an error).

- [ ] **Step 3: Commit**

```bash
git add tags.json
git commit -m "feat: add fire/celestial/music thematic easter egg name sets"
```

---

## Task 4: API Rate-Limit Fix

**Files:**
- Modify: `fetch_all_namedata.py` — update `DELAY`; simplify priority queue to all-tags-first

- [ ] **Step 1: Update delay and priority logic**

The current rate is 360/hr (10s delay). The actual limit is 4,000/day = ~2.7/min = 21.6s between requests.

Also simplify the priority queue: instead of hardcoding `jewish` and `water` as separate tiers, tier 1 is *all names in any tags.json key*, tier 2 is remaining SSA names by frequency. This automatically handles any new cultural tag keys added later.

Find these lines near the top of the file:

```python
DELAY    = 3600 / 360          # 10.0 seconds per request
```

Change to:

```python
DELAY    = 86400 / 4000        # 21.6 seconds — respects 4,000/day limit
```

Then find the priority queue section (lines 64–72):

```python
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
```

Replace with:

```python
# Tier 1: all tagged names (any tags.json key), by SSA popularity
tagged_names = set()
for name_list in tags.values():
    tagged_names.update(name_list)

tier1 = sorted(tagged_names - already, key=lambda n: -total(n))
# Tier 2: all remaining SSA names by popularity
tier2 = sorted((all_ssa - tagged_names) - already, key=lambda n: -total(n))

todo = tier1 + tier2
total_todo = len(todo)

days = total_todo * DELAY / 86400
eta = datetime.now() + timedelta(seconds=total_todo * DELAY)
print(f"\nQueue: {len(tier1)} tagged  +  {len(tier2)} others  =  {total_todo} total")
print(f"At 4000/day this will take ~{days:.1f} days  (ETA {eta.strftime('%a %b %d %H:%M')} if uninterrupted)\n")
```

Also remove the now-unused `jewish_names` and `water_names` variables (lines 51–52):

```python
jewish_names = set(tags.get("jewish", []))
water_names  = set(tags.get("water",  []))
```

Delete those two lines. The tier print in the fetch loop (line 94) also references them:

```python
            tier = "J" if name in jewish_names else ("W" if name in water_names else " ")
```

Replace with:

```python
            tier = "T" if name in tagged_names else " "
```

- [ ] **Step 2: Verify**

Run a dry-run check (don't actually fetch — just verify the queue builds correctly):

```bash
python3 -c "
import json, os
from collections import defaultdict

counts = defaultdict(lambda: {'m': 0, 'f': 0})
for year in range(2015, 2025):
    path = f'ssa-data/yob{year}.txt'
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                name, gender, n = line.strip().split(',')
                counts[name]['m' if gender == 'M' else 'f'] += int(n)

with open('tags.json') as f: tags = json.load(f)
with open('namedata.json') as f: results = json.load(f)

tagged = set(n for lst in tags.values() for n in lst)
already = set(results.keys())
total_fn = lambda n: counts[n]['m'] + counts[n]['f']

tier1 = sorted(tagged - already, key=lambda n: -total_fn(n))
tier2 = sorted((set(counts.keys()) - tagged) - already, key=lambda n: -total_fn(n))
todo = tier1 + tier2
days = len(todo) * (86400/4000) / 86400
print(f'Tier1 (tagged): {len(tier1)}, Tier2 (SSA): {len(tier2)}, Total: {len(todo)}, ~{days:.1f} days')
print(f'Top 5 tagged not yet fetched: {tier1[:5]}')
print(f'Top 5 SSA not yet fetched: {tier2[:5]}')
"
```

Expected: tier1 has a few hundred names (tags.json names not yet in namedata.json), tier2 has ~99k names. Days ~25.

- [ ] **Step 3: Commit**

```bash
git add fetch_all_namedata.py
git commit -m "fix: update API rate limit to 4000/day, simplify priority queue to all-tags-first"
```

---

## Task 5: Cultural Category Scraper

**Files:**
- Create: `fetch_cultural_tags.py`

This script scrapes the BTN glossary page to discover cultural categories, then paginates through each category's name list, and outputs new arrays for `tags.json`.

- [ ] **Step 1: Write the scraper**

Create `fetch_cultural_tags.py`:

```python
#!/usr/bin/env python3
"""
Scrape Behind the Name cultural category pages and output name lists
for adding to tags.json.

Usage:
    python3 fetch_cultural_tags.py              # print all categories + counts
    python3 fetch_cultural_tags.py arabic       # scrape and print names for one category
    python3 fetch_cultural_tags.py --all        # scrape all categories, write cultural_tags.json

Rate: 1 request/2 seconds (polite crawl, no API key needed).
"""

import sys
import time
import json
import re
import urllib.request
from html.parser import HTMLParser

DELAY = 2.0
BASE  = "https://www.behindthename.com"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8", errors="replace")

# ── 1. Parse glossary page for cultural categories ────────────────────────────

def get_categories():
    """Return list of (label, slug) from the glossary page."""
    html = fetch(f"{BASE}/glossary/view/name")
    # Links like /names/usage/jewish, /names/usage/arabic, etc.
    matches = re.findall(r'href="/names/usage/([^"]+)"[^>]*>([^<]+)<', html)
    seen = set()
    categories = []
    for slug, label in matches:
        label = label.strip()
        if slug not in seen and label:
            seen.add(slug)
            categories.append((label, slug))
    return categories

# ── 2. Scrape a single category page (paginated) ──────────────────────────────

def scrape_category(slug):
    """Return sorted list of name strings for a BTN usage category."""
    names = set()
    page = 1
    while True:
        url = f"{BASE}/names/usage/{slug}/{page}"
        html = fetch(url)
        # Name links: <a class="nl" href="/name/aaron">Aaron</a>
        found = re.findall(r'<a class="nl"[^>]*>([^<]+)</a>', html)
        if not found:
            break
        names.update(n.strip() for n in found)
        # Check for next page link
        if f'/names/usage/{slug}/{page + 1}' not in html:
            break
        page += 1
        time.sleep(DELAY)
    return sorted(names)

# ── 3. Main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        # Just list categories
        cats = get_categories()
        print(f"Found {len(cats)} cultural categories:\n")
        for label, slug in cats:
            print(f"  {slug:<30} {label}")

    elif args[0] == "--all":
        # Scrape all categories
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
        # Scrape a single named category
        slug = args[0]
        print(f"Scraping category: {slug}")
        names = scrape_category(slug)
        print(f"Found {len(names)} names:")
        for n in names:
            print(f"  {n}")
```

- [ ] **Step 2: Test — list categories**

```bash
python3 fetch_cultural_tags.py
```

Expected output: a list of ~18–20 category slugs and labels, including `jewish`, `arabic`, `celtic`, `germanic`, `ancient-greek`, etc.

- [ ] **Step 3: Test — scrape one category**

```bash
python3 fetch_cultural_tags.py arabic
```

Expected: a list of Arabic names (likely 100–500+). Verify a few known names appear (e.g. Ahmed, Fatima, Omar).

- [ ] **Step 4: Commit**

```bash
git add fetch_cultural_tags.py
git commit -m "feat: add cultural category scraper for behindthename.com"
```

---

## Self-Review

**Spec coverage:**
- ✅ Boolean usage search with AND/OR/NOT/parens — Task 1
- ✅ Jewish injection + checkbox removal — Task 2
- ✅ Thematic easter eggs (~water already works after Task 1; ~fire/~celestial/~music — Task 3)
- ✅ API rate limit 4000/day + all-tags-first priority — Task 4
- ✅ Cultural category scraper — Task 5
- ✅ `~bogus` unknown themes return no results (covered in Task 3 verification)

**Placeholder scan:** No TBDs. All code is complete.

**Type consistency:**
- `buildUsageMatcher(raw)` returns `((usages: {usage_full, usage_code}[]) => boolean) | null` — consistent across Task 1 and its use in `getFiltered()`
- `tagSets` is `Record<string, Set<string>>` — unchanged
- `themeSet` is `Set<string>` or `null` — used correctly in filter
- `tagged_names` in `fetch_all_namedata.py` replaces `jewish_names`/`water_names` — all references updated
