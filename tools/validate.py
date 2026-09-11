#!/usr/bin/env python3
"""Validate every church record in data/churches/ against the schema plus project rules.

Usage:
    python3 tools/validate.py            # validate all
    python3 tools/validate.py fbc-tucson # validate one slug

Exit status is non-zero when anything fails, so CI and agents can rely on it.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "jsonschema is not installed. Run: python3 -m pip install -r tools/requirements.txt\n"
    )
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "data" / "schema" / "church.schema.json"
CHURCHES_DIR = ROOT / "data" / "churches"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_schema() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def project_rules(record: dict, path: Path) -> list[str]:
    """Rules that JSON Schema cannot express."""
    problems: list[str] = []
    slug = record.get("slug")
    if slug != path.stem:
        problems.append(f"slug '{slug}' does not match filename '{path.stem}.json'")

    loc = record.get("location", {})
    geocode = loc.get("geocode")
    has_coords = loc.get("lat") is not None and loc.get("lng") is not None
    if geocode == "missing" and has_coords:
        problems.append("location.geocode is 'missing' but lat/lng are set")
    if geocode in {"verified", "approximate"} and not has_coords:
        problems.append(f"location.geocode is '{geocode}' but lat/lng are null")

    if record.get("in_scope") is False and not record.get("out_of_scope_reason"):
        problems.append("in_scope is false but out_of_scope_reason is empty")

    # UTC, not local: records are written by agents and CI in many timezones, and a
    # record stamped in UTC reads as "tomorrow" from anywhere west of Greenwich.
    today = datetime.now(timezone.utc).date().isoformat()
    for label, value in [("updated_at", record.get("updated_at"))]:
        if value and value > today:
            problems.append(f"{label} {value} is in the future")

    def check_report(report: dict, where: str) -> None:
        rel = report.get("path", "")
        if not rel.startswith(f"research/{slug}/"):
            problems.append(f"{where}: report path '{rel}' must live under research/{slug}/")
        if not (ROOT / rel).is_file():
            problems.append(f"{where}: report file not found: {rel}")

    for i, report in enumerate(record.get("reports", [])):
        check_report(report, f"reports[{i}]")

    for p_index, pastor in enumerate(record.get("pastors", [])):
        where = f"pastors[{p_index}] ({pastor.get('name', '?')})"
        for key in ("plagiarism", "ai_writing"):
            finding = pastor.get(key, {})
            status = finding.get("status")
            if status in {"cleared", "flagged"}:
                if not finding.get("confidence"):
                    problems.append(f"{where}.{key}: status '{status}' requires a confidence")
                if not finding.get("summary"):
                    problems.append(f"{where}.{key}: status '{status}' requires a summary")
                if not finding.get("methods"):
                    problems.append(f"{where}.{key}: status '{status}' requires at least one method")
                if not pastor.get("last_reviewed"):
                    problems.append(f"{where}: last_reviewed is required once a finding is cleared/flagged")
            if status == "flagged" and not finding.get("evidence"):
                problems.append(f"{where}.{key}: 'flagged' requires at least one evidence item")
            if status == "cleared" and not finding.get("sermons_reviewed"):
                problems.append(f"{where}.{key}: 'cleared' requires sermons_reviewed > 0")
        for i, report in enumerate(pastor.get("reports", [])):
            check_report(report, f"{where}.reports[{i}]")
    return problems


def validate_file(validator: Draft202012Validator, path: Path) -> list[str]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"invalid JSON: {exc}"]
    errors = [
        f"{'/'.join(str(p) for p in err.absolute_path) or '<root>'}: {err.message}"
        for err in sorted(validator.iter_errors(record), key=lambda e: list(e.absolute_path))
    ]
    if errors:
        return errors
    return project_rules(record, path)


def main(argv: list[str]) -> int:
    validator = load_schema()
    if argv:
        files = [CHURCHES_DIR / f"{slug.removesuffix('.json')}.json" for slug in argv]
    else:
        files = sorted(CHURCHES_DIR.glob("*.json"))
    if not files:
        print("No church records found.")
        return 1
    failures = 0
    seen_slugs: set[str] = set()
    for path in files:
        if not path.exists():
            print(f"FAIL {path.relative_to(ROOT)}: file does not exist")
            failures += 1
            continue
        problems = validate_file(validator, path)
        if path.stem in seen_slugs:
            problems.append("duplicate slug")
        seen_slugs.add(path.stem)
        if problems:
            failures += 1
            print(f"FAIL {path.relative_to(ROOT)}")
            for problem in problems:
                print(f"     - {problem}")
        else:
            print(f"ok   {path.relative_to(ROOT)}")
    print(f"\n{len(files) - failures} passed, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
