# Research agent handbook

This file is the contract for anyone (human or AI agent) who adds or updates a church in this repository.
Follow it exactly so that records stay comparable and the site stays trustworthy.

## The one-paragraph version

Every church is one JSON file at `data/churches/<slug>.json` that follows `data/schema/church.schema.json`.
Every deep dive lives in `research/<slug>/` (transcripts, source transcripts, generated reports).
You never edit `site/data/` or `site/reports/` by hand; `python3 tools/build.py` regenerates them.
Before you finish: `python3 tools/validate.py && python3 tools/build.py` must pass, then commit on a branch
named `research/<slug>` and open a pull request.

## Setup (once per machine)

```bash
python3 -m pip install -r tools/requirements.txt
# yt-dlp on PATH: https://github.com/yt-dlp/yt-dlp#installation  (brew install yt-dlp / pipx install yt-dlp)
# optional, for churches whose YouTube captions are disabled:
python3 -m pip install faster-whisper
```

## Repository map

| Path | What it is | Who writes it |
|---|---|---|
| `data/churches/<slug>.json` | The record for one church: identity, pastors, findings, report links | agents and humans, by hand or with `tools/new_church.py` |
| `data/schema/church.schema.json` | JSON Schema every record must satisfy | maintainers only |
| `research/<slug>/` | Working files for a deep dive (see layout below) | tools, plus your notes |
| `tools/` | Python CLI tools described below | maintainers only |
| `site/` | Static website (Leaflet map). `site/data/` and `site/reports/` are generated | `tools/build.py` |
| `.claude/skills/research-church/` | The `/research-church` skill for Claude Code | maintainers only |

### `research/<slug>/` layout

```
research/<slug>/
  README.md                       what was done, by whom, and what is still open
  playlists/<id>.json             per-video status from tools/fetch_transcripts.py
  failures.json                   videos with no accessible captions
  transcripts/*.txt|*.json        the church's sermons, one file per video
  audio/                          downloaded audio (gitignored)
  baseline_transcripts/*.txt      OPTIONAL: the same preacher's older sermons for AI-signal comparison
  source_transcripts/<source-slug>/*.txt   suspected source sermons, one folder per author/series
  source_transcripts/<source-slug>/meta.json  {"author","title","url","titles":{stem:title}}
  reports/plagiarism_analysis.json, plagiarism_report.md, plagiarism_report.pdf
  reports/ai_writing_signals.json, ai_writing_signals.md
```

Source audio (MP3/M4A) is never committed. Transcripts of public sermons are committed because they are the
evidence the reports rest on.

## Workflow

### 1. Pick or create the church

- Existing record: pick a church whose pastors are `unchecked`, set each finding you are about to work on to
  `"status": "in_progress"`, commit and push that small change first so parallel agents do not collide.
- New church: `python3 tools/new_church.py --name ... --tradition ... --address ... --source "Label|URL" --by "<you>"`
  then fill in the rest by hand. Scope is Protestant churches in the Tucson metro (Tucson, Oro Valley,
  Marana, Vail, Sahuarita, Catalina Foothills, South Tucson). Roman Catholic, LDS, Jehovah's Witness and
  Orthodox congregations are out of scope; if you researched one by mistake, keep the record with
  `"in_scope": false` and an `out_of_scope_reason` so nobody repeats the work.

### 2. Establish the facts about the church

From the church's own website (staff page, about page, footer), confirm: official name, address, denomination
or affiliation, website, YouTube channel and sermon playlist(s), and every regular preaching pastor with
their role. Record each page you used under `sources`. Do not guess names. If the site does not list a
preacher, leave `pastors: []` and say so in `notes`.

Coordinates: run `python3 tools/geocode.py <slug>` on a machine with internet access. It sets
`geocode: "verified"` for a house-number match and `"approximate"` otherwise. Never hand-type coordinates
as `verified`.

### 3. Get the sermons

```bash
python3 tools/fetch_transcripts.py --church <slug> "<playlist or channel /videos URL>" --limit 30
```

Aim for at least 8 sermons per preaching pastor spread over the last 12 to 24 months, and note which
pastor preached each one (the video title or description usually says). When captions are disabled:

```bash
python3 tools/fetch_transcripts.py --church <slug> "<url>" --audio-fallback
python3 tools/transcribe_audio.py research/<slug>/audio/*.m4a --out research/<slug>/transcripts
```

If you cannot obtain at least 4 transcripts for a pastor, the finding is `inconclusive`, not `cleared`.

### 4. Find candidate sources (the browser-heavy step)

For each sermon, pick 3 to 5 distinctive phrases that are NOT Scripture, NOT a hymn or creed, and NOT a
generic Christian idiom: an illustration, a turn of phrase, an unusual transition, a specific claim.
Search each in quotes on Google and Bing, and search the sermon's Scripture passage plus the sermon title
on the big sermon libraries: Truth For Life (Begg), Desiring God (Piper), Gospel in Life (Keller), Grace to
You (MacArthur), SermonAudio, Sermon Central, Monergism, Ligonier, Preaching Today, and the websites of
well-known megachurch pastors. Series titles that match a published series are a strong lead: FBC Tucson's
"Faith, Hope and Love", "No Clever Tricks", "Our Glory and Joy" matched Begg's sermon titles one-for-one.

When a lead is credible, obtain the source transcript:
- Published transcript on the ministry site: save the text as `research/<slug>/source_transcripts/<source-slug>/<nn-title>.txt`
  with a `# Title` line and `# URL` line at the top.
