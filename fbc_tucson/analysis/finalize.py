"""Merge machine results with reviewer JSON (sermon boundaries, Scripture labels)
and compute the final, sermon-body-denominated metrics used by the report."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpus import load_all, fmt_time  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
REV = OUT / "reviews"


def hms_to_s(s: str) -> float:
    parts = [float(p) for p in s.strip().split(":")]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def main():
    res = json.load(open(OUT / "results.json"))
    fbc, src = load_all()
    docs = {d.key: d for d in fbc}
    reviews = {}
    for p in REV.glob("*.json"):
        try:
            reviews[p.stem] = json.load(open(p))
        except Exception as e:  # keep going; report which review failed
            print("BAD REVIEW", p, e)

    for row in res["fbc"]:
        d = docs[row["key"]]
        rv = reviews.get(row["key"])
        row["review"] = rv
        # --- sermon body window --------------------------------------------------
        if rv and rv.get("sermon_start") and rv.get("sermon_end") and rv["sermon_start"] not in ("n/a", ""):
            s0, s1 = hms_to_s(rv["sermon_start"]), hms_to_s(rv["sermon_end"])
            lo = next((i for i, t in enumerate(d.times) if t >= s0), 0)
            hi = next((i for i, t in enumerate(d.times) if t > s1), d.n)
            row["window"] = {"start_tok": lo, "end_tok": hi, "start_time": fmt_time(s0), "end_time": fmt_time(s1),
                             "tokens": hi - lo, "minutes": round((s1 - s0) / 60, 1), "source": "reviewer"}
        else:
            w = row["window_heuristic"]
            lo, hi = w["start_tok"], w["end_tok"]
            row["window"] = {**w, "minutes": round((d.times[hi - 1] - d.times[lo]) / 60, 1) if d.times else 0, "source": "heuristic"}

        # --- Scripture relabel using reviewer region classification ---------------
        cls = (rv or {}).get("region_classification", {}) or {}
        for k, seg in enumerate(row["segments"], 1):
            lab = cls.get(str(k))
            seg["machine_flag"] = seg["scripture_flag"]
            if lab in ("scripture", "non_scripture", "mixed"):
                seg["final_class"] = lab
            else:
                seg["final_class"] = "scripture" if seg["scripture_flag"] == "likely_scripture" else "non_scripture"

        # --- recompute masks -----------------------------------------------------
        n = d.n
        fuzzy = [False] * n
        scr = [False] * n
        for seg in row["segments"]:
            for t in range(seg["fbc_start_tok"], seg["fbc_end_tok"]):
                fuzzy[t] = True
                if seg["final_class"] == "scripture":
                    scr[t] = True
                elif seg["final_class"] == "mixed":
                    scr[t] = scr[t]  # count mixed as non-scripture (conservative for Scripture, not for reuse)
        body = hi - lo
        f_body = sum(fuzzy[lo:hi])
        s_body = sum(1 for i in range(lo, hi) if scr[i])
        ns_body = f_body - s_body
        row["body"] = {
            "tokens": body,
            "reused_tokens": f_body, "reused_pct": round(100 * f_body / body, 1) if body else 0,
            "scripture_tokens": s_body, "scripture_pct": round(100 * s_body / body, 1) if body else 0,
            "nonscripture_tokens": ns_body, "nonscripture_pct": round(100 * ns_body / body, 1) if body else 0,
            "exact8_pct": round(100 * row["coverage"]["exact8_tokens"] / body, 1) if body else 0,
            "outside_window_reused": sum(fuzzy) - f_body,
        }
        row["per_minute"]["scripture"] = [0] * len(row["per_minute"]["total"])
        for i, t in enumerate(d.times):
            if scr[i]:
                row["per_minute"]["scripture"][int(t // 60)] += 1
        row["per_minute"]["window_min"] = [d.times[lo] / 60, d.times[hi - 1] / 60]
        # segment identity distribution (non-scripture only)
        row["identity_hist"] = [seg["identity"] for seg in row["segments"] if seg["final_class"] != "scripture"]
        row["rating"] = (rv or {}).get("dependence_rating")

    # corpus totals over paired sermons' bodies
    paired = [r for r in res["fbc"] if r["paired_sources"]]
    tb = sum(r["body"]["tokens"] for r in paired)
    res["totals"].update({
        "paired_body_tokens": tb,
        "paired_body_reused": sum(r["body"]["reused_tokens"] for r in paired),
        "paired_body_reused_pct": round(100 * sum(r["body"]["reused_tokens"] for r in paired) / tb, 1) if tb else 0,
        "paired_body_nonscripture": sum(r["body"]["nonscripture_tokens"] for r in paired),
        "paired_body_nonscripture_pct": round(100 * sum(r["body"]["nonscripture_tokens"] for r in paired) / tb, 1) if tb else 0,
        "paired_body_scripture": sum(r["body"]["scripture_tokens"] for r in paired),
        "reviews_loaded": len(reviews),
    })
    json.dump(res, open(OUT / "results_final.json", "w"), indent=1)
    print(json.dumps(res["totals"], indent=1))
    for r in res["fbc"]:
        w, b = r["window"], r["body"]
        print(f"{r['title']:26s} window {w['start_time']}-{w['end_time']} ({w['source'][:4]}, {w['tokens']} tok, {w['minutes']} min) "
              f"reused {b['reused_pct']:5.1f}%  non-scr {b['nonscripture_pct']:5.1f}%  scr {b['scripture_pct']:4.1f}%  rating={r['rating']}")


if __name__ == "__main__":
    main()
