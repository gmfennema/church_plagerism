#!/usr/bin/env python3
"""Combine fetched Chris McLaughlin YouTube caption JSON files into one corpus.

Run from the repository root after tools/fetch_transcripts.py has fetched the
YouTube URLs recorded in the source manifest. Missing items stay in a coverage
report; this script never fills gaps with invented text.
"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESEARCH = Path(__file__).resolve().parent
TRANSCRIPTS = RESEARCH / "transcripts"
MANIFEST = RESEARCH / "chris-mclaughlin-source-manifest.json"
OUT = RESEARCH / "chris-mclaughlin-all-sermons.txt"
COVERAGE = RESEARCH / "chris-mclaughlin-coverage.json"


def clock(seconds):
    total = round(float(seconds))
    return f"{total // 3600:02d}:{(total // 60) % 60:02d}:{total % 60:02d}"


def main():
    source = json.loads(MANIFEST.read_text(encoding="utf-8"))
    items = source["items"]
    output = [
        "Chris McLaughlin — The Fields Presbyterian Church",
        "Source archive: " + source["source"],
        "YouTube captions, unedited; recognition errors may remain.",
        "Each section identifies its original recording and caption source.",
        "",
    ]
    coverage = []
    for item in sorted(items, key=lambda x: (x.get("date") or "", x["short_code"])):
        video_id = item.get("youtube_id")
        matches = list(TRANSCRIPTS.glob(f"*_{video_id}.json")) if video_id else []
        status = "no_youtube_match" if not video_id else "captions_missing"
        if len(matches) == 1:
            record = json.loads(matches[0].read_text(encoding="utf-8"))
            snippets = record.get("snippets", [])
            if snippets:
                status = "included"
                output.extend([
                    "=" * 72,
                    f"{item['date'][:10]} | {item['title']}",
                    f"Speaker: {item['speaker']}",
                    f"Scripture: {item.get('scripture') or 'not listed'}",
                    f"Church page: {item['site_url']}",
                    f"YouTube: {item['youtube_url']}",
                    f"Captions: {'auto-generated' if record.get('is_generated') else 'human-created'} ({record.get('language_code', 'unknown')})",
                    "=" * 72,
                    "",
                ])
                output.extend(f"[{clock(s['start'])}] {s['text'].strip()}" for s in snippets)
                output.append("")
        coverage.append({
            "short_code": item["short_code"], "title": item["title"],
            "date": item.get("date"), "site_url": item["site_url"],
            "youtube_url": item.get("youtube_url"), "status": status,
        })

    OUT.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
    COVERAGE.write_text(json.dumps({
        "source_count": len(items),
        "included_count": sum(x["status"] == "included" for x in coverage),
        "entries": coverage,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Included {sum(x['status'] == 'included' for x in coverage)}/{len(items)} items in {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
