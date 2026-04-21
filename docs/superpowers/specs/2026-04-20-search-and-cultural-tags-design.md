# Design: Search Improvements & Cultural Name Tags

**Date:** 2026-04-20  
**Status:** Approved

---

## Overview

Four related improvements to the name filtering system, ordered by implementation priority (non-scraping work first):

1. Boolean usage search
2. Cultural name tags (Jewish → usage field; UI cleanup)
3. Thematic easter eggs (`~water`, `~fire`, etc.)
4. Cultural category scraping from behindthename.com
5. API enrichment (ongoing background task)

---

## Feature 1: Boolean Usage Search

**What:** The Usage text field gains full boolean support. Currently it does a plain substring match against any `usage_full` or `usage_code`. New behavior: parse the query as a boolean expression.

**Grammar:**
```
expr → term (('AND' | 'OR') term)*
term → 'NOT' atom | '(' expr ')' | atom
atom → word
```

`word` matches case-insensitively as a substring against any usage's `usage_full` or `usage_code`. A name passes if the root expression evaluates to true.

**Examples:**
- `Hebrew AND Biblical` — names with both Hebrew and Biblical usages
- `Hebrew OR Arabic` — names in either tradition
- `Hebrew AND (English OR French) NOT Archaic` — Hebrew names in English or French but not archaic

**Implementation:** ~70-line recursive descent parser inline in `index.html`. If parsing fails (malformed input), silently fall back to the current substring match so existing saved queries aren't broken.

**UI change:** Update the placeholder text to hint at boolean syntax, e.g. `Hebrew AND Biblical`.

---

## Feature 2: Cultural Name Tags (Jewish → Usage Field)

**Background:** The BTN API returns language/etymology codes (Hebrew, Biblical, English, etc.) but does NOT return cultural classifications like "Jewish". The BTN website maintains separate cultural name lists at `/names/usage/{code}` (e.g. `/names/usage/jewish`). Abraham, for example, returns Hebrew + Biblical from the API but does not get `usage_code: jewish` — yet it's #2 on the Jewish names page.

**Architecture:**
- `tags.json` is the authoritative source for cultural name lists (jewish, water, future cultures)
- `namedata.json` is the authoritative source for language/etymology from the API
- These are complementary, not redundant

**Frontend change:** At data init time, for every name in `tagSets.jewish`, inject a synthetic usage entry into that name's `nameData` record if not already present:
```js
{ usage_code: "jewish", usage_full: "Jewish" }
```
This is permanent — not a temporary bridge — because the API will never return this data.

**UI change:** Remove the "Jewish" checkbox from the Tags section. Searching `Jewish` in the Usage field replaces it. The `tagSets.jewish` Set is still maintained internally (for the injection and for including non-SSA names in `allNames`).

**No change to tags.json format.** The jewish list remains as-is; it may be refreshed via scraping later (Feature 4).

---

## Feature 3: Thematic Easter Eggs

**What:** Usage queries starting with `~` are treated as thematic set lookups. If `tagSets[word]` exists, filter to names in that set. If not, treat as a normal search (no error).

**Trigger format:** `~word` (lowercase, no spaces) — e.g. `~water`, `~fire`, `~celestial`.

**Themes in tags.json:**

| Key | Description | ~Count |
|-----|-------------|--------|
| `water` | Water-related names (existing) | 61 |
| `fire` | Fire, flame, and heat names | ~30 |
| `celestial` | Stars, planets, sky, light | ~30 |
| `music` | Musical terms and sounds | ~20 |

Sample names for new themes:
- **fire:** Aidan, Blaze, Ember, Seraphina, Cyrus, Ignatius, Brigid, Pele, Azar, Kenneth, Nuri, Edan, Fiamma, Kai (fire sense), Alinta, Kalinda, Tama
- **celestial:** Aurora, Orion, Luna, Phoebe, Stella, Rigel, Cassidy, Selene, Helios, Soleil, Cressida, Vesper, Elio, Nova, Lyra, Vega, Altair, Castor, Pollux, Electra
- **music:** Aria, Lyric, Melody, Harmony, Cadence, Viola, Carol, Calliope, Psalter, Serenade, Coda, Riff, Allegra

None of these themes appear anywhere in the UI. They're only triggered by knowing the keyword.

**Note:** The `water` list in `tags.json` is not authoritative (hand-made). All thematic lists are editorial and carry no external sourcing claim.

---

## Feature 4: Cultural Category Scraping

**What:** A Python script `fetch_cultural_tags.py` that:
1. Fetches `https://www.behindthename.com/glossary/view/name`
2. Parses the "Articles about names in selected cultures" section to get category names and URL slugs
3. For each category, paginates through `/names/usage/{code}` to collect all names in that category
4. Outputs additional entries for `tags.json` (e.g. `arabic`, `celtic`, `germanic`, `turkish`, etc.)

**Target categories from the glossary:**

*Contemporary:*
- Jewish (refresh existing list)
- Arabic
- Turkish
- Indian
- Chinese, Korean, Japanese, Vietnamese, Indonesian
- African

*Past:*
- Ancient Greek
- Roman
- Celtic
- Germanic
- Slavic
- Ancient Hebrew

**Output format:** Same as existing `tags.json` — flat arrays of name strings per culture key.

**Rate limiting:** The glossary pages are public HTML (no API key required), but should be fetched politely with delays between requests.

**Usage field autocomplete (future):** Once cultural categories are scraped, the set of known cultural codes (from both tags and namedata) can power a typeahead on the usage input. Deferred until the scraping is complete.

---

## Feature 5: API Enrichment

**What:** Continue running `fetch_all_namedata.py` to populate `namedata.json` for the remaining ~99,600 SSA names.

**Rate limit:** 4,000 requests/day (~2.7/min). Built in as a configurable constant.

**Priority order:**
1. Names in `tags.json` not yet in `namedata.json`
2. SSA names sorted by total frequency (most popular first)

**Robustness requirements:**
- Skip names already in `namedata.json` on startup
- Save incrementally every 100 names (so progress isn't lost on interrupt)
- Log progress: names fetched, names remaining, estimated days to completion

**Timeline:** ~25 days at full rate to cover all SSA names. Cultural injection (Feature 2) remains the fallback for names not yet fetched.

---

## Implementation Order

1. **Boolean usage search** — pure JS, no data dependencies
2. **Jewish → usage field injection + remove checkbox** — pure JS + existing tags.json
3. **Thematic easter eggs** — tags.json additions + ~10 lines of JS
4. **Cultural category scraping** (`fetch_cultural_tags.py`)
5. **API enrichment tuning** (`fetch_all_namedata.py` improvements)
