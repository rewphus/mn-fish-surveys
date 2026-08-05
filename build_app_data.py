#!/usr/bin/env python3
"""Flattens the raw pipeline output + species dictionary into one lean JSON
array (one row per lake/survey/species) for embedding directly in the Artifact."""
import json

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
    for survey in lake["surveys"]:
        for fc in survey.get("fishCatchSummaries", []):
            code = fc.get("species")
            sp = species.get(code, {})
            lengths = survey.get("lengths", {}).get(code, {})
            rows.append(
                {
                    "lake": lake["lake_name"],
                    "county": lake.get("county"),
                    "dow": lake["dow"],
                    "date": survey.get("surveyDate"),
                    "surveyType": survey.get("surveySubType") or survey.get("surveyType"),
                    "code": code,
                    "name": sp.get("common_name", code).title() if sp.get("common_name") else code,
                    "gameFish": bool(sp.get("game_fish")),
                    "group": sp.get("species_group"),
                    "catch": fc.get("totalCatch"),
                    "cpue": to_float(fc.get("CPUE")),
                    "avgWeight": to_float(fc.get("averageWeight")),
                    "gear": fc.get("gear"),
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
