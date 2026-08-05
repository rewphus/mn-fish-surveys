#!/usr/bin/env python3
"""Supplements the main pipeline output with MN DNR's Large Lake Program lakes,
which are systematically absent from the IBI-layer candidate list used by
fetch_survey_data.py (confirmed via Mille Lacs: it has a real 2025 survey but
was never in that candidate set). Verified DOW numbers below were each checked
individually against the LakeFinder metadata API before use.

Lake Pepin (the ~29,295-acre Mississippi River pool one) is deliberately
excluded — could not reliably locate its DOW as a standard lake-survey entry,
and as a river pool it may not follow the same survey/DOW pattern at all.
"""
import json
import sys
import time

sys.path.insert(0, ".")
from fetch_survey_data import get_lake_surveys, get_lake_metadata, qualifying_surveys, DELAY_SECONDS

LARGE_LAKES = {
    "04003000": "Cass",
    "69084500": "Kabetogama",
    "39000200": "Lake of the Woods",
    "11020300": "Leech",
    "48000200": "Mille Lacs",
    "69069400": "Rainy",
    "04003501": "Upper Red",
    "69037800": "Vermilion",
    "11014700": "Winnibigoshish",
}

YEAR_START, YEAR_END = 2025, 2026

with open("data/mn_fish_surveys_2025_2026.json") as f:
    dataset = json.load(f)

existing_dows = {lake["dow"] for lake in dataset["lakes"]}
added = []

for dow, name_hint in LARGE_LAKES.items():
    if dow in existing_dows:
        print(f"{name_hint} ({dow}) already present, skipping", file=sys.stderr)
        continue
    result = get_lake_surveys(dow)
    time.sleep(DELAY_SECONDS)
    if not result:
        print(f"{name_hint} ({dow}): no result from API", file=sys.stderr)
        continue
    qualifying = qualifying_surveys(result, YEAR_START, YEAR_END)
    if not qualifying:
        print(f"{name_hint} ({dow}): no {YEAR_START}-{YEAR_END} survey found", file=sys.stderr)
        continue
    meta = get_lake_metadata(dow)
    time.sleep(DELAY_SECONDS)
    entry = {
        "dow": dow,
        "lake_name": result.get("lakeName") or name_hint,
        "county": meta.get("county") if meta else None,
        "nearest_town": meta.get("nearest_town") if meta else None,
        "point": meta.get("point") if meta else None,
        "surveys": qualifying,
    }
    dataset["lakes"].append(entry)
    added.append((name_hint, len(qualifying)))
    print(f"{name_hint} ({dow}): added, {len(qualifying)} qualifying survey(s)", file=sys.stderr)

dataset["qualifying_lake_count"] = len(dataset["lakes"])
dataset["total_surveys_found"] += sum(n for _, n in added)
dataset["large_lake_supplement"] = {
    "checked": len(LARGE_LAKES),
    "added": [name for name, _ in added],
    "excluded": ["Lake Pepin (Mississippi River pool, DOW not reliably located / may not fit standard survey pattern)"],
}

with open("data/mn_fish_surveys_2025_2026.json", "w") as f:
    json.dump(dataset, f, indent=2)

print(f"\nAdded {len(added)} large lakes. New totals: {dataset['qualifying_lake_count']} lakes, {dataset['total_surveys_found']} surveys.", file=sys.stderr)
