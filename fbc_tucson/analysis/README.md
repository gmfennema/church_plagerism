# Sermon dependence analysis (v2)

Reproducible pipeline behind `../sermon_dependence_report.pdf`. It replaces the exact-match-only
review in `../plagiarism_report.pdf` with fuzzy sequence alignment measured against the sermon body,
plus an independent full-transcript close reading of every sermon pair.

```
python3 analyze.py        # exact runs + fuzzy regions for all 9 x 22 pairs, baselines -> out/results.json, out/alignments/
#   (reviewer JSON in out/reviews/ is produced by the close-reading pass; see REVIEW_BRIEF.md)
python3 finalize.py       # merge reviewer boundaries + Scripture labels -> out/results_final.json
python3 charts.py         # exhibits -> out/figures/*.svg
python3 build_report.py   # -> report/report.html ; then print with headless Chromium:
chrome --headless=new --no-pdf-header-footer --print-to-pdf=report/report.pdf file://$PWD/report/report.html
```

| File | Purpose |
|---|---|
| `corpus.py` | caption/ASR normalisation, per-token timestamps |
| `matching.py` | exact runs; seed-and-extend fuzzy alignment |
| `analyze.py` | full comparison, Scripture heuristic, baselines |
| `finalize.py` | reviewer merge, sermon-body denominators |
| `charts.py` | matplotlib exhibits (palette validated with the dataviz checker) |
| `build_report.py`, `report/report.css` | report layout |
| `REVIEW_BRIEF.md` | instructions given to the close-reading reviewer (Claude Opus 5) |
| `out/reviews/*.json` | reviewer output per sermon |
| `out/alignments/*.txt` | every reused region, side by side, with timestamps |
| `bible_ref/` | public-domain KJV/BBE used by the Scripture heuristic |
| `fonts/` | Inter, Source Serif 4, IBM Plex Mono (Google Fonts, OFL) |

Python deps: numpy, scipy, matplotlib, rapidfuzz (unused fallback), pymupdf (page previews only).
