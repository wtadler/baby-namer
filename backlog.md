# Backlog

## Cultural category scraper (`fetch_cultural_tags.py`)
The scaffold exists but the URL pattern is wrong. The BTN glossary links to `/glossary/view/jewish_names` (article pages), not `/names/usage/jewish` (name list pages). Fix the scraper to hit the correct name-list URLs, then run it to build `cultural_tags.json` with Arabic, Celtic, Germanic, Slavic, etc. name lists for `tags.json`.

## Remove the Tags section from the UI
`tagLabels` is now `{}` so the Tags section renders empty. Remove the Tags `<div>` (and its label) from the controls panel in `index.html` entirely.

## Improve mobile layout
Continue refining the table for narrow screens — column sizing, readability, and any other mobile UX issues.
