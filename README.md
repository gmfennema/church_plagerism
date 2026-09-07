# Church plagiarism analysis

Private research workspace for reviewing textual overlap between the FBC Tucson sermon playlist and the Alistair Begg 1 Thessalonians source archive.

## Current study

- [`fbc_tucson/sermon_dependence_report.pdf`](fbc_tucson/sermon_dependence_report.pdf) — **current report** (v2): fuzzy alignment against the sermon body, baselines, structure analysis, and a full-transcript close reading of every sermon pair. Headline: about 27% of the senior pastor's sermon words sit inside near-verbatim Begg passages; the two sermons by other FBC preachers contain none.
- [`fbc_tucson/analysis/`](fbc_tucson/analysis/) — reproducible v2 pipeline, reviewer output, and every reused region side by side with timestamps.
- [`fbc_tucson/`](fbc_tucson/) — playlist metadata, available FBC transcripts, source transcripts.
- [`fbc_tucson/plagiarism_report.pdf`](fbc_tucson/plagiarism_report.pdf) — superseded v1 review (exact 8-word runs, whole-transcript denominator; reported 3.7%).
- [`fbc_tucson/plagiarism_analysis.json`](fbc_tucson/plagiarism_analysis.json) — v1 machine-readable results.

The analysis is an evidence review, not a legal or ecclesiastical verdict. It uses locally generated ASR transcripts for the public source audio and YouTube auto-captions for the FBC material; Scripture quotations and transcription errors require contextual review.

Downloaded source MP3s are intentionally excluded from version control. They remain available locally for reproducible re-transcription.
