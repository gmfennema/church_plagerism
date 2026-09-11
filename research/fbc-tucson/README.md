# FBC Tucson (Fellowship Bible Church Tucson) - research folder

Record: [`data/churches/fbc-tucson.json`](../../data/churches/fbc-tucson.json)

## What was done (Sept 2026)

1. Pulled the YouTube playlist *A Church of Irresistible Influence* (1 Thessalonians series, Apr-Aug 2026):
   9 of 25 videos had usable auto-captions (`transcripts/`); 9 had captions disabled and 7 were unavailable
   (`failures.json`, `playlist.json`).
2. Sermon titles matched Alistair Begg's Truth For Life series *A Study in 1 Thessalonians* volumes 1-3
   one-for-one. The 22 public MP3s were transcribed locally with Whisper (`source_transcripts/begg-1-thessalonians-vol{1,2,3}/`,
   audio not committed).
3. `python3 tools/compare_transcripts.py --church fbc-tucson` produced `reports/plagiarism_analysis.json`,
   `reports/plagiarism_report.md`, `reports/plagiarism_report.pdf`: 8 of 9 sermons contain exact 8+ word runs,
   3,067 of 82,449 words (3.72%) inside matched runs, 6 sermons exceed the rubric. Longest run (42 words) is
   1 Thessalonians 5:23-24 and is excluded; the longest non-Scripture runs are 31, 25, 25, 24, 23 words of
   Begg's own commentary.
4. `python3 tools/ai_writing_signals.py --church fbc-tucson` produced `reports/ai_writing_signals.{json,md}`;
   no baseline, so the AI-writing finding stays `unchecked`/inconclusive.

## Still open

- Confirm the preaching pastor's name from the church staff page and confirm the church's address.
- Listen to the opening and closing minutes of two or three matched sermons for spoken attribution to Begg;
  set `attributed_in_sermon` accordingly. Attribution would move the finding toward `cleared`.
- Fetch older sermons (pre-2023) as `baseline_transcripts/` and re-run the AI signals with `--baseline`.
- Transcribe the nine caption-disabled sermons with `--audio-fallback` + `tools/transcribe_audio.py`.

`legacy/` holds the original one-off scripts this study was first done with; the generic tools in `tools/`
replace them.
