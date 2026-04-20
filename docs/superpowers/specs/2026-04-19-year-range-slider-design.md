# Year Range Slider — Design Spec

**Date:** 2026-04-19
**Status:** Approved

## Summary

Replace the static "SSA data 2015–2024" label in the header with an interactive dual-handle range slider. Users can drag to select any year range from 1880–2024. Popularity counts are re-aggregated from cached SSA files whenever the range changes.

## Header Change

The `<header>` currently contains:
```html
<h1>Baby Name Explorer</h1>
<span>SSA data 2015–2024</span>
```

Replace the `<span>` with a dual-handle slider inline on the right side of the header (option A from mockup). Layout: `[1880] ——●————●—— [2024]  1995–2024`. The live label (e.g., `1995–2024`) sits to the right of the track and updates as the user drags. The slider reuses the existing `.dual-slider` CSS component already present for the unisex threshold control.

- Min year: 1880, Max year: 2024
- Default start: 2015, Default end: 2024 (matches current behavior)
- Step: 1 year

## Data Loading

**Current:** `loadAll()` fetches a hardcoded `YEARS = [2015…2024]` array on startup, discarding the text after aggregation.

**New:**
- Replace `const YEARS = [...]` with `const MIN_YEAR = 1880` and `const MAX_YEAR = 2024`
- Add `const yearCache = new Map()` — maps year (number) to the raw file text string
- `loadAll()` becomes `loadRange(startYear, endYear)`:
  - Iterates years in range
  - For each year: if already in `yearCache`, use cached text; otherwise fetch `ssa-data/yob${year}.txt` and store in cache
  - Re-aggregates `nameMap` from all cached texts in the selected range
  - Returns the name array (same shape as before)

## Slider Behavior

- On slider input: update the live label immediately (feel responsive)
- On slider settle (300ms debounce after `input` event stops): call `loadRange()` then re-render the table
- Thumb collision: enforce `startYear <= endYear - 1` (same pattern as unisex threshold)
- While loading: keep the existing table visible and unchanged until the new data is ready, then swap in the new results atomically. No spinner needed — SSA files are small and fetches are fast.

## Render Pipeline

No changes to the render/filter/sort logic. `loadRange()` returns the same name array shape that `loadAll()` currently returns. The rest of the pipeline is unchanged.

## Scope

All changes confined to `index.html`:
1. Header HTML — swap static span for slider markup
2. JS constants — `YEARS` → `MIN_YEAR`, `MAX_YEAR`, `yearCache`
3. `loadAll()` → `loadRange(start, end)` with cache logic
4. Slider event wiring with debounce

No changes to Python scripts, `namedata.json`, `tags.json`, or SSA data files.
