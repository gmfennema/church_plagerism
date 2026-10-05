# Chris McLaughlin transcript collection

This folder is a transcript store for the user's requested collection. Do not create a church record, plagiarism finding, site report, or Convex task for this work. The requested deliverables are individual sermon text files and one combined text file in this folder. Keep source audio and video out of Git.

## Completed collection — 2026-10-04

**All 99 manifest recordings are complete:** 27 YouTube auto-caption transcripts and 72 local Whisper transcriptions, totaling **547,733 transcript words**. These cover the 70 Sunday sermons and 29 other teaching sessions in the inventory. The earlier archive display discrepancy (105 displayed versus 99 retrievable items) remains unresolved; completion refers to the 99 identified recordings.

For an AI agent, use [`chris-mclaughlin-query.txt`](chris-mclaughlin-query.txt): one chronological UTF-8 text file with a contents list, clear START/END boundaries, stable recording IDs, titles, dates, passages, original URLs, and transcription provenance. It preserves every transcript word, normalizes whitespace into paragraphs, and omits per-segment timestamps. It contains **664,770 tokens using `o200k_base`** (about 2.95 MB). Token counts differ with other tokenizers; leave room for the agent's instructions and response.

[`chris-mclaughlin-all.txt`](chris-mclaughlin-all.txt) retains segment timestamps for tracing quotations and contains 1,238,699 tokens with the same tokenizer. Individual timestamped text and original caption/local segment metadata are in [`items/`](items/).

Final verification checked all 99 IDs, both files' 99 matching boundaries, preservation of every transcript word in the query copy, unchanged original caption files, monotonic timestamps, duration consistency, and temporary audio deletion. No automated quality flags or significant endpoint discrepancies were found. This is not a manual word-for-word verification of the recordings; machine recognition errors may remain. See [`verification.json`](verification.json), [`coverage.md`](coverage.md), and [`coverage.json`](coverage.json).

Seven batches of 10 local transcripts were committed and pushed, followed by the final single-recording remainders and the compact query-copy completion update. No source audio, video, model, local environment, or credentials were committed.

## Sources and scope

- Speaker archive: https://fieldspres.org/media/speaker/Chris+McLaughlin
- Church YouTube channel: https://www.youtube.com/@fieldspres/videos
- [video-links.md](video-links.md) is a human-readable list of all 99 retrievable recordings, with church page, Subsplash, matched YouTube, and direct media links.
- [manifest.json](manifest.json) has the same inventory as structured data: title, date, passage, speaker, duration, source URLs, short code, and any matched YouTube ID.

The speaker page displayed **105** items on 2026-09-29 UTC. Its live `POST /controllers/subsplash` pagination (`action=getMediaItems`, `method=speaker`, `value=Chris McLaughlin`, `limit=12`) returned **99 unique items** across nine pages (12 each on pages 1–8, three on page 9); the API reported `total=99`. The other six could not be identified from that listing. The 99 include 70 Sunday sermons with video and 29 weekday sessions or teachings, totaling about 62.6 hours. One Sunday item lacks a direct audio link; the 29 weekday items have audio but no video link in the manifest.

**43 items** have high-confidence YouTube matches based on exact normalized titles, with Scripture used to resolve ambiguity. The remaining **56** have no confirmed YouTube counterpart. A match does not establish that captions can be downloaded.

## Local audio transcription pipeline

The remaining recordings are processed with **Whisper large-v3-turbo through MLX on Apple Silicon**, using a pinned local model revision. Current counts, source types, and failures are in [`coverage.md`](coverage.md) and [`coverage.json`](coverage.json). The combined [`chris-mclaughlin-all.txt`](chris-mclaughlin-all.txt) is rebuilt after every completed recording; its chronological numbering can change, so cite the stable item ID and timestamp.

The worker downloads one public MP3 at a time, checks its duration against the manifest, transcribes it locally, saves timestamped text and segment metadata, rebuilds and checks the combined file, and deletes the temporary audio. For the single item without an MP3, it reads a public audio-only HLS stream and saves temporary audio. No video file is saved. Sermon audio is not uploaded to an AI service. Model and library downloads require network access during setup; Hugging Face telemetry is disabled and the worker loads the model offline.

Source recovery: “Enjoyment Restored” initially failed because its original MP4 URL returned 403. Its public Subsplash page advertises a playable master playlist with an audio-only rendition. That audio playlist was verified on 2026-10-04 (2,640.1 seconds, matching the manifest), and its URL/provenance were added to the manifest. The recovery run successfully transcribed it, deleted temporary audio, and pushed the final recording to GitHub.

Machine transcriptions are labeled separately from YouTube captions, with engine/model versions, pinned model revision, processing time, and quality flags. They are not manually corrected. Repetition, unusually sparse output, decoder scores, and early transcript endings are checked; consequential quotations should still be verified against the recording.

The queue prioritizes failed caption matches, then other Sunday sermons, then weekday teachings. `--sync` commits and pushes after **every 10 additional local transcripts**, including new text, segment metadata, the combined file, and coverage/verification reports. It also syncs the final remainder. A push failure stops the worker for recovery. Existing completed files are reused, and a lock prevents duplicate workers.

Setup on an Apple Silicon Mac with Python and ffmpeg installed:

