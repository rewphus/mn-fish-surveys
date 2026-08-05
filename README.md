# MN Lake Fish Surveys

A browsable table of every species logged in a Minnesota DNR lake survey dated 2025 or 2026 — catch counts, CPUE, average weight, and measured size range — built directly from DNR's own (undocumented but open) survey API.

**Live:** enable GitHub Pages on this repo (Settings → Pages → Source: `main` branch, `/ (root)`) and it serves straight from `index.html`.

## How it's built

Three-stage pipeline, all server-side (no CORS issues since nothing runs in a browser until the final static page):

1. **`fetch_survey_data.py`** — pulls a candidate list of ~959 lakes from DNR's biotic-integrity ArcGIS layer, then checks each one's *actual* survey history against the authoritative `maps.dnr.state.mn.us` lake-survey API and keeps whatever falls in the requested year range. Re-run with `--year-start`/`--year-end` for other years.
2. **`add_large_lakes.py`** — the candidate list above systematically excludes DNR's Large Lake Program waters (Mille Lacs, Leech, Winnibigoshish, etc. — confirmed by checking Mille Lacs directly). This adds a hand-verified list of those DOW numbers and pulls their data the same way.
3. **`build_app_data.py`** — flattens the raw survey JSON into one row per lake/survey/species, decoding DNR's species codes via `fish_species.json` (extracted from LakeFinder's own client-side JS, not hand-typed).
4. **`assemble.py`** — inlines the flattened dataset and an embedded webfont into `template.html`, producing the final self-contained `index.html`. No build tooling, no dependencies, no server needed at runtime.

## Known gaps

- Not a complete census of every 2025-2026 MN fish survey — bounded by the ~959-lake candidate list plus the 9 manually-added large lakes.
- Lake Pepin (the Mississippi River pool one) is still missing — couldn't reliably locate its DOW number, and as a river pool it may not follow the standard lake-survey pattern at all.
- Surveys with no logged catch (mostly "Targeted Survey" type — likely invasive-species or single-species checks) don't produce rows, so the app's lake count is lower than the raw survey count.

## Rebuilding

```
python3 fetch_survey_data.py --year-start 2025 --year-end 2026
python3 add_large_lakes.py
python3 build_app_data.py
python3 assemble.py
```

Not an official DNR product.
