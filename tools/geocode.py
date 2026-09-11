#!/usr/bin/env python3
"""Fill in lat/lng for church records using a free geocoder. Run this on a machine with normal internet access.

    python3 tools/geocode.py                 # every record with geocode == "missing"
    python3 tools/geocode.py fbc-tucson      # one slug
    python3 tools/geocode.py --upgrade       # also re-geocode "approximate" records
    python3 tools/geocode.py --provider census

Providers:
    nominatim (default)  OpenStreetMap Nominatim. Free, 1 request/second, requires a descriptive User-Agent.
    census               US Census Bureau geocoder. Free, no key, US street addresses only.

A house-number-level match is stored as geocode "verified"; anything coarser is stored as "approximate".
Nothing is written when the geocoder returns no result or a result outside the Tucson area.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHURCHES_DIR = ROOT / "data" / "churches"
USER_AGENT = "tucson-church-map/0.1 (github.com/gmfennema/church_plagerism)"
BOUNDS = {"lat": (31.5, 33.0), "lng": (-111.8, -110.2)}


def fetch_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def nominatim(address: str) -> tuple[float, float, str] | None:
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({"q": address, "format": "jsonv2", "limit": 1, "countrycodes": "us", "addressdetails": 1})
    results = fetch_json(url)
    if not results:
        return None
    hit = results[0]
    precise = hit.get("addresstype") in {"building", "house", "place_of_worship", "amenity", "church"} or "house_number" in hit.get("address", {})
    return float(hit["lat"]), float(hit["lon"]), "verified" if precise else "approximate"


def census(address: str) -> tuple[float, float, str] | None:
    url = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?" + urllib.parse.urlencode({"address": address, "benchmark": "Public_AR_Current", "format": "json"})
    data = fetch_json(url)
    matches = data.get("result", {}).get("addressMatches", [])
    if not matches:
        return None
    coords = matches[0]["coordinates"]
    return float(coords["y"]), float(coords["x"]), "verified" if matches[0].get("tigerLine") else "approximate"


PROVIDERS = {"nominatim": nominatim, "census": census}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slugs", nargs="*")
    parser.add_argument("--provider", choices=PROVIDERS, default="nominatim")
    parser.add_argument("--upgrade", action="store_true", help="also re-geocode records marked approximate")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    files = [CHURCHES_DIR / f"{s}.json" for s in args.slugs] if args.slugs else sorted(CHURCHES_DIR.glob("*.json"))
    geocode = PROVIDERS[args.provider]
    changed = 0
    for path in files:
        record = json.loads(path.read_text(encoding="utf-8"))
        loc = record["location"]
        if loc.get("geocode") == "verified" or (loc.get("geocode") == "approximate" and not args.upgrade):
            continue
        query = ", ".join(part for part in [loc.get("address"), loc.get("city"), loc.get("state"), loc.get("postal_code")] if part)
        try:
            result = geocode(query)
        except Exception as exc:  # noqa: BLE001
            print(f"ERR  {record['slug']}: {exc}")
            continue
        if args.provider == "nominatim":
            time.sleep(1.1)
        if not result:
            print(f"none {record['slug']}: no match for '{query}'")
            continue
        lat, lng, quality = result
        if not (BOUNDS["lat"][0] <= lat <= BOUNDS["lat"][1] and BOUNDS["lng"][0] <= lng <= BOUNDS["lng"][1]):
            print(f"skip {record['slug']}: result {lat:.4f},{lng:.4f} is outside the Tucson area")
            continue
        print(f"{quality:11s} {record['slug']}: {lat:.5f}, {lng:.5f}")
        if args.dry_run:
            continue
        loc["lat"], loc["lng"], loc["geocode"] = round(lat, 6), round(lng, 6), quality
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        changed += 1
    print(f"\n{changed} record(s) updated. Run python3 tools/validate.py && python3 tools/build.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
