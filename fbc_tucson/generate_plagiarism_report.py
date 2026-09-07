#!/usr/bin/env python3
"""Compare the FBC Tucson transcripts with the downloaded Begg source corpus."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import date
from html import escape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
LOCAL_DIR = ROOT / "transcripts"
SOURCE_DIR = ROOT / "source_transcripts"
OUTPUT_JSON = ROOT / "plagiarism_analysis.json"
OUTPUT_MD = ROOT / "plagiarism_report.md"
OUTPUT_PDF = ROOT / "plagiarism_report.pdf"

WORD_RE = re.compile(r"[a-z]+(?:['-][a-z]+)*")
TIMESTAMP_RE = re.compile(r"\[\d{2}:\d{2}:\d{2}\.\d{3}\]")

SOURCE_TITLE_OVERRIDES = {
    "01-faithhopelove": "Faith, Hope and Love",
    "04-noclevertricks": "No Clever Tricks",
    "05-truthandlove": "Truth and Love",
    "06-thewordofgodnotmen": "God's Word... Not Man's",
    "07-ourgloryandjoy": "Our Glory and Joy",
    "01-pleasinggod": "Pleasing God",
    "02-sexualpuritypartone": "Sexual Purity, Part 1",
    "03-sexualpurityparttwo": "Sexual Purity, Part 2",
    "06-thosewhohavehope": "Those Who Have Hope",
    "07-thecomingofthelordpartone": "The Coming of the Lord, Part 1",
    "08-thecomingofthelordparttwo": "The Coming of the Lord, Part 2",
    "09-thecomingofthelordpartthree": "The Coming of the Lord, Part 3",
    "01-learningtorespectourleadership": "Learning to Respect Our Leadership",
    "02-learningtoliveinpeace": "Learning to Live in Peace",
    "03-practicingpatience": "Practicing Patience",
    "04-cultivatingkindness": "Cultivating Kindness",
    "05-learninghowtoworshipanintroduction": "Learning How to Worship",
    "06-givethanks": "Give Thanks",
    "07-donotgrievetheholyspirit": "Do Not Grieve the Holy Spirit",
    "08-listeningtothewordofgod": "Listening to the Word of God",
    "09-sanctification": "Sanctification",
    "10-thefaithfulnessofgod": "The Faithfulness of God",
}

LOCAL_TITLE_OVERRIDES = {
    "Big_Mess_8-1-2026_rI2h_cc-Kj4": "Big Mess (Aug. 1, 2026)",
    "Faith_Hope_and_Love_-_041926_pgy_YF3x3gE": "Faith, Hope and Love (Apr. 19, 2026)",
    "God_s_Word...Not_Man_s_-_052426_UA--g_npTNA": "God's Word... Not Man's (May 24, 2026)",
    "No_Clever_Tricks_-_051026_j9oaoRg6kZ8": "No Clever Tricks (May 10, 2026)",
    "Our_Glory_and_Joy_-_053126_U1kxopCXoNY": "Our Glory and Joy (May 31, 2026)",
    "Sexual_Purity_-_062826_B1H7S1-j6ag": "Sexual Purity (June 28, 2026)",
    "The_Faithfulness_of_God_-_072626_MXAy4hKNfwc": "The Faithfulness of God (July 26, 2026)",
    "The_Walk_of_Influence_-_071926_EuKaZ_afxRo": "The Walk of Influence (July 19, 2026)",
    "Your_True_Identity_-_071226_T-_Xdtb-Ync": "Your True Identity (July 12, 2026)",
}


def words_from_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"^\s*#.*$", " ", text, flags=re.MULTILINE)
    text = TIMESTAMP_RE.sub(" ", text.lower())
    text = text.replace("[music]", " ").replace(">>", " ")
    return WORD_RE.findall(text)


def display_name(path: Path) -> str:
    if path.stem in LOCAL_TITLE_OVERRIDES:
        return LOCAL_TITLE_OVERRIDES[path.stem]
    if path.stem in SOURCE_TITLE_OVERRIDES:
        return SOURCE_TITLE_OVERRIDES[path.stem]
    name = path.stem
    name = re.sub(r"_[A-Za-z0-9-]{8,}$", "", name)
    name = re.sub(r"^\d+-", "", name)
    return re.sub(r"[_-]+", " ", name).strip().title()


def volume_name(path: Path) -> str:
    match = re.fullmatch(r"volume(\d+)", path.name)
    return f"Volume {match.group(1)}" if match else path.name


def exact_runs(left: list[str], right: list[str], minimum: int = 8) -> list[dict[str, Any]]:
    """Find exact contiguous matches using an n-gram index, then extend each run."""
    index: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for pos in range(len(right) - minimum + 1):
        index[tuple(right[pos : pos + minimum])].append(pos)

    runs: list[tuple[int, int, int]] = []
    for left_pos in range(len(left) - minimum + 1):
        ngram = tuple(left[left_pos : left_pos + minimum])
        for right_pos in index.get(ngram, []):
            length = minimum
            while (
                left_pos + length < len(left)
                and right_pos + length < len(right)
                and left[left_pos + length] == right[right_pos + length]
            ):
                length += 1
            runs.append((left_pos, right_pos, length))

    # Keep maximal runs and discard runs contained by a longer run on the same pair.
    runs.sort(key=lambda item: item[2], reverse=True)
    kept: list[tuple[int, int, int]] = []
    for run in runs:
        li, ri, length = run
        if any(
            old_li <= li
            and old_ri <= ri
            and old_li + old_len >= li + length
            and old_ri + old_len >= ri + length
            for old_li, old_ri, old_len in kept
        ):
            continue
        kept.append(run)
    return [
        {
            "local_start": li,
            "source_start": ri,
            "length": length,
            "phrase": " ".join(left[li : li + length]),
        }
        for li, ri, length in kept
    ]


def compare(local_words: list[str], source_words: list[str]) -> dict[str, Any]:
    runs = exact_runs(local_words, source_words, minimum=8)
    covered: set[int] = set()
    for run in runs:
        covered.update(range(run["local_start"], run["local_start"] + run["length"]))
    shared = sum((Counter(local_words) & Counter(source_words)).values())
    return {
        "local_word_count": len(local_words),
        "source_word_count": len(source_words),
        "shared_word_count_multiset": shared,
        "exact_run_count": len(runs),
        "exact_run_words": len(covered),
        "exact_run_pct_local": round((len(covered) / len(local_words)) * 100, 2)
        if local_words
        else 0,
        "longest_exact_run": max((run["length"] for run in runs), default=0),
        "runs": runs,
    }


def safe_pdf(text: str) -> str:
    replacements = {
        "—": "-",
        "–": "-",
        "’": "'",
        "“": '"',
        "”": '"',
        "…": "...",
        "•": "-",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def markdown_report(data: dict[str, Any]) -> str:
    summary = data["summary"]
    lines = [
        "# Sermon Text Similarity Review",
        "## FBC Tucson / Alistair Begg 1 Thessalonians corpus",
        "",
        f"**Prepared:** {date.today().isoformat()}  ",
        "**Purpose:** Evidence review of textual overlap; not a legal or ecclesiastical verdict.",
        "",
        "## Executive synthesis",
        "",
        f"The review compared **{summary['local_sermon_count']} available FBC Tucson transcript(s)** against **{summary['source_sermon_count']} public Alistair Begg source sermon transcript(s)** from the Truth For Life three-volume 1 Thessalonians archive.",
        "",
        f"Using a conservative definition of verbatim overlap - a contiguous run of at least eight normalized words - **{summary['local_sermons_with_matches']} of {summary['local_sermon_count']} FBC transcripts contain at least one match** in the source corpus. Across the local corpus, **{summary['covered_local_words']} of {summary['local_words']} words ({summary['covered_local_pct']}%)** fall inside one or more such exact runs.",
        "",
        "> These figures are strong indicators of textual similarity, not by themselves a final finding of plagiarism. The source audio was transcribed locally with Whisper, while the FBC text came from YouTube auto-captions; quotation of Scripture, prayer language, and transcription errors can move the numbers in either direction.",
        "",
        "## Findings by FBC transcript",
        "",
        "| FBC sermon | Words | Best source match | Exact runs (8+ words) | Longest run | Matched words | Local coverage |",
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    for item in data["local_results"]:
        lines.append(
            f"| {item['local_title']} | {item['word_count']:,} | {item['best_source']} | {item['exact_run_count']} | {item['longest_exact_run']} | {item['matched_words']:,} | {item['matched_pct']:.2f}% |"
        )

    lines += ["", "## Illustrative longest matching passages", ""]
    lines += [
        "These are machine-normalized excerpts selected by contiguous word length. Several may be Scripture quotations or other shared religious language; they require contextual review and are not standalone plagiarism findings.",
        "",
    ]
    for index, match in enumerate(data["top_matches"], start=1):
        lines += [
            f"### {index}. {match['length']} consecutive words",
            f"- **FBC:** {match['local_title']}",
            f"- **Source:** {match['source_title']} ({match['source_volume']})",
            f"- **Phrase:** “{match['phrase']}”",
            "",
        ]

    lines += [
        "## Corpus and method",
        "",
        "### Local corpus",
        "- Playlist: https://youtube.com/playlist?list=PLEFrfWIivGoZxyyOR8G49a2HKwczrRut5",
        f"- Available transcripts analyzed: {summary['local_sermon_count']}",
        "- Missing/disabled transcripts were not invented or imputed.",
        "",
        "### Comparison corpus",
        "- Truth For Life, *A Study in 1 Thessalonians, Volume 1*: https://www.truthforlife.org/resources/series/study-in-1-thessalonians-volume-1/",
        "- Truth For Life, *A Study in 1 Thessalonians, Volume 2*: https://www.truthforlife.org/resources/series/study-in-1-thessalonians-volume-2/",
        "- Truth For Life, *A Study in 1 Thessalonians, Volume 3*: https://www.truthforlife.org/resources/series/study-in-1-thessalonians-volume-3/",
        "- Volume 3 is dated March 1, 2005 and is subtitled “Reminders for the Local Church.” The individual recordings are older Parkside sermons; the archive page is the source for the series date.",
        "",
        "### Calculation",
        "1. Normalize case, timestamps, caption headers, music markers, and punctuation.",
        "2. Compare each local transcript with every source transcript.",
        "3. Count exact contiguous matches of at least eight words. This threshold is intended to filter out ordinary shared words while retaining meaningful copied phrasing.",
        "4. Report local-word coverage using the union of all matched local positions, so repeated matches are not double-counted.",
        "",
        "## Interpretation guardrails",
        "",
        "- **Verbatim overlap is not identical to plagiarism.** Attribution, licensed adaptation, common source material, and Scripture quotations require separate judgment.",
        "- **The source transcript is ASR-derived.** Whisper errors generally reduce exact matches, so the reported match rate should be read as conservative rather than exact-to-the-audio.",
        "- **The local captions are also imperfect.** Some phrases may be missed because YouTube captions misheard them.",
        "- **A fair conclusion should inspect the longest passages in context**, including delivery structure, illustrations, transitions, and distinctive non-biblical phrasing.",
        "",
        "## Appendix",
        "",
        "The machine-readable results are in `plagiarism_analysis.json`. The reproducible analysis is in `generate_plagiarism_report.py`.",
    ]
    return "\n".join(lines) + "\n"


def build_pdf(data: dict[str, Any]) -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
        PageBreak,
    )

    navy = colors.HexColor("#15324B")
    blue = colors.HexColor("#2C6E9B")
    light_blue = colors.HexColor("#EAF2F7")
    gray = colors.HexColor("#56616B")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=25, leading=29, textColor=navy, alignment=TA_LEFT, spaceAfter=8))
    styles.add(ParagraphStyle(name="Subtitle", parent=styles["Normal"], fontName="Helvetica", fontSize=11, leading=15, textColor=gray, spaceAfter=18))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=navy, spaceBefore=14, spaceAfter=8))
    styles.add(ParagraphStyle(name="BodySmall", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.5, leading=12, textColor=colors.HexColor("#27333D"), spaceAfter=6))
    styles.add(ParagraphStyle(name="Callout", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=10, leading=14, textColor=navy, backColor=light_blue, borderColor=blue, borderWidth=0.5, borderPadding=8, spaceBefore=8, spaceAfter=10))
    styles.add(ParagraphStyle(name="Tiny", parent=styles["BodyText"], fontName="Helvetica", fontSize=6.7, leading=8.5, textColor=gray))

    def p(text: str, style: str = "BodySmall") -> Paragraph:
        return Paragraph(escape(safe_pdf(text)).replace("\n", "<br/>"), styles[style])

    doc = SimpleDocTemplate(str(OUTPUT_PDF), pagesize=letter, rightMargin=0.55 * inch, leftMargin=0.55 * inch, topMargin=0.55 * inch, bottomMargin=0.55 * inch, title="Sermon Text Similarity Review")
    story: list[Any] = [
        p("Sermon Text Similarity Review", "ReportTitle"),
        p("FBC Tucson / Alistair Begg 1 Thessalonians corpus", "Subtitle"),
        p(f"Prepared {date.today().isoformat()} | Evidence review, not a legal or ecclesiastical verdict", "Tiny"),
        Spacer(1, 12),
        p("Executive synthesis", "Section"),
        p(data["executive_pdf"] , "Callout"),
        p("Interpretation", "Section"),
        p("The overlap figures are indicators of textual similarity. They should not be treated as a final plagiarism finding without reviewing attribution, licensing, Scripture quotations, oral delivery, and the longest passages in context.", "BodySmall"),
        p("FBC transcript results", "Section"),
    ]

    table_data = [[p("FBC sermon", "Tiny"), p("Words", "Tiny"), p("Best source", "Tiny"), p("8+ word runs", "Tiny"), p("Longest", "Tiny"), p("Matched", "Tiny"), p("Coverage", "Tiny")]]
    for item in data["local_results"]:
        table_data.append([
            p(item["local_title"], "Tiny"),
            p(f"{item['word_count']:,}", "Tiny"),
            p(item["best_source"], "Tiny"),
            p(str(item["exact_run_count"]), "Tiny"),
            p(str(item["longest_exact_run"]), "Tiny"),
            p(f"{item['matched_words']:,}", "Tiny"),
            p(f"{item['matched_pct']:.2f}%", "Tiny"),
        ])
    table = Table(table_data, colWidths=[1.25 * inch, 0.48 * inch, 1.45 * inch, 0.62 * inch, 0.45 * inch, 0.52 * inch, 0.55 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), navy),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#C9D2D9")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FA")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    story.append(PageBreak())
    story.append(p("Illustrative longest matching passages", "Section"))
    story.append(p("These machine-normalized excerpts require contextual review; Scripture quotations and shared religious language are not standalone plagiarism findings.", "BodySmall"))
    for index, match in enumerate(data["top_matches"], start=1):
        story.append(p(f"{index}. {match['length']} consecutive words", "Section"))
        story.append(p(f"FBC: {match['local_title']} | Source: {match['source_title']} ({match['source_volume']})", "BodySmall"))
        story.append(p(f'“{match["phrase"]}”', "Callout"))
    story.append(p("Method and guardrails", "Section"))
    for bullet in [
        "Normalize case, timestamps, caption headers, music markers, and punctuation.",
        "Compare each local transcript with every source transcript.",
        "Count exact contiguous matches of at least eight words and union matched local positions to avoid double-counting.",
        "Source text is Whisper ASR; local text is YouTube auto-caption text. Both can contain errors.",
        "Volume 3 is dated March 1, 2005; its individual recordings are older Parkside sermons.",
    ]:
        story.append(p("- " + bullet, "BodySmall"))

    def footer(canvas: Any, _doc: Any) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(gray)
        canvas.drawString(0.55 * inch, 0.32 * inch, "Confidential working analysis | Source text and statistics documented in the project folder")
        canvas.drawRightString(7.95 * inch, 0.32 * inch, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def main() -> None:
    local_files = sorted(LOCAL_DIR.glob("*.txt"))
    source_files = sorted(SOURCE_DIR.glob("volume*/[0-9]*.txt"))
    local_words = {path: words_from_file(path) for path in local_files}
    source_words = {path: words_from_file(path) for path in source_files}

    comparisons: dict[str, dict[str, dict[str, Any]]] = {}
    local_results: list[dict[str, Any]] = []
    all_covered: set[tuple[Path, int]] = set()
    top_matches: list[dict[str, Any]] = []

    for local_path, words in local_words.items():
        comparisons[local_path.name] = {}
        best: dict[str, Any] | None = None
        for source_path, source in source_words.items():
            result = compare(words, source)
            comparisons[local_path.name][source_path.as_posix()] = result
            for run in result["runs"]:
                for position in range(run["local_start"], run["local_start"] + run["length"]):
                    all_covered.add((local_path, position))
                if run["length"] >= 10:
                    top_matches.append({
                        "local_title": display_name(local_path),
                        "source_title": display_name(source_path),
                        "source_volume": volume_name(source_path.parent),
                        **run,
                    })
            if best is None or (result["exact_run_words"], result["longest_exact_run"]) > (best["result"]["exact_run_words"], best["result"]["longest_exact_run"]):
                best = {"source": source_path, "result": result}

        assert best is not None
        local_results.append({
            "local_title": display_name(local_path),
            "word_count": len(words),
            "best_source": display_name(best["source"]),
            "exact_run_count": best["result"]["exact_run_count"],
            "longest_exact_run": best["result"]["longest_exact_run"],
            "matched_words": best["result"]["exact_run_words"],
            "matched_pct": best["result"]["exact_run_pct_local"],
        })

    top_matches.sort(key=lambda item: item["length"], reverse=True)
    top_matches = top_matches[:12]
    total_local_words = sum(len(words) for words in local_words.values())
    summary = {
        "local_sermon_count": len(local_files),
        "source_sermon_count": len(source_files),
        "local_words": total_local_words,
        "covered_local_words": len(all_covered),
        "covered_local_pct": round((len(all_covered) / total_local_words) * 100, 2) if total_local_words else 0,
        "local_sermons_with_matches": sum(item["matched_words"] > 0 for item in local_results),
    }
    data = {"generated_at": date.today().isoformat(), "summary": summary, "local_results": local_results, "top_matches": top_matches, "comparisons": comparisons}
    data["executive_pdf"] = (
        f"{summary['local_sermons_with_matches']} of {summary['local_sermon_count']} available FBC transcripts contain at least one contiguous exact match of 8+ normalized words. "
        f"The union of matched local words is {summary['covered_local_words']:,} of {summary['local_words']:,} words ({summary['covered_local_pct']:.2f}%). "
        "This is an evidence signal, not a final plagiarism verdict."
    )
    OUTPUT_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(markdown_report(data), encoding="utf-8")
    build_pdf(data)
    print(json.dumps({"summary": summary, "markdown": str(OUTPUT_MD), "pdf": str(OUTPUT_PDF)}, indent=2))


if __name__ == "__main__":
    main()