- Audio only: download the public MP3 locally (do not commit it) and run `tools/transcribe_audio.py ... --out research/<slug>/source_transcripts/<source-slug>`.
- Add `meta.json` to the folder with `author`, `title` (series), `url`, and a `titles` map from file stem to display title.

Also check attribution: listen to the first and last two minutes of two or three matched sermons and look at
the church's sermon notes or bulletin. Record `attributed_in_sermon` true/false/null on each source compared.

### 5. Run the comparison

```bash
python3 tools/compare_transcripts.py --church <slug> --pastor "<Name>"
```

Read `research/<slug>/reports/plagiarism_report.md`. For each of the longest passages decide: Scripture /
liturgy (ignore), or the source's own commentary, illustration or transition (evidence). If Scripture
dominates the matches, pass the quoted passages in a text file via `--exclude-file` and re-run.

### 6. Run the AI-writing signals

```bash
python3 tools/ai_writing_signals.py --church <slug> --pastor "<Name>" [--baseline research/<slug>/baseline_transcripts]
```

A baseline of the same preacher's sermons from before 2023 makes this meaningful; without one the tool will
tell you the result is `inconclusive`. Then read the corroboration checklist in the report.

The tool only counts stylometric signals. For the qualitative read - which patterns actually mean something in
a sermon, and the false-positive traps specific to preaching - see
[`docs/ai-writing-signs.md`](docs/ai-writing-signs.md). Read its sections 1 and 6 before you score anything.

### 7. Decide, using the rubric

**Plagiarism**

| Status | Criteria |
|---|---|
| `flagged` | At least 2 sermons each with either >= 2% of words inside exact 8+ word runs against a single source, or a non-Scripture run of >= 20 words; AND no spoken or printed attribution to that source found. `confidence: high` when attribution was checked in 3+ sermons and found absent, or when 5+ sermons exceed; `medium` when attribution was not checked or only 2 to 4 sermons exceed; `low` is not allowed for flagged - use `inconclusive`. |
| `cleared` | >= 8 sermons obtained; distinctive-phrase searches (>= 3 per sermon) found no source; any suspected source compared came back under 0.5% coverage and no non-Scripture run >= 15 words. `confidence: high` with 12+ sermons and 2+ suspected sources compared, otherwise `medium`. |
| `inconclusive` | Fewer than 8 sermons, captions unavailable, overlap that is fully attributed or entirely Scripture, or a licensed curriculum the church openly uses. Explain in `summary`. |
| `in_progress` | You are working on it right now. |

Attributed use is not plagiarism. If the pastor credits the source from the pulpit or in notes, record
`attributed_in_sermon: true` and set `cleared` (or `inconclusive` if attribution is partial), and say so
in the summary.

**AI writing**

| Status | Criteria |
|---|---|
| `flagged` | Two or more signals shifted >= 2 standard deviations toward generated text against a baseline of the same preacher, AND at least one corroborating item: published manuscripts or notes with the same signals, near-identical outline structure across many sermons, illustrations inconsistent with the preacher's known biography, or a public statement. `confidence` is `medium` unless there is an admission or documentary proof (`high`). |
| `cleared` | Baseline available, no convergent shift, 8+ recent sermons. |
| `inconclusive` | No baseline, or signals without corroboration. This will be the common outcome; that is fine. |

**Never** set `flagged` on a person from a single sermon, from Scripture overlap, or from AI-phrase counts alone.

### 8. Write it up in the record

Fill the pastor's `plagiarism` and `ai_writing` findings: `status`, `confidence`, `summary` (plain English,
name the source author), `sermons_reviewed`, `review_period`, `methods`, `sources_compared`, `evidence`
(3 to 6 strongest items with sermon URL, source, and a short excerpt or metric), `metrics` (copy the
headline numbers from `plagiarism_analysis.json`), and `reports` (paths under `research/<slug>/reports/`).
Set `last_reviewed`, `reviewed_by`, and update the church-level `summary`, `notes`, `updated_at`, `updated_by`.
Write `research/<slug>/README.md` describing what you did and what remains.

Tone: neutral and specific. "Eight of nine sermons contain unattributed verbatim passages from Alistair
Begg" is right; "the pastor is a plagiarist" is not. The site says "evidence review, not a verdict" and the
records must live up to that.

### 9. Validate, build, commit

```bash
python3 tools/validate.py <slug>
python3 tools/build.py
git checkout -b research/<slug>   # or reuse your branch
git add data/churches/<slug>.json research/<slug>
git commit -m "research(<slug>): <one-line result>"
git push -u origin research/<slug>
```

Open a pull request. Do not commit `site/data/` or `site/reports/`; CI builds and deploys them.

## Conventions that keep parallel agents from colliding

- One church per branch and pull request.
- Set `in_progress` and push before the long work starts.
- Never rewrite another church's record in your PR unless you found a factual error, and then say so in the PR.
- File names inside `research/<slug>/` come from the tools; do not rename them.
- Dates are ISO `YYYY-MM-DD`. Slugs are lowercase-hyphen. Report paths are repo-relative.

## Common mistakes

- Treating Scripture overlap as evidence. 1 Thessalonians 5:23-24 produced the single longest FBC Tucson match (42 words) and was correctly excluded.
- Guessing a pastor's name from a search snippet about a different church of the same name.
- Marking `cleared` after checking 3 sermons. That is `inconclusive`.
- Hand-editing `site/data/churches.json`.
- Committing audio files.
