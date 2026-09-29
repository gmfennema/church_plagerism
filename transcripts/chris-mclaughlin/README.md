# Chris McLaughlin transcript handoff

This folder is a transcript store for the user's requested collection. Do not create a church record, plagiarism finding, site report, or Convex task for this work. The requested deliverables are individual sermon text files and one combined text file in this folder. Keep source audio and video out of Git.

## Sources and scope

- Speaker archive: https://fieldspres.org/media/speaker/Chris+McLaughlin
- Church YouTube channel: https://www.youtube.com/@fieldspres/videos
- [video-links.md](video-links.md) is a human-readable list of all 99 retrievable recordings, with church page, Subsplash, matched YouTube, and direct media links.
- [manifest.json](manifest.json) has the same inventory as structured data: title, date, passage, speaker, duration, source URLs, short code, and any matched YouTube ID.

The speaker page displayed **105** items on 2026-09-29 UTC. Its live `POST /controllers/subsplash` pagination (`action=getMediaItems`, `method=speaker`, `value=Chris McLaughlin`, `limit=12`) returned **99 unique items** across nine pages (12 each on pages 1–8, three on page 9); the API reported `total=99`. The other six could not be identified from that listing. The 99 include 70 Sunday sermons with video and 29 weekday sessions or teachings, totaling about 62.6 hours. One Sunday item lacks a direct audio link; the 29 weekday items have audio but no video link in the manifest.

**43 items** have high-confidence YouTube matches based on exact normalized titles, with Scripture used to resolve ambiguity. The remaining **56** have no confirmed YouTube counterpart. A match does not establish that captions can be downloaded.

## What has been tried

- The YouTube page's transcript export said **“No transcript is available”** for two recent matches (`BsHPzUBhjgA`, `cI2HJebQ6Qk`) and one older match (`9HdV078XZSg`). The player showed captions unavailable.
- `youtube-transcript-api` listed an English auto-generated track for `BsHPzUBhjgA`, but fetching it returned `IpBlocked` from this cloud environment.
- `yt-dlp --skip-download --write-auto-subs` reached the same video's subtitle request but received HTTP 429.
- A `faster-whisper` CPU transcription test in the cloud workspace was rejected by automatic approval review because model loading unexpectedly contacted a Microsoft telemetry endpoint. Do not assume that attempt produced a transcript. A local agent should choose a transcription setup with an understood network and privacy behavior.

There are **no transcript files yet**. The 1–3 hour caption-only plan was an estimate conditional on accessible captions and cannot be promised for these recordings. This inventory is a handoff, not a finished corpus.

## Suggested local workflow

1. Read `manifest.json`, use its `short_code` as the stable item ID, and verify the source count. Work through every item, including the weekday sessions unless the user later narrows the scope.
2. Check captions for matched YouTube videos using ordinary YouTube transcript access or the repo's `tools/fetch_transcripts.py`. Respect errors or site limits; record failures explicitly. Prefer human captions if present, then auto captions. Preserve the YouTube URL and caption provenance in each file.
3. For items without accessible captions, use the public Subsplash audio URL from the manifest (or video if audio is absent) with a local transcription tool. Label these as machine transcriptions, with model and date. Do not present them as YouTube captions. Do not commit MP3/MP4 files.
4. Save one UTF-8 `.txt` per item under `transcripts/chris-mclaughlin/items/`, for example `2026-05-17_vwtp3nq_the-lord-is-my-banner.txt`. Include title, date, passage, speaker, church page, media URL, transcript source, and timestamps when available.
5. Generate `chris-mclaughlin-all.txt` from those individual files in date order. Put a conspicuous boundary and original source URL between items. Generate a coverage report listing each of the 99 IDs as complete, missing, or failed. Do not silently omit items or invent text.
6. Spot-check a sample from the start, middle, and end of each recording, especially names and Scripture references. Confirm the combined file count against the coverage report before marking the work complete.

The existing `tools/fetch_transcripts.py` accepts YouTube URLs and writes timestamped text and snippet JSON under `research/<slug>/`; it does not understand this Subsplash speaker page. A local agent can reuse its fetching logic while writing final deliverables to this transcript folder. The user's explicit preference is to use this repository for storage without creating a church research record.
