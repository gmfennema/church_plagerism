---
name: research-church
description: Run a full sermon-integrity review of one Tucson church (plagiarism + AI-writing signals) and update its record. Use when asked to research, review, check, or clear a church or pastor, or to add a new church to the map.
argument-hint: <slug or church name> [--pastor "Name"]
---

# /research-church

You are performing one church review end to end, following `AGENTS.md` in the repository root. Read it in
full before starting; the rubric there decides statuses, not your intuition.

Argument: `$ARGUMENTS` (a slug from `data/churches/`, or a church name to add).

## Steps

1. **Locate or create the record.** `ls data/churches/ | grep -i <term>`. If absent, verify the church facts in
   the browser (official website: staff, about, address, YouTube link) and scaffold with `tools/new_church.py`.
   Immediately set the relevant findings to `in_progress`, validate, commit on branch `research/<slug>`, push.
2. **Sermons.** Find the sermon playlist/channel. Run `tools/fetch_transcripts.py`. Use `--audio-fallback` and
   `tools/transcribe_audio.py` when captions are disabled. Map each video to its preacher.
3. **Source hunt (browser).** For every sermon pick 3 to 5 distinctive non-Scripture phrases and search them in
   quotes; search the passage + title on Truth For Life, Desiring God, Gospel in Life, Grace to You,
   SermonAudio, Sermon Central, Monergism, Ligonier. Collect transcripts of credible leads into
   `research/<slug>/source_transcripts/<source-slug>/` with a `meta.json`. Check attribution by listening to
   the opening and closing minutes of two or three matched sermons.
4. **Compare.** `python3 tools/compare_transcripts.py --church <slug> --pastor "<Name>"`; classify the longest
   passages (Scripture vs source commentary). Re-run with `--exclude-file` if Scripture dominates.
5. **AI signals.** `python3 tools/ai_writing_signals.py --church <slug> --pastor "<Name>"`, with `--baseline`
   if older sermons of the same preacher exist.
6. **Decide with the rubric** (AGENTS.md step 7) and write the findings into the record: status, confidence,
   summary, sermons_reviewed, review_period, methods, sources_compared (with attributed_in_sermon),
   evidence (3 to 6 items with URLs), metrics, reports, last_reviewed, reviewed_by. Update church summary,
   notes, updated_at, updated_by. Write `research/<slug>/README.md`.
7. **Ship.** `python3 tools/validate.py <slug> && python3 tools/build.py`; commit `data/churches/<slug>.json`
   and `research/<slug>/` (never audio, never `site/data`), push, open a PR titled
   `research(<slug>): <result>` whose body lists sermons reviewed, sources compared, and the rubric line that
   decided the status.

## Guardrails

- Never set `flagged` from one sermon, from Scripture overlap, or from AI-phrase counts alone.
- Never invent a pastor name, URL, or coordinate. Unknown is recorded as unknown.
- Neutral wording. The site promises an evidence review, not a verdict.
- If you run out of time, leave the status `in_progress` (or `inconclusive` with an explanation), write what
  you learned in `notes`, and still push so the next agent can continue.
