# Year Range Slider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the static "SSA data 2015–2024" label in the header with a dual-handle year range slider that re-aggregates popularity counts from cached SSA files when the range changes.

**Architecture:** All changes are in `index.html`. The existing `.dual-slider` CSS component is reused as-is. A `yearCache` Map stores fetched SSA file text keyed by year so dragging over already-loaded years is instant. Slider changes update the label immediately and debounce the data reload by 300ms.

**Tech Stack:** Vanilla JS, HTML, CSS — no build step, no dependencies.

---

### Task 1: Update header CSS and HTML

**Files:**
- Modify: `index.html:17-26` (header CSS)
- Modify: `index.html:326-329` (header HTML)

- [ ] **Step 1: Change header CSS**

Find this block (lines 17–26):
```css
  header {
    background: #fff;
    border-bottom: 1px solid #e5e0d8;
    padding: 20px 32px;
    display: flex;
    align-items: baseline;
    gap: 12px;
  }
  header h1 { font-size: 1.4rem; font-weight: 700; letter-spacing: -0.02em; }
  header span { font-size: 0.85rem; color: #888; }
```

Replace with:
```css
  header {
    background: #fff;
    border-bottom: 1px solid #e5e0d8;
    padding: 20px 32px;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  header h1 { font-size: 1.4rem; font-weight: 700; letter-spacing: -0.02em; }

  .year-range-ctrl {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-left: auto;
  }
  .year-bound {
    font-size: 0.75rem;
    color: #888;
    white-space: nowrap;
  }
  .year-label {
    font-size: 0.85rem;
    color: #3b82f6;
    font-weight: 600;
    white-space: nowrap;
    min-width: 72px;
  }
```

- [ ] **Step 2: Replace the header HTML**

Find (lines 326–329):
```html
<header>
  <h1>Baby Name Explorer</h1>
  <span>SSA data 2015–2024</span>
</header>
```

Replace with:
```html
<header>
  <h1>Baby Name Explorer</h1>
  <div class="year-range-ctrl">
    <span class="year-bound">1880</span>
    <div class="dual-slider" id="yearSlider">
      <div class="dual-fill" id="yearFill"></div>
      <input type="range" id="yearStart" min="1880" max="2024" value="2015" step="1">
      <input type="range" id="yearEnd"   min="1880" max="2024" value="2024" step="1">
    </div>
    <span class="year-bound">2024</span>
    <span class="year-label" id="yearLabel">2015–2024</span>
  </div>
</header>
```

- [ ] **Step 3: Verify visually**

Open `http://localhost:8000` in a browser. The header should show "Baby Name Explorer" on the left and a blue dual-handle slider with "1880 … 2024  2015–2024" on the right. The slider thumbs should be draggable (they won't reload data yet — that's Task 3).

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: add year range slider to header (UI only)"
```

---

### Task 2: Replace YEARS / loadAll with yearCache / loadRange

**Files:**
- Modify: `index.html:381` (YEARS constant)
- Modify: `index.html:385-419` (loadAll function)

- [ ] **Step 1: Replace the YEARS constant and add cache**

Find (line 381):
```js
const YEARS = [2015,2016,2017,2018,2019,2020,2021,2022,2023,2024];
```

Replace with:
```js
const MIN_YEAR     = 1880;
const MAX_YEAR     = 2024;
const DEFAULT_START = 2015;
const DEFAULT_END   = 2024;
const yearCache = new Map(); // year (number) -> raw file text
```

- [ ] **Step 2: Replace loadAll with loadRange**

Find the entire `loadAll` function (lines 385–419):
```js
async function loadAll() {
  const nameMap = new Map(); // name -> { m: 0, f: 0, years: Set }

  for (const year of YEARS) {
    let text;
    try {
      const res = await fetch(`ssa-data/yob${year}.txt`);
      if (!res.ok) throw new Error(res.status);
      text = await res.text();
    } catch(e) {
      console.warn(`Could not load ssa-data/yob${year}.txt:`, e);
      continue;
    }
    for (const line of text.trim().split('\n')) {
      const [name, gender, countStr] = line.split(',');
      if (!name) continue;
      const count = parseInt(countStr, 10);
      if (isNaN(count)) continue;
      if (!nameMap.has(name)) nameMap.set(name, { m: 0, f: 0, years: new Set() });
      const entry = nameMap.get(name);
      if (gender === 'M') entry.m += count;
      else if (gender === 'F') entry.f += count;
      entry.years.add(year);
    }
  }

  // Convert to array
  const names = [];
  for (const [name, { m, f }] of nameMap) {
    const total = m + f;
    const pctM = total > 0 ? (m / total) * 100 : 0;
    names.push({ name, m, f, total, pctM });
  }
  return names;
}
```

Replace with:
```js
async function loadRange(startYear, endYear) {
  const nameMap = new Map(); // name -> { m: 0, f: 0 }

  for (let year = startYear; year <= endYear; year++) {
    let text = yearCache.get(year);
    if (!text) {
      try {
        const res = await fetch(`ssa-data/yob${year}.txt`);
        if (!res.ok) throw new Error(res.status);
        text = await res.text();
        yearCache.set(year, text);
      } catch(e) {
        console.warn(`Could not load ssa-data/yob${year}.txt:`, e);
        continue;
      }
    }
    for (const line of text.trim().split('\n')) {
      const [name, gender, countStr] = line.split(',');
      if (!name) continue;
      const count = parseInt(countStr, 10);
      if (isNaN(count)) continue;
      if (!nameMap.has(name)) nameMap.set(name, { m: 0, f: 0 });
      const entry = nameMap.get(name);
      if (gender === 'M') entry.m += count;
      else if (gender === 'F') entry.f += count;
    }
  }

  const names = [];
  for (const [name, { m, f }] of nameMap) {
    const total = m + f;
    const pctM = total > 0 ? (m / total) * 100 : 0;
    names.push({ name, m, f, total, pctM });
  }
  return names;
}
```

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat: replace loadAll with loadRange using yearCache"
```

