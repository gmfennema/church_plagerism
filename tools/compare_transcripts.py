#!/usr/bin/env python3
"""Compare a church's sermon transcripts against a corpus of suspected source sermons.

    python3 tools/compare_transcripts.py --church fbc-tucson
    python3 tools/compare_transcripts.py --church fbc-tucson --pastor "Jane Doe" --min-run 8

Inputs (under research/<slug>/):
    transcripts/*.txt                         the church's sermons (from tools/fetch_transcripts.py or transcribe_audio.py)
    source_transcripts/<source-slug>/*.txt    suspected sources, one folder per series/author
    source_transcripts/<source-slug>/meta.json  optional: {"author": "...", "title": "...", "url": "...", "titles": {"file-stem": "Nice Title"}}

Outputs (under research/<slug>/reports/):
    plagiarism_analysis.json   every exact run for every sermon/source pair
    plagiarism_report.md       readable report
    plagiarism_report.pdf      formatted report (needs reportlab)

Method: normalise both texts to lowercase words, index every n-gram of --min-run words in each source,
find matching runs in each sermon and extend them as far as they stay identical. Coverage is the union of
matched sermon words, so overlapping runs are not double counted. Verbatim overlap is evidence, not a
verdict: Scripture, hymns, creeds and prayers are shared language. The report prints the longest runs so a
human can classify them. Use --exclude-file to supply text (e.g. Bible passages) whose n-grams are ignored.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import date
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WORD_RE = re.compile(r"[a-z]+(?:['’-][a-z]+)*")
TIMESTAMP_RE = re.compile(r"\[\d{2}:\d{2}:\d{2}\.\d{3}\]")

# Rubric thresholds (see AGENTS.md). Informational: the tool suggests, the reviewer decides.
FLAG_COVERAGE_PCT = 2.0      # a sermon whose non-trivial overlap covers >= 2% of its words
FLAG_LONG_RUN = 20           # or contains a run of >= 20 words that is not Scripture
FLAG_MIN_SERMONS = 2         # in at least this many sermons


def words_from_text(text: str) -> list[str]:
    text = re.sub(r"^\s*#.*$", " ", text, flags=re.MULTILINE)
    text = TIMESTAMP_RE.sub(" ", text.lower())
    text = text.replace("[music]", " ").replace("[applause]", " ").replace(">>", " ").replace("’", "'")
    return WORD_RE.findall(text)


def words_from_file(path: Path) -> list[str]:
    return words_from_text(path.read_text(encoding="utf-8", errors="replace"))


def read_header(path: Path) -> dict[str, str]:
    """Pull '# key: value' style header lines and the first '# Title' line."""
    info: dict[str, str] = {}
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.startswith("#"):
                break
            body = line.lstrip("#").strip()
            if not body:
                continue
            if "title" not in info and ":" not in body and not body.startswith("http"):
                info["title"] = body
            elif body.startswith("http"):
                info.setdefault("url", body)
            elif ":" in body:
                key, _, value = body.partition(":")
                info[key.strip().lower().replace(" ", "_")] = value.strip()
    return info


def pretty_stem(stem: str) -> str:
    stem = re.sub(r"_[A-Za-z0-9_-]{11}$", "", stem)  # strip YouTube id
    stem = re.sub(r"^\d+-", "", stem)
    return re.sub(r"[_-]+", " ", stem).strip().title()


def sermon_meta(path: Path) -> dict[str, Any]:
    meta = read_header(path)
    sibling = path.with_suffix(".json")
    if sibling.exists():
        try:
            data = json.loads(sibling.read_text(encoding="utf-8"))
            meta.setdefault("title", data.get("title"))
            meta.setdefault("url", data.get("url"))
            if data.get("upload_date"):
                meta.setdefault("upload_date", data["upload_date"])
        except json.JSONDecodeError:
            pass
    title = meta.get("title") or pretty_stem(path.stem)
    date_match = re.search(r"(\d{2})(\d{2})(\d{2})\b", path.stem) or re.search(r"(\d{1,2})-(\d{1,2})-(\d{4})", path.stem)
    return {"file": path.name, "title": title, "url": meta.get("url"), "upload_date": meta.get("upload_date"), "date_hint": date_match.group(0) if date_match else None}


def load_sources(source_dir: Path) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    folders = sorted(p for p in source_dir.iterdir() if p.is_dir()) if source_dir.exists() else []
    for folder in folders:
        meta: dict[str, Any] = {}
        meta_path = folder / "meta.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        titles = meta.get("titles", {})
        for path in sorted(folder.glob("*.txt")):
            header = read_header(path)
            sources.append({
                "path": path,
                "collection": folder.name,
                "author": meta.get("author") or header.get("author") or "Unknown author",
                "series": meta.get("title") or folder.name.replace("-", " ").title(),
                "series_url": meta.get("url"),
                "title": titles.get(path.stem) or header.get("title") or pretty_stem(path.stem),
                "words": words_from_file(path),
            })
    return sources


def build_index(words: list[str], n: int) -> dict[tuple[str, ...], list[int]]:
    index: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for pos in range(len(words) - n + 1):
        index[tuple(words[pos:pos + n])].append(pos)
    return index


def exact_runs(local: list[str], source: list[str], index: dict[tuple[str, ...], list[int]], n: int, excluded: set[tuple[str, ...]]) -> list[dict[str, Any]]:
    runs: list[tuple[int, int, int]] = []
    pos = 0
    seen_end: dict[int, int] = {}
    for left in range(len(local) - n + 1):
        gram = tuple(local[left:left + n])
        if gram in excluded:
            continue
        for right in index.get(gram, []):
            # skip if this (left,right) pair lies inside an already-recorded run on the same diagonal
            if seen_end.get(right - left, -1) >= left:
                continue
            length = n
            while left + length < len(local) and right + length < len(source) and local[left + length] == source[right + length]:
                length += 1
            runs.append((left, right, length))
            seen_end[right - left] = left + length - 1
    return [
        {"local_start": li, "source_start": ri, "length": length, "phrase": " ".join(local[li:li + length])}
        for li, ri, length in sorted(runs, key=lambda r: -r[2])
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--church", required=True, help="church slug")
    parser.add_argument("--pastor", help="pastor name, printed in the report")
    parser.add_argument("--min-run", type=int, default=8, help="minimum consecutive words to count (default 8)")
    parser.add_argument("--transcripts", type=Path, help="override sermon transcript directory")
    parser.add_argument("--sources", type=Path, help="override source transcript directory")
    parser.add_argument("--exclude-file", type=Path, action="append", default=[], help="text whose n-grams are ignored (e.g. Bible passages quoted in the series)")
    parser.add_argument("--top", type=int, default=15, help="number of longest passages to print")
    parser.add_argument("--no-pdf", action="store_true")
    args = parser.parse_args()

    research = ROOT / "research" / args.church
    transcripts_dir = args.transcripts or research / "transcripts"
    source_dir = args.sources or research / "source_transcripts"
    reports_dir = research / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    church_name = args.church
    church_path = ROOT / "data" / "churches" / f"{args.church}.json"
    if church_path.exists():
        church_name = json.loads(church_path.read_text(encoding="utf-8")).get("name", args.church)

    sermon_files = sorted(transcripts_dir.glob("*.txt"))
    sources = load_sources(source_dir)
    if not sermon_files:
        raise SystemExit(f"No sermon transcripts in {transcripts_dir}. Run tools/fetch_transcripts.py first.")
    if not sources:
        raise SystemExit(f"No source transcripts in {source_dir}/<source-slug>/*.txt. See AGENTS.md step 4.")

    excluded: set[tuple[str, ...]] = set()
    for path in args.exclude_file:
        w = words_from_file(path)
        excluded.update(tuple(w[i:i + args.min_run]) for i in range(len(w) - args.min_run + 1))

    for src in sources:
        src["index"] = build_index(src["words"], args.min_run)

    sermons: list[dict[str, Any]] = []
    all_runs: list[dict[str, Any]] = []
    total_words = 0
    total_covered = 0
    for path in sermon_files:
        words = words_from_file(path)
        meta = sermon_meta(path)
        covered: set[int] = set()
        per_source: list[dict[str, Any]] = []
        for src in sources:
            runs = exact_runs(words, src["words"], src["index"], args.min_run, excluded)
            src_covered: set[int] = set()
            for run in runs:
                src_covered.update(range(run["local_start"], run["local_start"] + run["length"]))
                all_runs.append({**run, "sermon_title": meta["title"], "sermon_file": meta["file"], "source_author": src["author"], "source_title": src["title"], "source_series": src["series"], "source_file": src["path"].name})
            covered |= src_covered
            per_source.append({
                "source_author": src["author"],
                "source_series": src["series"],
                "source_title": src["title"],
                "source_file": src["path"].name,
                "source_word_count": len(src["words"]),
                "exact_run_count": len(runs),
                "matched_words": len(src_covered),
                "matched_pct": round(100 * len(src_covered) / len(words), 2) if words else 0.0,
                "longest_exact_run": max((r["length"] for r in runs), default=0),
                "runs": runs,
            })
        per_source.sort(key=lambda s: (s["matched_words"], s["longest_exact_run"]), reverse=True)
        best = per_source[0]
        total_words += len(words)
        total_covered += len(covered)
        sermons.append({
            **meta,
            "word_count": len(words),
            "matched_words_any_source": len(covered),
            "matched_pct_any_source": round(100 * len(covered) / len(words), 2) if words else 0.0,
            "best_source": {k: v for k, v in best.items() if k != "runs"},
            "exceeds_rubric": best["matched_pct"] >= FLAG_COVERAGE_PCT or best["longest_exact_run"] >= FLAG_LONG_RUN,
            "sources": per_source,
        })

    all_runs.sort(key=lambda r: r["length"], reverse=True)
    top = all_runs[: args.top]
    sermons_with_matches = sum(s["matched_words_any_source"] > 0 for s in sermons)
    sermons_exceeding = sum(s["exceeds_rubric"] for s in sermons)
    summary = {
        "church": church_name,
        "church_slug": args.church,
        "pastor": args.pastor,
        "generated_at": date.today().isoformat(),
        "min_run_words": args.min_run,
        "sermon_count": len(sermons),
        "source_count": len(sources),
        "source_authors": sorted({s["author"] for s in sources}),
        "source_series": sorted({s["series"] for s in sources}),
        "total_sermon_words": total_words,
        "covered_words": total_covered,
        "covered_pct": round(100 * total_covered / total_words, 2) if total_words else 0.0,
        "sermons_with_matches": sermons_with_matches,
        "sermons_exceeding_rubric": sermons_exceeding,
        "longest_run": top[0]["length"] if top else 0,
        "rubric": {"coverage_pct": FLAG_COVERAGE_PCT, "long_run_words": FLAG_LONG_RUN, "min_sermons": FLAG_MIN_SERMONS},
        "suggested_outcome": (
            "meets flag threshold - review the longest passages for Scripture/attribution before flagging"
            if sermons_exceeding >= FLAG_MIN_SERMONS
            else "below flag threshold - consider 'cleared' if enough sermons and likely sources were covered, else 'inconclusive'"
        ),
    }
    data = {"summary": summary, "sermons": sermons, "top_passages": top}
    (reports_dir / "plagiarism_analysis.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (reports_dir / "plagiarism_report.md").write_text(markdown_report(data), encoding="utf-8")
    if not args.no_pdf:
        try:
            build_pdf(data, reports_dir / "plagiarism_report.pdf")
        except ImportError:
            print("reportlab not installed; skipped PDF (pip install reportlab)")
    print(json.dumps(summary, indent=2))
    print(f"\nReports written to {reports_dir.relative_to(ROOT)}/")


def markdown_report(data: dict[str, Any]) -> str:
    s = data["summary"]
    who = f"{s['church']}" + (f" / {s['pastor']}" if s.get("pastor") else "")
    lines = [
        f"# Sermon Text Similarity Review: {who}",
        "",
        f"**Prepared:** {s['generated_at']}  ",
        f"**Compared against:** {', '.join(s['source_authors'])} - {', '.join(s['source_series'])}  ",
        "**Purpose:** Evidence review of verbatim textual overlap. Not a legal or ecclesiastical verdict.",
        "",
        "## Summary",
        "",
        f"{s['sermon_count']} sermon transcript(s) were compared with {s['source_count']} source transcript(s). "
        f"Counting only exact runs of at least {s['min_run_words']} consecutive normalised words, "
        f"**{s['sermons_with_matches']} of {s['sermon_count']} sermons contain at least one match**, and "
        f"**{s['covered_words']:,} of {s['total_sermon_words']:,} sermon words ({s['covered_pct']}%)** fall inside a matched run.",
        "",
        f"{s['sermons_exceeding_rubric']} sermon(s) exceed the project rubric (>= {s['rubric']['coverage_pct']}% coverage or a run of >= {s['rubric']['long_run_words']} words against a single source). "
        f"Suggested outcome: *{s['suggested_outcome']}*.",
        "",
        "> Verbatim overlap is an indicator, not a finding. Scripture, hymns, creeds and prayers are shared language, and both transcripts may contain speech-recognition errors. Read the longest passages in context before drawing conclusions.",
        "",
        "## Results by sermon",
        "",
        "| Sermon | Words | Best-matching source | Runs | Longest run | Matched words | Coverage | Rubric |",
        "|---|---:|---|---:|---:|---:|---:|:-:|",
    ]
    for item in data["sermons"]:
        b = item["best_source"]
        lines.append(
            f"| {item['title']} | {item['word_count']:,} | {b['source_title']} ({b['source_author']}) | {b['exact_run_count']} | {b['longest_exact_run']} | {b['matched_words']:,} | {b['matched_pct']:.2f}% | {'exceeds' if item['exceeds_rubric'] else '-'} |"
        )
    lines += ["", "## Longest matching passages", "", "Machine-normalised excerpts, longest first. Classify each as Scripture / liturgy / source commentary before citing it as evidence.", ""]
    for i, run in enumerate(data["top_passages"], start=1):
        lines += [
            f"### {i}. {run['length']} consecutive words",
            f"- **Sermon:** {run['sermon_title']}",
            f"- **Source:** {run['source_title']} - {run['source_author']} ({run['source_series']})",
            f"- **Text:** \"{run['phrase']}\"",
            "",
        ]
    lines += [
        "## Method",
        "",
        "1. Normalise case, strip timestamps, caption headers and noise markers, and tokenise to words.",
        f"2. Index every {s['min_run_words']}-word sequence in each source transcript.",
        "3. For each sermon, find every source sequence that also occurs in the sermon and extend the match while the words stay identical.",
        "4. Report coverage as the union of matched sermon positions so overlapping runs are not double-counted.",
        "",
        "## Interpretation guardrails",
        "",
        "- Verbatim overlap is not the same as plagiarism. Check for spoken or printed attribution, licensed curricula and shared source material.",
        "- Auto-captions and Whisper both make errors, which mostly suppress matches; treat the figures as conservative.",
        "- Long runs that are Scripture quotations should be set aside. Runs of the source's own commentary, illustrations and transitions are the material evidence.",
        "",
        "Machine-readable results: `plagiarism_analysis.json` in the same folder. Reproduce with `tools/compare_transcripts.py`.",
    ]
    return "\n".join(lines) + "\n"


def _pdf_safe(text: str) -> str:
    for old, new in {"—": "-", "–": "-", "’": "'", "“": '"', "”": '"', "…": "..."}.items():
        text = text.replace(old, new)
    return escape(text.encode("latin-1", errors="replace").decode("latin-1"))


def build_pdf(data: dict[str, Any], output: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    s = data["summary"]
    navy, gray, light = colors.HexColor("#15324B"), colors.HexColor("#56616B"), colors.HexColor("#EAF2F7")
    ss = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle("t", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=navy, alignment=0, spaceAfter=6),
        "sub": ParagraphStyle("s", parent=ss["Normal"], fontSize=10.5, leading=14, textColor=gray, spaceAfter=14),
        "h": ParagraphStyle("h", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=navy, spaceBefore=12, spaceAfter=6),
        "body": ParagraphStyle("b", parent=ss["BodyText"], fontSize=9, leading=12.5, spaceAfter=6),
        "callout": ParagraphStyle("c", parent=ss["BodyText"], fontName="Helvetica-Bold", fontSize=9.5, leading=13, textColor=navy, backColor=light, borderPadding=7, spaceBefore=6, spaceAfter=10),
        "tiny": ParagraphStyle("y", parent=ss["BodyText"], fontSize=7, leading=8.6, textColor=gray),
    }

    def p(text: str, style: str = "body") -> Paragraph:
        return Paragraph(_pdf_safe(text), styles[style])

    who = s["church"] + (f" / {s['pastor']}" if s.get("pastor") else "")
    story: list[Any] = [
        p("Sermon Text Similarity Review", "title"),
        p(f"{who} compared with {', '.join(s['source_authors'])}: {', '.join(s['source_series'])}", "sub"),
        p(f"Prepared {s['generated_at']} | Evidence review, not a legal or ecclesiastical verdict", "tiny"),
        Spacer(1, 10),
        p("Summary", "h"),
        p(
            f"{s['sermons_with_matches']} of {s['sermon_count']} sermon transcripts contain at least one exact run of {s['min_run_words']}+ consecutive words found in the source corpus. "
            f"Matched words total {s['covered_words']:,} of {s['total_sermon_words']:,} ({s['covered_pct']}%). "
            f"{s['sermons_exceeding_rubric']} sermon(s) exceed the project rubric. Suggested outcome: {s['suggested_outcome']}.",
            "callout",
        ),
        p("Verbatim overlap is an indicator, not a finding. Scripture, hymns, creeds and prayers are shared language, and both transcripts may contain speech-recognition errors. The longest passages are listed so a reader can classify them in context.", "body"),
        p("Results by sermon", "h"),
    ]
    rows = [[p(h, "tiny") for h in ["Sermon", "Words", "Best-matching source", "Runs", "Longest", "Matched", "Coverage"]]]
    for item in data["sermons"]:
        b = item["best_source"]
        rows.append([p(item["title"], "tiny"), p(f"{item['word_count']:,}", "tiny"), p(f"{b['source_title']} ({b['source_author']})", "tiny"), p(str(b["exact_run_count"]), "tiny"), p(str(b["longest_exact_run"]), "tiny"), p(f"{b['matched_words']:,}", "tiny"), p(f"{b['matched_pct']:.2f}%", "tiny")])
    table = Table(rows, colWidths=[1.6 * inch, 0.5 * inch, 2.1 * inch, 0.45 * inch, 0.55 * inch, 0.6 * inch, 0.65 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), navy), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#C9D2D9")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FA")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story += [table, PageBreak(), p("Longest matching passages", "h"), p("Machine-normalised excerpts, longest first. Classify each as Scripture, liturgy or source commentary before citing it.", "body")]
    for i, run in enumerate(data["top_passages"], start=1):
        story.append(p(f"{i}. {run['length']} consecutive words - Sermon: {run['sermon_title']} | Source: {run['source_title']} ({run['source_author']}, {run['source_series']})", "body"))
        story.append(p(f'"{run["phrase"]}"', "callout"))
    story += [p("Method and guardrails", "h")]
    for bullet in [
        f"Normalise text, index every {s['min_run_words']}-word sequence in each source, extend matches while words stay identical, union matched positions.",
        "Overlap is not plagiarism: check spoken or printed attribution, licensing and shared source material.",
        "Speech-recognition errors suppress matches; figures are conservative.",
        "Set aside Scripture quotations; the source's own commentary, illustrations and transitions are the material evidence.",
    ]:
        story.append(p("- " + bullet, "body"))

    def footer(canvas: Any, _doc: Any) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(gray)
        canvas.drawString(0.55 * inch, 0.32 * inch, "Tucson sermon integrity project | working analysis; see repository for data and code")
        canvas.drawRightString(7.95 * inch, 0.32 * inch, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    SimpleDocTemplate(str(output), pagesize=letter, rightMargin=0.55 * inch, leftMargin=0.55 * inch, topMargin=0.55 * inch, bottomMargin=0.55 * inch, title="Sermon Text Similarity Review").build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    main()
