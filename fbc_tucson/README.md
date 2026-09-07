# FBC Tucson playlist transcripts

This project stores the available transcripts from the FBC Tucson YouTube playlist:

<https://youtube.com/playlist?list=PLEFrfWIivGoZxyyOR8G49a2HKwczrRut5>

The parent project and folder names intentionally match the requested spelling:
`church_plagerism/fbc_tucson`.

## Contents

- `fetch_playlist_transcripts.py` — repeatable downloader using `yt-dlp` and `youtube-transcript-api`
- `playlist.json` — playlist metadata and per-video status
- `failures.json` — videos that were unavailable or had no accessible transcript
- `transcripts/*.txt` — readable timestamped transcripts
- `transcripts/*.json` — structured transcript snippets and metadata
- `source_transcripts/volume*/` — locally generated transcripts of the public Truth For Life source audio
- `plagiarism_report.pdf` — formatted evidence review
- `plagiarism_report.md` — readable report text
- `plagiarism_analysis.json` — machine-readable comparison results
- `generate_plagiarism_report.py` — reproducible exact-match analysis and PDF generator

The downloaded source MP3s live in `source_audio/` locally but are intentionally excluded from version control because of their size and copyright status.

## Setup

`yt-dlp` must be available on your PATH. Install the Python dependency with:

```bash
python3 -m pip install --user youtube-transcript-api
```

## Run

From this directory:

```bash
python3 fetch_playlist_transcripts.py
```

Or provide another playlist URL:

```bash
python3 fetch_playlist_transcripts.py "https://www.youtube.com/playlist?list=..."
```

The script keeps going when a video is unavailable or subtitles are disabled. Those cases are recorded in `failures.json` rather than stopping the whole batch.