---

### Task 3: Add year slider helper functions and event wiring

**Files:**
- Modify: `index.html` — add functions after `updateThreshDesc` (line 557), add event listeners after existing slider listeners (line 593)

- [ ] **Step 1: Add updateYearFill and updateYearLabel**

After the closing `}` of `updateThreshDesc` (after line 557), insert:

```js
function updateYearFill() {
  const start = parseInt(document.getElementById('yearStart').value);
  const end   = parseInt(document.getElementById('yearEnd').value);
  const span  = MAX_YEAR - MIN_YEAR;
  const fill  = document.getElementById('yearFill');
  fill.style.left  = ((start - MIN_YEAR) / span * 100) + '%';
  fill.style.width = ((end - start)       / span * 100) + '%';
}

function updateYearLabel() {
  const start = parseInt(document.getElementById('yearStart').value);
  const end   = parseInt(document.getElementById('yearEnd').value);
  document.getElementById('yearLabel').textContent = `${start}–${end}`;
}
```

- [ ] **Step 2: Add onYearChange with debounced reload**

Immediately after the two functions above, insert:

```js
let yearDebounce = null;
async function onYearChange() {
  updateYearFill();
  updateYearLabel();
  clearTimeout(yearDebounce);
  yearDebounce = setTimeout(async () => {
    const start = parseInt(document.getElementById('yearStart').value);
    const end   = parseInt(document.getElementById('yearEnd').value);
    const names = await loadRange(start, end);
    allNames = names;
    // Re-add tagged names missing from SSA data for this range
    const ssnNames = new Set(allNames.map(n => n.name));
    for (const nameList of Object.values(tagSets)) {
      for (const name of nameList) {
        if (!ssnNames.has(name)) {
          const g = nameData[name]?.gender;
          const pctM = g === 'm' ? 100 : g === 'f' ? 0 : 50;
          allNames.push({ name, m: 0, f: 0, total: 0, pctM });
          ssnNames.add(name);
        }
      }
    }
    globalMaxTotal = Math.max(...allNames.map(n => n.total), 1);
    renderTable();
  }, 300);
}
```

- [ ] **Step 3: Add event listeners for the year slider**

After the existing dual-slider listeners (after line 593, before the `firstLetter` change listener), insert:

```js
document.getElementById('yearStart').addEventListener('input', function() {
  const endEl = document.getElementById('yearEnd');
  if (parseInt(this.value) > parseInt(endEl.value)) endEl.value = this.value;
  onYearChange();
});
document.getElementById('yearEnd').addEventListener('input', function() {
  const startEl = document.getElementById('yearStart');
  if (parseInt(this.value) < parseInt(startEl.value)) startEl.value = this.value;
  onYearChange();
});
```

- [ ] **Step 4: Verify in browser**

1. Open `http://localhost:8000`. Table should load with 2015–2024 data (same as before).
2. Drag the left thumb to 2010. After 300ms, the table should update — total counts increase since there are more years.
3. Drag the left thumb all the way to 2020. Table should show fewer totals.
4. Drag both thumbs to the same year (e.g., 2024 only). Table should still render.
5. Open DevTools Network tab. Drag left thumb to 1990, then back to 2000. Years 1990–1999 should each appear once as network requests. Dragging back to 2000 should not re-fetch those files.

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "feat: wire year slider events with debounced reload"
```

---

### Task 4: Update boot sequence to use loadRange

**Files:**
- Modify: `index.html:614-615` (boot IIFE)
- Modify: `index.html:659-660` (post-load UI init)

- [ ] **Step 1: Change loadAll() call to loadRange()**

Find (line 614–615):
```js
    const [names, tagsRaw, nameDataRaw] = await Promise.all([
      loadAll(),
```

Replace with:
```js
    const [names, tagsRaw, nameDataRaw] = await Promise.all([
      loadRange(DEFAULT_START, DEFAULT_END),
```

- [ ] **Step 2: Initialize year slider UI on boot**

Find (line 659):
```js
    updateSliderFill();
    updateThreshDesc();
```

Replace with:
```js
    updateSliderFill();
    updateThreshDesc();
    updateYearFill();
    updateYearLabel();
```

- [ ] **Step 3: Final browser verification**

1. Hard-reload `http://localhost:8000` (Cmd+Shift+R). Page loads, label reads "2015–2024", fill is visible between the thumbs.
2. Drag left thumb to 1990 — label immediately updates to "1990–2024", table re-renders after 300ms.
3. Drag right thumb to 2000 — thumb can't cross left thumb; clamps at 1990.
4. Drag both thumbs back to 2015–2024 — second visit uses cached files, no new network requests.
5. Check that unisex threshold, letter filters, search, and tags all still work correctly after a year range change.

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "feat: boot with loadRange; initialize year slider fill and label"
```
