# FBC Tucson (Fellowship Bible Church Tucson) - research folder

Record: [`data/churches/fbc-tucson.json`](../../data/churches/fbc-tucson.json)

## What was done (Sept 2026)

1. Pulled the YouTube playlist *A Church of Irresistible Influence* (1 Thessalonians series, Apr-Aug 2026):
   9 of 25 videos had usable auto-captions (`transcripts/`); 9 had captions disabled and 7 were unavailable
   (`failures.json`, `playlist.json`).
2. Sermon titles matched Alistair Begg's Truth For Life series *A Study in 1 Thessalonians* volumes 1-3
   one-for-one. The 22 public MP3s were transcribed locally with Whisper (`source_transcripts/begg-1-thessalonians-vol{1,2,3}/`,
   audio not committed).
3. The preliminary exact-run analysis in `reports/plagiarism_analysis.json` found 3.72% coverage across
   whole-service transcripts. That number is retained as a diagnostic but is not the sermon-body result.
4. The final close-read review in `reports/plagiarism_report.pdf` and
   `reports/sermon_dependence_analysis.json` identifies six sermons by Pat McClanahan, marks the sermon
   boundaries, aligns near-verbatim regions, and classifies shared Scripture separately. Coverage is 10% to
   40% per sermon and 27.2% across the six sermon bodies (25.0% after shared Scripture is removed). Begg and
   Truth For Life were not named in any of the six sermons.
5. `python3 tools/ai_writing_signals.py --church fbc-tucson` produced `reports/ai_writing_signals.{json,md}`;
   no baseline, so the AI-writing finding stays `unchecked`/inconclusive.

## Still open

- Fetch older sermons (pre-2023) as `baseline_transcripts/` and re-run the AI signals with `--baseline`.
- Transcribe the nine caption-disabled sermons with `--audio-fallback` + `tools/transcribe_audio.py`.

`legacy/` holds the original one-off scripts this study was first done with; the generic tools in `tools/`
replace them.
