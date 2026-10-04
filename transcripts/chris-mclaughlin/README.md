# Chris McLaughlin transcript handoff

This folder is a transcript store for the user's requested collection. Do not create a church record, plagiarism finding, site report, or Convex task for this work. The requested deliverables are individual sermon text files and one combined text file in this folder. Keep source audio and video out of Git.

## Sources and scope

- Speaker archive: https://fieldspres.org/media/speaker/Chris+McLaughlin
- Church YouTube channel: https://www.youtube.com/@fieldspres/videos
- [video-links.md](video-links.md) is a human-readable list of all 99 retrievable recordings, with church page, Subsplash, matched YouTube, and direct media links.
- [manifest.json](manifest.json) has the same inventory as structured data: title, date, passage, speaker, duration, source URLs, short code, and any matched YouTube ID.

The speaker page displayed **105** items on 2026-09-29 UTC. Its live `POST /controllers/subsplash` pagination (`action=getMediaItems`, `method=speaker`, `value=Chris McLaughlin`, `limit=12`) returned **99 unique items** across nine pages (12 each on pages 1–8, three on page 9); the API reported `total=99`. The other six could not be identified from that listing. The 99 include 70 Sunday sermons with video and 29 weekday sessions or teachings, totaling about 62.6 hours. One Sunday item lacks a direct audio link; the 29 weekday items have audio but no video link in the manifest.

**43 items** have high-confidence YouTube matches based on exact normalized titles, with Scripture used to resolve ambiguity. The remaining **56** have no confirmed YouTube counterpart. A match does not establish that captions can be downloaded.

## Caption collection — 2026-10-04

The first caption pass produced **27 English auto-caption transcripts**, containing **156,383 transcript words**. The combined file is ready for querying:

- [`chris-mclaughlin-all.txt`](chris-mclaughlin-all.txt): chronological collection with a contents list, conspicuous START/END boundaries, stable recording IDs, dates, passages, source URLs, and timestamps.
- [`items/`](items/): individual text transcripts and the original caption segments with provenance.
- [`coverage.md`](coverage.md) / [`coverage.json`](coverage.json): status of every one of the 99 manifest recordings.
- [`verification.json`](verification.json): integrity checks and beginning/middle/end text samples from every completed recording.

**This is a partial corpus.** Of the 43 confirmed YouTube matches, 27 captions were retrieved and 16 requests returned `IpBlocked`. Those failures do not establish that the videos lack captions. The other 56 recordings have no confirmed YouTube match and were not fetched. No audio or video was downloaded, and no local transcription was performed. The archive's earlier 105-versus-99 discrepancy remains unresolved.

Verification confirmed matching start/end boundaries, inclusion of each individual transcript in the combined file, ordered timestamps, and caption endpoints within 10% or 60 seconds of the archive durations. The caption text was inspected at the beginning, middle, and end; it has not been checked against audio. Automatic captions may misrecognize names, references, and quotations. Preserve the original captions and verify any consequential quotation against its recording.

To rebuild the collection without network requests:

```bash
python3 transcripts/chris-mclaughlin/collect_captions.py --offline
```

After YouTube's limits clear, resume caption collection with:

```bash
python3 transcripts/chris-mclaughlin/collect_captions.py --retry-failed --request-delay 60
```

The collector reuses completed caption files, waits 60 seconds between new requests by default, and stops network access on a blocking response. A later attempt with this spacing still received `IpBlocked` on its first new request, so the other failed requests were not retried in that run. It never downloads audio/video. Audio transcription remains a later phase.

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
