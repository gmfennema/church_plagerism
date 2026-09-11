#!/usr/bin/env python3
"""Compile data/churches/*.json into the static site.

    python3 tools/build.py            # validate, derive statuses, write site/data/churches.json, copy reports
    python3 tools/build.py --no-validate

Then preview locally:  python3 -m http.server -d site 8000  ->  http://localhost:8000

Derived church status (worst case across pastors, plagiarism and AI findings both considered):
    flagged      any pastor has a flagged finding
    in_progress  otherwise, any finding is in_progress
    cleared      every active pastor's plagiarism finding is cleared (AI may still be unchecked; shown separately)
    partial      some pastor has been reviewed (cleared/inconclusive) but not everyone is cleared
    unchecked    nobody has been reviewed (or no pastors are listed yet)
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from validate import main as validate_main  # noqa: E402

CHURCHES_DIR = ROOT / "data" / "churches"
SITE = ROOT / "site"
SITE_DATA = SITE / "data"
SITE_REPORTS = SITE / "reports"

TRADITION_LABELS = {
    "baptist": "Baptist",
    "presbyterian_reformed": "Presbyterian / Reformed",
    "lutheran": "Lutheran",
    "methodist_wesleyan": "Methodist / Wesleyan",
    "anglican_episcopal": "Anglican / Episcopal",
    "pentecostal_charismatic": "Pentecostal / Charismatic",
    "non_denominational": "Non-denominational",
    "evangelical_free": "Evangelical Free",
    "nazarene_holiness": "Nazarene / Holiness",
    "restoration_churches_of_christ": "Churches of Christ / Christian Church",
    "mennonite_anabaptist": "Mennonite / Anabaptist",
    "adventist": "Adventist",
    "other_protestant": "Other Protestant",
}
STATUS_ORDER = ["unchecked", "partial", "in_progress", "cleared", "flagged"]


def derive_status(pastors: list[dict[str, Any]]) -> tuple[str, str, str]:
    """Return (status, ai_status, reason)."""
    active = [p for p in pastors if p.get("active", True)] or pastors
    if not active:
        return "unchecked", "unchecked", "No preaching pastors identified yet."
    plag = [p["plagiarism"]["status"] for p in active]
    ai = [p["ai_writing"]["status"] for p in active]
    both = plag + ai
    if "flagged" in both:
        names = [p["name"] for p in active if "flagged" in (p["plagiarism"]["status"], p["ai_writing"]["status"])]
        status = "flagged"
        reason = "Flag on: " + ", ".join(names)
    elif "in_progress" in both:
        status, reason = "in_progress", "A review is under way."
    elif all(s == "cleared" for s in plag):
        status, reason = "cleared", "All preaching pastors cleared on plagiarism."
    elif all(s == "unchecked" for s in both):
        status, reason = "unchecked", "Not yet reviewed."
    else:
        status, reason = "partial", "Some pastors reviewed; not all cleared."

    if "flagged" in ai:
        ai_status = "flagged"
    elif "in_progress" in ai:
        ai_status = "in_progress"
    elif all(s == "cleared" for s in ai):
        ai_status = "cleared"
    elif all(s == "unchecked" for s in ai):
        ai_status = "unchecked"
    else:
        ai_status = "partial"
    return status, ai_status, reason


def site_report(report: dict[str, Any], slug: str) -> dict[str, Any]:
    rel = Path(report["path"])
    inner = rel.relative_to(Path("research") / slug)
    target = SITE_REPORTS / slug / inner
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / rel, target)
    size = target.stat().st_size
    return {**report, "url": f"reports/{slug}/{inner.as_posix()}", "size_bytes": size}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-validate", action="store_true")
    args = parser.parse_args()

    if not args.no_validate and validate_main([]) != 0:
        print("\nBuild aborted: fix validation errors first.")
        return 1

    if SITE_REPORTS.exists():
        shutil.rmtree(SITE_REPORTS)
    SITE_DATA.mkdir(parents=True, exist_ok=True)

    churches: list[dict[str, Any]] = []
    out_of_scope: list[dict[str, str]] = []
    for path in sorted(CHURCHES_DIR.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("in_scope", True) is False:
            out_of_scope.append({"slug": record["slug"], "name": record["name"], "reason": record.get("out_of_scope_reason", "")})
            continue
        slug = record["slug"]
        status, ai_status, reason = derive_status(record.get("pastors", []))
        pastors = []
        for pastor in record.get("pastors", []):
            pastors.append({**pastor, "reports": [site_report(r, slug) for r in pastor.get("reports", [])]})
        churches.append({
            **record,
            "tradition_label": TRADITION_LABELS.get(record["tradition"], record["tradition"]),
            "status": status,
            "ai_status": ai_status,
            "status_reason": reason,
            "pastors": pastors,
            "reports": [site_report(r, slug) for r in record.get("reports", [])],
            "plotted": record["location"].get("lat") is not None and record["location"].get("lng") is not None,
        })

    counts = {s: sum(c["status"] == s for c in churches) for s in STATUS_ORDER}
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "church_count": len(churches),
        "plotted_count": sum(c["plotted"] for c in churches),
        "pastor_count": sum(len(c["pastors"]) for c in churches),
        "counts": counts,
        "traditions": TRADITION_LABELS,
        "out_of_scope": out_of_scope,
        "churches": sorted(churches, key=lambda c: c["name"].lower()),
    }
    (SITE_DATA / "churches.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nBuilt site/data/churches.json: {len(churches)} churches ({payload['plotted_count']} plotted), {payload['pastor_count']} pastors, statuses {counts}")
    if out_of_scope:
        print(f"Excluded {len(out_of_scope)} out-of-scope record(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
