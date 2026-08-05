#!/usr/bin/env python3
"""
Pulls MN DNR fish lake survey data for a given year range.

Two-step, server-side only (no CORS concerns since nothing here runs in a browser):
1. Enumerate candidate lakes from the DNR IBI ArcGIS layer (broad candidate set,
   not trusted for its own survey_year field).
2. For each candidate DOW, hit the confirmed-authoritative lake_survey detail API
   and keep the lake only if IT reports a survey actually dated within the
   requested year range.

Re-run with different --year-start/--year-end to pull other years later;
nothing here is hardcoded to 2025-2026 except the defaults.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

FEATURE_SERVER = "https://enterprise.gisdata.mn.gov/aghost/rest/services/us_mn_state_dnr/env_ibi_lakes_fisheries/FeatureServer/0/query"
DETAIL_API = "https://maps.dnr.state.mn.us/cgi-bin/lakefinder/detail.cgi"
METADATA_API = "https://services.dnr.state.mn.us/api/lakefinder/by_id/v1/"
USER_AGENT = "mn-fish-surveys-research-script/1.0 (personal use)"
DELAY_SECONDS = 0.25
PAGE_SIZE = 2000
MAX_RETRIES = 2


def fetch_json(url, retries=MAX_RETRIES):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_err = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last_err = e
            time.sleep(1 + attempt)
    raise last_err


def get_candidate_lakes():
    """Paginate the ArcGIS FeatureServer for the full dow -> lake_name candidate set."""
    lakes = {}
    offset = 0
    while True:
        params = {
            "where": "1=1",
            "outFields": "dow,lake_name",
            "f": "json",
            "resultOffset": offset,
            "resultRecordCount": PAGE_SIZE,
            "returnGeometry": "false",
        }
        url = f"{FEATURE_SERVER}?{urllib.parse.urlencode(params)}"
        data = fetch_json(url)
        feats = data.get("features", [])
        for feat in feats:
            attrs = feat["attributes"]
            dow = attrs.get("dow")
            if dow:
                lakes[dow] = attrs.get("lake_name")
        if len(feats) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return lakes


def get_lake_surveys(dow):
    url = f"{DETAIL_API}?type=lake_survey&id={urllib.parse.quote(dow)}"
    data = fetch_json(url)
    return data.get("result")


def get_lake_metadata(dow):
    url = f"{METADATA_API}?id={urllib.parse.quote(dow)}"
    data = fetch_json(url)
    results = data.get("results", [])
    return results[0] if results else None


def qualifying_surveys(result, year_start, year_end):
    out = []
    for s in result.get("surveys", []):
        date = s.get("surveyDate", "")
        if not date or len(date) < 4:
            continue
        try:
            year = int(date[:4])
        except ValueError:
            continue
        if year_start <= year <= year_end:
            out.append(s)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year-start", type=int, default=2025)
    parser.add_argument("--year-end", type=int, default=2026)
    parser.add_argument("--out", default=None)
    parser.add_argument("--limit", type=int, default=None, help="cap candidate lakes (debug)")
    args = parser.parse_args()

    out_path = args.out or f"data/mn_fish_surveys_{args.year_start}_{args.year_end}.json"

    print("Fetching candidate lake list...", file=sys.stderr, flush=True)
    candidates = get_candidate_lakes()
    print(f"Got {len(candidates)} candidate lakes", file=sys.stderr, flush=True)

    items = list(candidates.items())
    if args.limit:
        items = items[: args.limit]

    results = []
    errors = []
    total_surveys_found = 0

    for i, (dow, name_hint) in enumerate(items):
        if i % 50 == 0:
            print(f"Progress: {i}/{len(items)} candidates checked, {len(results)} qualifying so far", file=sys.stderr, flush=True)
        try:
            result = get_lake_surveys(dow)
        except Exception as e:
            errors.append({"dow": dow, "lake_name": name_hint, "stage": "survey", "error": str(e)})
            time.sleep(DELAY_SECONDS)
            continue

        time.sleep(DELAY_SECONDS)

        if not result:
            continue

        qualifying = qualifying_surveys(result, args.year_start, args.year_end)
        if not qualifying:
            continue

        total_surveys_found += len(qualifying)

        try:
            meta = get_lake_metadata(dow)
        except Exception as e:
            meta = None
            errors.append({"dow": dow, "lake_name": name_hint, "stage": "metadata", "error": str(e)})
        time.sleep(DELAY_SECONDS)

        results.append(
            {
                "dow": dow,
                "lake_name": result.get("lakeName") or name_hint,
                "county": meta.get("county") if meta else None,
                "nearest_town": meta.get("nearest_town") if meta else None,
                "point": meta.get("point") if meta else None,
                "surveys": qualifying,
            }
        )

    output = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "year_range": [args.year_start, args.year_end],
        "candidate_lake_count": len(items),
        "qualifying_lake_count": len(results),
        "total_surveys_found": total_surveys_found,
        "error_count": len(errors),
        "lakes": results,
        "errors": errors,
    }

    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(
        f"Done. {len(results)} lakes with {total_surveys_found} qualifying surveys "
        f"({args.year_start}-{args.year_end}), {len(errors)} errors. Wrote {out_path}",
        file=sys.stderr,
        flush=True,
    )


if __name__ == "__main__":
    main()