```bash
python3 -m venv .transcription/venv
.transcription/venv/bin/python -m pip install -r transcripts/chris-mclaughlin/transcription-requirements.txt
.transcription/venv/bin/python transcripts/chris-mclaughlin/setup_transcription_model.py
```

Run or resume:

```bash
caffeinate -i .transcription/venv/bin/python -u transcripts/chris-mclaughlin/transcribe_remaining.py --sync
```

The ignored `.transcription/` directory contains the environment, model, lock, and `run.json` progress. Only one recording's temporary audio is present during processing. Checkpoint sync uses the already signed-in `gmfennema` GitHub account without changing the default account. Run on `main` with no unrelated staged changes.

## Caption collection — 2026-10-04

The first caption pass produced **27 English auto-caption transcripts**, containing **156,383 transcript words**. The combined file is ready for querying:

- [`chris-mclaughlin-all.txt`](chris-mclaughlin-all.txt): chronological collection with a contents list, conspicuous START/END boundaries, stable recording IDs, dates, passages, source URLs, and timestamps.
- [`items/`](items/): individual text transcripts and the original caption segments with provenance.
- [`coverage.md`](coverage.md) / [`coverage.json`](coverage.json): status of every one of the 99 manifest recordings.
- [`verification.json`](verification.json): integrity checks and beginning/middle/end text samples from every completed recording.

**Caption-stage result:** of the 43 confirmed YouTube matches, 27 captions were retrieved and 16 requests returned `IpBlocked`. Those failures do not establish that the videos lack captions. The other 56 recordings have no confirmed YouTube match and were not fetched during this stage. No audio or video was downloaded during the caption pass. The archive's earlier 105-versus-99 discrepancy remains unresolved.

Verification confirmed matching start/end boundaries, inclusion of each individual transcript in the combined file, ordered timestamps, and caption endpoints within 10% or 60 seconds of the archive durations. The caption text was inspected at the beginning, middle, and end; it has not been checked against audio. Automatic captions may misrecognize names, references, and quotations. Preserve the original captions and verify any consequential quotation against its recording.

To rebuild the collection without network requests:

```bash
python3 transcripts/chris-mclaughlin/collect_captions.py --offline
```

After YouTube's limits clear, resume caption collection with:

```bash
python3 transcripts/chris-mclaughlin/collect_captions.py --retry-failed --request-delay 60
```

The caption collector reuses completed files, waits 60 seconds between new requests by default, and stops network access on a blocking response. A later attempt with this spacing still received `IpBlocked` on its first new request, so the other failed requests were not retried in that run. It never downloads audio/video. The shared offline builder includes both saved captions and local audio transcripts.

## What has been tried

- The YouTube page's transcript export said **“No transcript is available”** for two recent matches (`BsHPzUBhjgA`, `cI2HJebQ6Qk`) and one older match (`9HdV078XZSg`). The player showed captions unavailable.
- `youtube-transcript-api` listed an English auto-generated track for `BsHPzUBhjgA`, but fetching it returned `IpBlocked` from this cloud environment.
- `yt-dlp --skip-download --write-auto-subs` reached the same video's subtitle request but received HTTP 429.
- A `faster-whisper` CPU transcription test in the cloud workspace was rejected by automatic approval review because model loading unexpectedly contacted a Microsoft telemetry endpoint. Do not assume that attempt produced a transcript. A local agent should choose a transcription setup with an understood network and privacy behavior.

At the time of the original handoff there were no transcript files. The earlier 1–3 hour caption-only plan was conditional on accessible captions; see the current collection status above.

## Suggested local workflow

1. Read `manifest.json`, use its `short_code` as the stable item ID, and verify the source count. Work through every item, including the weekday sessions unless the user later narrows the scope.
2. Check captions for matched YouTube videos using ordinary YouTube transcript access or the repo's `tools/fetch_transcripts.py`. Respect errors or site limits; record failures explicitly. Prefer human captions if present, then auto captions. Preserve the YouTube URL and caption provenance in each file.
3. For items without accessible captions, use the public Subsplash audio URL from the manifest (or video if audio is absent) with a local transcription tool. Label these as machine transcriptions, with model and date. Do not present them as YouTube captions. Do not commit MP3/MP4 files.
4. Save one UTF-8 `.txt` per item under `transcripts/chris-mclaughlin/items/`, for example `2026-05-17_vwtp3nq_the-lord-is-my-banner.txt`. Include title, date, passage, speaker, church page, media URL, transcript source, and timestamps when available.
5. Generate `chris-mclaughlin-all.txt` from those individual files in date order. Put a conspicuous boundary and original source URL between items. Generate a coverage report listing each of the 99 IDs as complete, missing, or failed. Do not silently omit items or invent text.
6. Spot-check a sample from the start, middle, and end of each recording, especially names and Scripture references. Confirm the combined file count against the coverage report before marking the work complete.

The existing `tools/fetch_transcripts.py` accepts YouTube URLs and writes timestamped text and snippet JSON under `research/<slug>/`; it does not understand this Subsplash speaker page. A local agent can reuse its fetching logic while writing final deliverables to this transcript folder. The user's explicit preference is to use this repository for storage without creating a church research record.
