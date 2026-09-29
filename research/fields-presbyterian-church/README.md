# Chris McLaughlin sermon transcript collection

Source: https://fieldspres.org/media/speaker/Chris+McLaughlin

## Inventory and scope

The speaker page displayed 105 items on 2026-09-29, but its live `getMediaItems` pagination returned 99 distinct items across nine pages (12 on pages 1–8, three on page 9) and reported a total of 99. The six-item discrepancy is unresolved. The 99 items include 70 Sunday sermons and 29 weekday sessions or teachings, totaling approximately 62.6 hours. This collection aims to include all 99 retrievable items unless the other six are identified.

The JSON manifest records the church page, title, date, passage, media links, and any matched YouTube URL. It currently matches 43 items to the church's YouTube channel by title, using the passage to distinguish ambiguous titles. The unmatched items need source matching or transcription from Subsplash audio. The manifest is an inventory, not a claim that captions were obtained.

## Transcript workflow

1. For each matched YouTube URL, run the repository's `tools/fetch_transcripts.py --church fields-presbyterian-church URL`. Its outputs preserve timestamped text and caption snippets in `transcripts/`. Captions that fail are recorded in `failures.json`.
2. Review failures and fetch captions by another authorized route where possible. For items without YouTube captions, transcribe the publicly available Subsplash audio and label the provenance explicitly. Do not represent speech recognition output as YouTube captions.
3. Run `python3 research/fields-presbyterian-church/build_chris_corpus.py` to combine the fetched YouTube caption JSON files. It writes `chris-mclaughlin-all-sermons.txt` and `chris-mclaughlin-coverage.json`. It only includes nonempty, real caption snippets. The audio transcript integration will need a provenance-aware extension before those items can be included.
4. Verify the number of included items against the manifest and spot-check names, Scripture references, starts, middles, and ends. Keep missing items explicit in the coverage report.

## Current status

The inventory is ready. No transcript is committed yet. In this execution environment, the YouTube transcript API identifies an English automatic caption track for a sample sermon but its fetch is IP-blocked; yt-dlp's subtitle request returned HTTP 429. A local transcription attempt was stopped by automatic approval review when model loading unexpectedly contacted a Microsoft telemetry endpoint. No audio or video files should be committed.
