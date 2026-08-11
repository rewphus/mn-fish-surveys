#!/usr/bin/env python3
"""Flattens the raw pipeline output + species dictionary into one lean JSON
array (one row per lake/survey/species) for embedding directly in the Artifact.

DNR surveys use multiple gear types per visit (standard gill nets, standard
trap nets, electrofishing) and report a separate catch summary per species
per gear type - not a single number per species. Anglers don't care which
net caught what, so this combines gear entries per (lake, date, species):
  - catch: summed (a real total, valid to add)
  - avgWeight: catch-weighted average, computed from each entry's totalWeight
    (grams, converted to lb) divided by combined catch - not a naive average
    of averages, which would over-weight low-catch gear entries
  - min/max length: already a single shared value per species per survey in
    DNR's data (not split by gear), so no combination needed there
  - CPUE is dropped entirely: it's catch-per-unit-effort for one specific
    gear type, and different gear types don't share a unit of "effort", so
    there's no valid single combined CPUE. Manufacturing one by summing
    catch/gearCount across incompatible gear types would produce a number
    that looks precise but isn't real.
"""
import json
from collections import defaultdict

GRAMS_PER_LB = 453.592

with open("data/mn_fish_surveys_2025_2026.json") as f:
    raw = json.load(f)

with open("fish_species.json") as f:
    species = json.load(f)


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


rows = []
for lake in raw["lakes"]:
    point = lake.get("point") or {}
    latlon = point.get("epsg:4326")  # DNR returns [lon, lat]
    lat = latlon[1] if latlon else None
    lon = latlon[0] if latlon else None
    for survey in lake["surveys"]:
        by_species = defaultdict(list)
        for fc in survey.get("fishCatchSummaries", []):
            by_species[fc.get("species")].append(fc)

        for code, entries in by_species.items():
            sp = species.get(code, {})
            lengths = survey.get("lengths", {}).get(code, {})

            total_catch = sum(fc.get("totalCatch") or 0 for fc in entries)
            total_weight_g = sum(to_float(fc.get("totalWeight")) or 0 for fc in entries)
            avg_weight_lb = (total_weight_g / GRAMS_PER_LB / total_catch) if total_catch else None

            rows.append(
                {
                    "lake": lake["lake_name"],
                    "county": lake.get("county"),
                    "dow": lake["dow"],
                    "lat": lat,
                    "lon": lon,
                    "date": survey.get("surveyDate"),
                    "surveyType": survey.get("surveySubType") or survey.get("surveyType"),
                    "code": code,
                    "name": sp.get("common_name", code).title() if sp.get("common_name") else code,
                    "gameFish": bool(sp.get("game_fish")),
                    "group": sp.get("species_group"),
                    "catch": total_catch,
                    "avgWeight": round(avg_weight_lb, 2) if avg_weight_lb is not None else None,
                    "minLen": lengths.get("minimum_length"),
                    "maxLen": lengths.get("maximum_length"),
                }
            )

meta = {
    "generated": raw["generated"],
    "yearRange": raw["year_range"],
    "candidateLakes": raw["candidate_lake_count"],
    "qualifyingLakes": raw["qualifying_lake_count"],
    "totalSurveys": raw["total_surveys_found"],
}

out = {"meta": meta, "rows": rows}

with open("app_data.json", "w") as f:
    json.dump(out, f, separators=(",", ":"))

print(f"{len(rows)} rows written to app_data.json")
import os
print(f"file size: {os.path.getsize('app_data.json') / 1024:.0f} KB")
