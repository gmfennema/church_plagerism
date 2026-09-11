#!/usr/bin/env python3
"""Compute AI-writing *signals* for sermon transcripts. Signals, not verdicts.

    python3 tools/ai_writing_signals.py --church fbc-tucson
    python3 tools/ai_writing_signals.py --church fbc-tucson --baseline research/fbc-tucson/baseline_transcripts

Why this is hard: sermons are delivered orally, transcripts come from speech recognition without punctuation,
and preachers have always used manuscripts. No single number proves a sermon was written by an LLM. What CAN be
measured, and compared against the same preacher's older sermons (a baseline, ideally pre-2023):

  1. ai_phrase_rate      occurrences per 1,000 words of vocabulary that LLM prose over-uses (delve, tapestry,
                          "it's important to note", "in today's fast-paced world", navigate, foster, testament to ...)
  2. disfluency_rate     um/uh/false starts/immediate word repeats per 1,000 words. Extemporaneous preaching has
                          many; reading a generated manuscript verbatim has few. (Auto-captions drop some fillers,
                          so compare like with like.)
  3. connective_rate     "furthermore / moreover / additionally / ultimately / in conclusion" per 1,000 words -
                          essay connectives that are rare in speech.
  4. list_scaffold_rate  "first(ly) ... second(ly) ... third(ly)", "number one", "point number" per 1,000 words.
  5. mattr               moving-average type-token ratio (window 500). LLM text tends to be lexically even.
  6. personal_rate       first-person anecdote markers ("my wife", "when I was", "years ago", "I remember") per
                          1,000 words. Generated sermons are often light on specific personal narrative.

Each metric is reported per sermon and as a corpus mean. When a baseline directory is supplied, z-scores against
the baseline are computed and a shift is called out when |z| >= 2 on at least two independent signals.

Output: research/<slug>/reports/ai_writing_signals.json and .md. Then apply the AGENTS.md rubric:
'flagged' for AI requires converging evidence (strong multi-signal shift vs baseline AND corroboration such as
published manuscripts that trip several signals, identical structure across sermons, or an admission).
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WORD_RE = re.compile(r"[a-z]+(?:['’-][a-z]+)*")
TIMESTAMP_RE = re.compile(r"\[\d{2}:\d{2}:\d{2}\.\d{3}\]")

AI_PHRASES = [
    "delve", "delves", "delving", "tapestry", "it's important to note", "it is important to note", "in today's fast-paced world",
    "in today's world", "in a world where", "navigate", "navigating", "foster", "fostering", "testament to", "serves as a reminder",
    "profound", "pivotal", "crucial", "vibrant", "beacon", "realm", "underscore", "underscores", "multifaceted", "nuanced", "intricate",
    "embark", "journey of", "unwavering", "steadfast commitment", "let's unpack", "let's dive in", "dive into", "landscape", "resonate", "resonates",
    "empower", "empowers", "transformative", "embrace", "embracing", "at its core", "in essence", "not only", "but also", "whether you're",
    "picture this", "imagine a world", "here's the thing", "the key takeaway", "in summary", "to sum up", "let that sink in", "unpack",
    "cultivate", "cultivating", "meaningful connections", "authentic", "intentional", "shed light", "highlight", "highlights", "game-changer",
    "leverage", "holistic", "elevate", "thrive", "ever-evolving", "seamless", "a testament",
]
CONNECTIVES = ["furthermore", "moreover", "additionally", "ultimately", "in conclusion", "consequently", "thus", "hence", "in addition", "therefore"]
LIST_SCAFFOLD = ["firstly", "secondly", "thirdly", "first of all", "second of all", "number one", "number two", "number three", "point number", "the first point", "the second point", "the third point", "the first thing", "the second thing", "the third thing"]
DISFLUENCIES = ["um", "uh", "uhm", "hmm", "er", "you know", "i mean", "sort of", "kind of"]
PERSONAL = ["my wife", "my husband", "my kids", "my son", "my daughter", "when i was", "years ago", "i remember", "i grew up", "my dad", "my mom", "my father", "my mother", "the other day", "last week", "this week", "a friend of mine", "true story"]


def words_from_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"^\s*#.*$", " ", text, flags=re.MULTILINE)
    text = TIMESTAMP_RE.sub(" ", text.lower()).replace("’", "'")
    text = text.replace("[music]", " ").replace("[applause]", " ")
    return WORD_RE.findall(text)


def phrase_count(joined: str, phrases: list[str]) -> int:
    return sum(len(re.findall(rf"\b{re.escape(p)}\b", joined)) for p in phrases)


def mattr(words: list[str], window: int = 500) -> float:
    if len(words) <= window:
        return round(len(set(words)) / len(words), 4) if words else 0.0
    ratios = []
    counts: dict[str, int] = {}
    for w in words[:window]:
        counts[w] = counts.get(w, 0) + 1
    ratios.append(len(counts) / window)
    for i in range(window, len(words)):
        out, inc = words[i - window], words[i]
        counts[out] -= 1
        if counts[out] == 0:
            del counts[out]
        counts[inc] = counts.get(inc, 0) + 1
        ratios.append(len(counts) / window)
    return round(sum(ratios) / len(ratios), 4)


def immediate_repeats(words: list[str]) -> int:
    return sum(1 for a, b in zip(words, words[1:]) if a == b and len(a) > 1)


def analyse(path: Path) -> dict[str, Any]:
    words = words_from_file(path)
    n = max(len(words), 1)
    joined = " ".join(words)
    per_k = lambda count: round(1000 * count / n, 2)  # noqa: E731
    title = path.stem
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[:3]:
        if line.startswith("# ") and not line[2:].startswith("http"):
            title = line[2:].strip()
            break
    return {
        "file": path.name,
        "title": title,
        "word_count": len(words),
        "ai_phrase_rate": per_k(phrase_count(joined, AI_PHRASES)),
        "disfluency_rate": per_k(phrase_count(joined, DISFLUENCIES) + immediate_repeats(words)),
        "connective_rate": per_k(phrase_count(joined, CONNECTIVES)),
        "list_scaffold_rate": per_k(phrase_count(joined, LIST_SCAFFOLD)),
        "personal_rate": per_k(phrase_count(joined, PERSONAL)),
        "mattr": mattr(words),
    }


METRICS = ["ai_phrase_rate", "disfluency_rate", "connective_rate", "list_scaffold_rate", "personal_rate", "mattr"]
# direction in which a shift points toward generated text
DIRECTION = {"ai_phrase_rate": +1, "disfluency_rate": -1, "connective_rate": +1, "list_scaffold_rate": +1, "personal_rate": -1, "mattr": +1}


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for m in METRICS:
        values = [r[m] for r in rows]
        out[m] = {"mean": round(statistics.fmean(values), 3), "stdev": round(statistics.pstdev(values), 3) if len(values) > 1 else 0.0, "min": min(values), "max": max(values)}
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--church", required=True)
    parser.add_argument("--transcripts", type=Path, help="override research/<slug>/transcripts")
    parser.add_argument("--baseline", type=Path, help="directory of the same preacher's older transcripts for comparison")
    parser.add_argument("--pastor")
    args = parser.parse_args()

    research = ROOT / "research" / args.church
    transcripts_dir = args.transcripts or research / "transcripts"
    files = sorted(transcripts_dir.glob("*.txt"))
    if not files:
        raise SystemExit(f"No transcripts in {transcripts_dir}")
    rows = [analyse(p) for p in files]
    result: dict[str, Any] = {
        "church_slug": args.church,
        "pastor": args.pastor,
        "generated_at": date.today().isoformat(),
        "sermon_count": len(rows),
        "sermons": rows,
        "corpus": summarise(rows),
        "baseline": None,
        "shift_signals": [],
        "suggested_outcome": "inconclusive - signals only; no baseline supplied" if not args.baseline else None,
    }
    if args.baseline:
        base_files = sorted(args.baseline.glob("*.txt"))
        if not base_files:
            raise SystemExit(f"No baseline transcripts in {args.baseline}")
        base_rows = [analyse(p) for p in base_files]
        base = summarise(base_rows)
        result["baseline"] = {"dir": str(args.baseline.relative_to(ROOT)) if args.baseline.is_relative_to(ROOT) else str(args.baseline), "sermon_count": len(base_rows), "corpus": base}
        for m in METRICS:
            sd = base[m]["stdev"] or 1e-9
            z = (result["corpus"][m]["mean"] - base[m]["mean"]) / sd
            toward_ai = z * DIRECTION[m] >= 2
            result["shift_signals"].append({"metric": m, "recent_mean": result["corpus"][m]["mean"], "baseline_mean": base[m]["mean"], "z": round(z, 2), "points_toward_generated": toward_ai})
        strong = [s for s in result["shift_signals"] if s["points_toward_generated"]]
        result["suggested_outcome"] = (
            f"{len(strong)} signal(s) shifted toward generated text vs baseline ({', '.join(s['metric'] for s in strong)}) - corroborate before flagging"
            if len(strong) >= 2 else "no convergent shift vs baseline - lean 'cleared' if the baseline is sound, otherwise 'inconclusive'"
        )

    reports = research / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "ai_writing_signals.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (reports / "ai_writing_signals.md").write_text(markdown(result), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in {"sermons"}}, indent=2))
    print(f"\nWritten to {reports.relative_to(ROOT)}/ai_writing_signals.{{json,md}}")


def markdown(r: dict[str, Any]) -> str:
    lines = [
        f"# AI-writing signals: {r['church_slug']}" + (f" / {r['pastor']}" if r.get("pastor") else ""),
        "",
        f"**Prepared:** {r['generated_at']}  ",
        f"**Sermons analysed:** {r['sermon_count']}  ",
        f"**Suggested outcome:** {r['suggested_outcome']}",
        "",
        "> These are stylometric signals computed from speech-recognition transcripts. None of them proves that a sermon was generated by an AI system. A flag requires converging evidence as described in AGENTS.md.",
        "",
        "## Corpus averages (per 1,000 words unless noted)",
        "",
        "| Metric | Mean | Std dev | Min | Max |" + (" Baseline mean | z |" if r.get("baseline") else ""),
        "|---|---:|---:|---:|---:|" + ("---:|---:|" if r.get("baseline") else ""),
    ]
    shifts = {s["metric"]: s for s in r.get("shift_signals", [])}
    for m, v in r["corpus"].items():
        row = f"| {m} | {v['mean']} | {v['stdev']} | {v['min']} | {v['max']} |"
        if r.get("baseline"):
            s = shifts[m]
            row += f" {s['baseline_mean']} | {s['z']}{' *' if s['points_toward_generated'] else ''} |"
        lines.append(row)
    if r.get("baseline"):
        lines += ["", f"Baseline: {r['baseline']['sermon_count']} sermon(s) from `{r['baseline']['dir']}`. `*` marks a shift of at least two standard deviations toward generated-text characteristics."]
    lines += ["", "## Per sermon", "", "| Sermon | Words | AI phrases | Disfluencies | Connectives | List scaffolds | Personal | MATTR |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for s in r["sermons"]:
        lines.append(f"| {s['title']} | {s['word_count']:,} | {s['ai_phrase_rate']} | {s['disfluency_rate']} | {s['connective_rate']} | {s['list_scaffold_rate']} | {s['personal_rate']} | {s['mattr']} |")
    lines += [
        "",
        "## How to read this",
        "",
        "- **AI phrases**: vocabulary over-represented in LLM prose. Some preachers use these words naturally; the baseline comparison matters more than the raw rate.",
        "- **Disfluencies**: um/uh/false starts. A sharp drop relative to the same preacher's earlier sermons suggests reading a manuscript verbatim, which is consistent with, but not proof of, generated text.",
        "- **Connectives / list scaffolds**: essay-style structure that speech rarely has.",
        "- **Personal**: specific first-person anecdote markers. Generated sermons tend to be generic.",
        "- **MATTR**: moving-average type-token ratio; generated text is often lexically even.",
        "",
        "Corroborating evidence to look for before flagging: published sermon manuscripts or notes that trip several signals, identical outline structure across many sermons, sermons whose illustrations do not fit the preacher's known biography, or a public statement by the preacher or church.",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
