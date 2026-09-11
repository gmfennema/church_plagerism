#!/usr/bin/env python3
"""Scaffold a new church record that passes validation.

    python3 tools/new_church.py --name "Grace Community Church" --tradition non_denominational \
        --address "123 E Example Rd" --zip 85710 --website https://example.org \
        --youtube https://www.youtube.com/@example --pastor "Jane Doe|Lead Pastor" \
        --source "Church website staff page|https://example.org/staff" --by "claude research agent"

Prints the path written. Coordinates start as null/missing; run tools/geocode.py to fill them.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def slugify(name: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", name.lower())).strip("-")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", required=True)
    parser.add_argument("--slug", help="defaults to a slug of the name")
    parser.add_argument("--tradition", required=True)
    parser.add_argument("--denomination")
    parser.add_argument("--address", required=True)
    parser.add_argument("--city", default="Tucson")
    parser.add_argument("--zip")
    parser.add_argument("--website")
    parser.add_argument("--youtube", help="channel URL")
    parser.add_argument("--playlist", action="append", default=[], help="sermon playlist URL (repeatable)")
    parser.add_argument("--pastor", action="append", default=[], help='"Name|Role" (repeatable)')
    parser.add_argument("--source", action="append", default=[], help='"Label|URL" (repeatable, at least one)')
    parser.add_argument("--aka", action="append", default=[])
    parser.add_argument("--notes")
    parser.add_argument("--by", required=True, help="who is creating this record")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    slug = args.slug or slugify(args.name)
    path = ROOT / "data" / "churches" / f"{slug}.json"
    if path.exists() and not args.force:
        raise SystemExit(f"{path.relative_to(ROOT)} already exists (use --force to overwrite)")
    if not args.source:
        raise SystemExit("at least one --source 'Label|URL' is required: say where you verified the church facts")

    def split_pair(value: str) -> tuple[str, str]:
        left, sep, right = value.partition("|")
        if not sep:
            raise SystemExit(f"expected 'A|B' but got {value!r}")
        return left.strip(), right.strip()

    record = {
        "slug": slug,
        "name": args.name,
        "aka": args.aka,
        "in_scope": True,
        "tradition": args.tradition,
        "denomination": args.denomination or "",
        "website": args.website,
        "youtube": {
            "channel_url": args.youtube,
            "sermon_playlist_urls": args.playlist,
            "transcripts_available": "unknown",
        },
        "location": {"address": args.address, "city": args.city, "state": "AZ", "postal_code": args.zip, "lat": None, "lng": None, "geocode": "missing"},
        "summary": "Not yet reviewed.",
        "pastors": [
            {"name": n, "role": r, "active": True, "plagiarism": {"status": "unchecked"}, "ai_writing": {"status": "unchecked"}}
            for n, r in (split_pair(p) for p in args.pastor)
        ],
        "reports": [],
        "sources": [{"label": l, "url": u, "accessed": date.today().isoformat()} for l, u in (split_pair(s) for s in args.source)],
        "notes": args.notes or "",
        "updated_at": date.today().isoformat(),
        "updated_by": args.by,
    }
    # drop empty optionals so the file stays clean
    for key in ("aka", "denomination", "website", "notes"):
        if not record[key]:
            del record[key]
    if not record["youtube"]["channel_url"]:
        del record["youtube"]["channel_url"]
    if not record["youtube"]["sermon_playlist_urls"]:
        del record["youtube"]["sermon_playlist_urls"]
    if record["location"]["postal_code"] is None:
        del record["location"]["postal_code"]
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT)}")
    print("next: python3 tools/validate.py", slug, "&& python3 tools/geocode.py", slug)


if __name__ == "__main__":
    main()
