"""Run the full FBC Tucson vs. Alistair Begg comparison and write results.

Outputs (in fbc_tucson/analysis/out/):
  results.json          all metrics used by the report
  alignments/<fbc>.txt  human-readable side-by-side reused regions per FBC sermon
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpus import load_all, fmt_time, Doc, _normalize_text  # noqa: E402
from matching import (exact_runs, coverage_from_runs, fuzzy_segments,  # noqa: E402
                      coverage_from_segments, matched_token_mask, ngram_index, Segment)

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
(OUT / "alignments").mkdir(parents=True, exist_ok=True)

PAIR_THRESHOLD = 0.04     # fuzzy coverage of FBC tokens needed to call a source "paired"
SCRIPTURE_CUES = re.compile(r"\b(verse|verses|chapter|v\.|reads|read|says|it says|scripture|bible|passage|text)\b")

# --------------------------------------------------------------------------- Bible
def load_bible() -> tuple[list[str], list[str]]:
    """Token stream + per-token reference for KJV and BBE (public domain)."""
    toks, refs = [], []
    for fn in ("en_kjv.json", "en_bbe.json"):
        data = json.load(open(HERE / "bible_ref" / fn, encoding="utf-8-sig"))
        tr = fn.split("_")[1].split(".")[0].upper()
        for book in data:
            for ci, chap in enumerate(book["chapters"], 1):
                for vi, verse in enumerate(chap, 1):
                    ref = f"{book['name']} {ci}:{vi} ({tr})"
                    for tok, _ in _normalize_text(verse):
                        toks.append(tok)
                        refs.append(ref)
    return toks, refs


class ScriptureFlagger:
    """Flags a token span as probable Scripture quotation.

    Signals (any two => 'likely', strongest alone => 'likely'):
      * fuzzy overlap with a public-domain translation (KJV/BBE) — the preachers
        read the NIV, so this is deliberately lenient (3-gram seeds, 35%+).
      * a quotation cue ('verse 6', 'chapter 2', 'it says') in the 12 words
        preceding the span in the FBC transcript.
      * the same span also appears near-verbatim in >= 2 *other* Begg sermons
        (Begg quotes the same text across the series).
    """

    def __init__(self):
        self.toks, self.refs = load_bible()
        self.idx = ngram_index(self.toks, 3)
        # drop hyper-common trigrams
        self.idx = {k: v for k, v in self.idx.items() if len(v) <= 40}

    def bible_overlap(self, span: list[str]) -> tuple[float, str]:
        if len(span) < 6:
            return 0.0, ""
        hits = defaultdict(int)
        for i in range(len(span) - 2):
            for j in self.idx.get(tuple(span[i:i + 3]), ()):
                hits[self.refs[j]] += 1
        if not hits:
            return 0.0, ""
        # aggregate by chapter to tolerate verse boundaries
        by_chapter = defaultdict(int)
        for ref, c in hits.items():
            by_chapter[ref.rsplit(":", 1)[0]] += c
        ref, c = max(by_chapter.items(), key=lambda kv: kv[1])
        return min(1.0, (c + 2) / max(1, len(span))), ref


# --------------------------------------------------------------------------- helpers
def pct(x, n):
    return round(100.0 * x / n, 2) if n else 0.0


def union(masks):
    out = [False] * len(masks[0])
    for m in masks:
        for i, v in enumerate(m):
            if v:
                out[i] = True
    return out


def sermon_window_heuristic(doc: Doc, segs: list[Segment]) -> tuple[int, int]:
    """Fallback sermon-body window in token indices (first to last reused region,
    padded by 600 tokens each side, clipped)."""
    if not segs:
        return 0, doc.n
    lo = min(s.a_start for s in segs)
    hi = max(s.a_end for s in segs)
    return max(0, lo - 600), min(doc.n, hi + 600)


def display_span(doc: Doc, lo: int, hi: int) -> str:
    return " ".join(doc.tokens[lo:hi])


# --------------------------------------------------------------------------- main
def main():
    fbc, src = load_all()
    flagger = ScriptureFlagger()
    results = {"fbc": [], "sources": [], "matrix": {}, "pairs": [], "baselines": {}}

    for d in src:
        results["sources"].append({"key": d.key, "title": d.title, "volume": d.meta["volume"], "tokens": d.n})

    # 1. full matrix ---------------------------------------------------------------
    matrix = {}
    segs_cache: dict[tuple[str, str], list[Segment]] = {}
    for a in fbc:
        for b in src:
            segs = fuzzy_segments(a.tokens, b.tokens)
            segs_cache[(a.key, b.key)] = segs
            runs = exact_runs(a.tokens, b.tokens, 8)
            cov_f = sum(coverage_from_segments(segs, a.n))
            cov_b = sum(coverage_from_segments(segs, b.n, "b"))
            cov_e = sum(coverage_from_runs(runs, a.n))
            matrix[(a.key, b.key)] = {
                "fuzzy_cov_fbc": cov_f, "fuzzy_cov_fbc_pct": pct(cov_f, a.n),
                "fuzzy_cov_src": cov_b, "fuzzy_cov_src_pct": pct(cov_b, b.n),
                "exact8_cov_fbc": cov_e, "exact8_cov_fbc_pct": pct(cov_e, a.n),
                "exact8_runs": len(runs), "longest_exact": max([r.length for r in runs], default=0),
                "segments": len(segs),
            }
    results["matrix"] = {f"{k[0]}||{k[1]}": v for k, v in matrix.items()}

    # 2. Begg-vs-Begg self-reuse baseline ----------------------------------------
    self_pairs = []
    for i, b1 in enumerate(src):
        for b2 in src[i + 1:]:
            segs = fuzzy_segments(b1.tokens, b2.tokens)
            c = sum(coverage_from_segments(segs, b1.n))
            self_pairs.append({"a": b1.key, "b": b2.key, "fuzzy_cov_pct": pct(c, b1.n)})
    results["baselines"]["begg_self_pairs"] = self_pairs

    # 3. per-FBC analysis -----------------------------------------------------------
    for a in fbc:
        row = {"key": a.key, "title": a.title, "date": a.meta["date"], "video_id": a.meta["video_id"],
               "url": a.meta["url"], "tokens": a.n,
               "duration_s": a.times[-1] if a.times else 0}
        ranked = sorted(src, key=lambda b: -matrix[(a.key, b.key)]["fuzzy_cov_fbc"])
        paired = [b for b in ranked if matrix[(a.key, b.key)]["fuzzy_cov_fbc_pct"] >= PAIR_THRESHOLD * 100]
        row["paired_sources"] = [b.key for b in paired]
        row["best_source"] = ranked[0].key
        row["source_ranking"] = [{"key": b.key, "fuzzy_cov_fbc_pct": matrix[(a.key, b.key)]["fuzzy_cov_fbc_pct"]} for b in ranked[:5]]

        # union coverage across paired sources
        all_segs: list[tuple[Segment, Doc]] = []
        for b in paired:
            all_segs += [(s, b) for s in segs_cache[(a.key, b.key)]]
        all_segs.sort(key=lambda sb: sb[0].a_start)

        if paired:
            fuzzy_mask = union([coverage_from_segments(segs_cache[(a.key, b.key)], a.n) for b in paired])
            exact_mask = union([coverage_from_runs(exact_runs(a.tokens, b.tokens, 8), a.n) for b in paired])
            exact5_mask = union([coverage_from_runs(exact_runs(a.tokens, b.tokens, 5), a.n) for b in paired])
            tok_mask = union([matched_token_mask(a.tokens, b.tokens, segs_cache[(a.key, b.key)]) for b in paired])
        else:
            fuzzy_mask = exact_mask = exact5_mask = tok_mask = [False] * a.n

        # non-paired noise floor for this sermon
        noise = [matrix[(a.key, b.key)]["fuzzy_cov_fbc_pct"] for b in src if b not in paired]
        row["noise_floor_pct"] = {"max": max(noise) if noise else 0, "mean": round(sum(noise) / len(noise), 2) if noise else 0}

        # segments with Scripture flag & display text
        seg_rows = []
        for s, b in all_segs:
            span = a.tokens[s.a_start:s.a_end]
            ov, ref = flagger.bible_overlap(span)
            lead = " ".join(a.tokens[max(0, s.a_start - 12):s.a_start])
            cue = bool(SCRIPTURE_CUES.search(lead))
            # recurrence across other Begg sermons
            recur = 0
            for other in src:
                if other.key == b.key:
                    continue
                if fuzzy_segments(span, other.tokens, min_len=min(12, len(span)), min_identity=0.6):
                    recur += 1
            score = (2 if ov >= 0.45 else 1 if ov >= 0.3 else 0) + (1 if cue else 0) + (1 if recur >= 2 else 0)
            if ov >= 0.6:
                score = max(score, 2)
            flag = "likely_scripture" if score >= 2 else "possible_scripture" if score == 1 else "non_scripture"
            seg_rows.append({
                "source": b.key, "fbc_start_tok": s.a_start, "fbc_end_tok": s.a_end,
                "fbc_time": fmt_time(a.times[s.a_start]), "fbc_time_end": fmt_time(a.times[min(s.a_end, a.n) - 1]),
                "fbc_seconds": a.times[s.a_start],
                "src_start_tok": s.b_start, "src_end_tok": s.b_end,
                "fbc_len": s.a_len, "src_len": s.b_len, "matched": s.matched, "identity": s.identity,
                "bible_overlap": round(ov, 2), "bible_ref": ref, "cue": cue, "recurrence": recur,
                "scripture_flag": flag,
                "fbc_text": display_span(a, s.a_start, s.a_end),
                "src_text": display_span(b, s.b_start, s.b_end),
            })
        row["segments"] = seg_rows

        # Scripture-adjusted coverage
        scr_mask = [False] * a.n
        for sr in seg_rows:
            if sr["scripture_flag"] == "likely_scripture":
                for t in range(sr["fbc_start_tok"], sr["fbc_end_tok"]):
                    scr_mask[t] = True
        nonscr_fuzzy = sum(1 for i in range(a.n) if fuzzy_mask[i] and not scr_mask[i])

        # sermon window heuristic (refined later with reviewer timestamps)
        lo, hi = sermon_window_heuristic(a, [s for s, _ in all_segs])
        row["window_heuristic"] = {"start_tok": lo, "end_tok": hi, "start_time": fmt_time(a.times[lo]) if a.times else "",
                                   "end_time": fmt_time(a.times[hi - 1]) if a.times else "", "tokens": hi - lo}

        row["coverage"] = {
            "exact8_tokens": sum(exact_mask), "exact8_pct_total": pct(sum(exact_mask), a.n),
            "exact5_tokens": sum(exact5_mask), "exact5_pct_total": pct(sum(exact5_mask), a.n),
            "fuzzy_tokens": sum(fuzzy_mask), "fuzzy_pct_total": pct(sum(fuzzy_mask), a.n),
            "fuzzy_matched_tokens": sum(tok_mask), "fuzzy_matched_pct_total": pct(sum(tok_mask), a.n),
            "fuzzy_nonscripture_tokens": nonscr_fuzzy, "fuzzy_nonscripture_pct_total": pct(nonscr_fuzzy, a.n),
            "scripture_tokens": sum(scr_mask),
            "fuzzy_pct_window": pct(sum(fuzzy_mask[lo:hi]), hi - lo),
            "segments": len(seg_rows),
            "longest_segment_tokens": max([s["fbc_len"] for s in seg_rows], default=0),
            "longest_exact_run": max([matrix[(a.key, b.key)]["longest_exact"] for b in paired], default=0),
        }
        # source consumption
        row["source_consumption"] = []
        for b in paired:
            m = matrix[(a.key, b.key)]
            row["source_consumption"].append({"source": b.key, "title": b.title, "tokens": b.n,
                                              "covered_tokens": m["fuzzy_cov_src"], "covered_pct": m["fuzzy_cov_src_pct"]})

        # per-minute density (fuzzy coverage) for timeline strips
        dur = int(a.times[-1] // 60) + 1 if a.times else 0
        per_min_total = [0] * dur
        per_min_cov = [0] * dur
        per_min_scr = [0] * dur
        for i, t in enumerate(a.times):
            m = int(t // 60)
            per_min_total[m] += 1
            if fuzzy_mask[i]:
                per_min_cov[m] += 1
            if scr_mask[i]:
                per_min_scr[m] += 1
        row["per_minute"] = {"total": per_min_total, "covered": per_min_cov, "scripture": per_min_scr}

        # order preservation: positions of segments (for dot plot & rank correlation)
        pts = [(sr["fbc_start_tok"], sr["src_start_tok"], sr["source"], sr["fbc_len"]) for sr in seg_rows]
        row["dotplot"] = pts
        if len(pts) >= 4:
            # Spearman rho on (fbc pos, src pos) for the best source only
            best = paired[0].key
            xs = [p[0] for p in pts if p[2] == best]
            ys = [p[1] for p in pts if p[2] == best]
            row["order_rho"] = spearman(xs, ys) if len(xs) >= 4 else None
        else:
            row["order_rho"] = None

        results["fbc"].append(row)

        # human-readable alignment dump for reviewers
        with open(OUT / "alignments" / f"{a.key}.txt", "w", encoding="utf-8") as fh:
            fh.write(f"# {a.title} ({a.meta['date']}) — reused regions vs Alistair Begg sources\n")
            fh.write(f"# FBC tokens: {a.n}; paired sources: {[b.title for b in paired]}\n")
            fh.write(f"# fuzzy coverage {row['coverage']['fuzzy_pct_total']}% of full transcript; "
                     f"{row['coverage']['fuzzy_pct_window']}% of heuristic sermon window "
                     f"{row['window_heuristic']['start_time']}–{row['window_heuristic']['end_time']}\n\n")
            for k, sr in enumerate(seg_rows, 1):
                fh.write(f"=== Region {k}  FBC {sr['fbc_time']}–{sr['fbc_time_end']}  ({sr['fbc_len']} words, identity {sr['identity']:.2f}, "
                         f"scripture={sr['scripture_flag']}{' ' + sr['bible_ref'] if sr['bible_ref'] and sr['scripture_flag']!='non_scripture' else ''})  source: {sr['source']}\n")
                fh.write(f"FBC : {sr['fbc_text']}\n")
                fh.write(f"BEGG: {sr['src_text']}\n\n")

    # corpus-level totals
    tot_tokens = sum(r["tokens"] for r in results["fbc"])
    results["totals"] = {
        "fbc_transcripts": len(fbc), "source_transcripts": len(src),
        "fbc_tokens": tot_tokens,
        "fuzzy_tokens": sum(r["coverage"]["fuzzy_tokens"] for r in results["fbc"]),
        "exact8_tokens": sum(r["coverage"]["exact8_tokens"] for r in results["fbc"]),
        "nonscripture_fuzzy_tokens": sum(r["coverage"]["fuzzy_nonscripture_tokens"] for r in results["fbc"]),
        "sermons_with_pair": sum(1 for r in results["fbc"] if r["paired_sources"]),
    }
    json.dump(results, open(OUT / "results.json", "w"), indent=1)
    print(json.dumps(results["totals"], indent=1))
    for r in results["fbc"]:
        c = r["coverage"]
        print(f"{r['title']:28s} pairs={len(r['paired_sources'])} exact8={c['exact8_pct_total']:5.1f}% fuzzy={c['fuzzy_pct_total']:5.1f}% "
              f"window={c['fuzzy_pct_window']:5.1f}% nonscr={c['fuzzy_nonscripture_pct_total']:5.1f}% noise_max={r['noise_floor_pct']['max']} rho={r['order_rho']}")


def spearman(xs, ys):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0] * len(v)
        for rank, i in enumerate(order):
            r[i] = rank
        return r
    rx, ry = ranks(xs), ranks(ys)
    n = len(xs)
    d2 = sum((a - b) ** 2 for a, b in zip(rx, ry))
    return round(1 - 6 * d2 / (n * (n * n - 1)), 3)


if __name__ == "__main__":
    main()
