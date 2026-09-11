# Tucson Sermon Integrity Map

A public map of Protestant churches in the Tucson, Arizona area that shows, for each church's preaching
pastors, whether their sermons have been reviewed for **plagiarism** (delivering another preacher's material
without credit) and for **AI-written text**, with the evidence behind every finding available for download.

Statuses: **Flagged**, **Cleared**, **Partially reviewed**, **In progress**, **Not yet reviewed**.
Every finding carries a confidence level, the method used, the sources compared, and downloadable reports.
This is an evidence review, not a verdict.

## Layout

```
data/churches/<slug>.json     one record per church (schema: data/schema/church.schema.json)
research/<slug>/              transcripts, source transcripts and generated reports for a deep dive
tools/                        Python CLI: validate, build, fetch_transcripts, transcribe_audio,
                              compare_transcripts, ai_writing_signals, new_church, geocode
site/                         static Leaflet site; site/data and site/reports are generated
AGENTS.md                     the research workflow and decision rubric (read this first)
.claude/skills/research-church  Claude Code skill: /research-church <slug>
.claude/agents/church-researcher.md  Opus subagent definition for parallel reviews
```

## Run the site locally

```bash
python3 -m pip install -r tools/requirements.txt
python3 tools/build.py
python3 -m http.server -d site 8000     # open http://localhost:8000
```

On GitHub, pushes to `main` build and deploy the site to GitHub Pages (`.github/workflows/deploy-pages.yml`;
enable Pages with source "GitHub Actions" in the repository settings). Pull requests run
`tools/validate.py` and a build.

## Research a church

Humans and agents follow the same procedure in [`AGENTS.md`](AGENTS.md). Short version:

```bash
python3 tools/new_church.py --name "..." --tradition baptist --address "..." --source "Staff page|https://..." --by "you"
python3 tools/fetch_transcripts.py --church <slug> "<youtube playlist url>"
#   ...find candidate sources in the browser, save them under research/<slug>/source_transcripts/<source>/...
python3 tools/compare_transcripts.py --church <slug> --pastor "Name"
python3 tools/ai_writing_signals.py --church <slug> --pastor "Name"
#   ...decide with the rubric, write findings into data/churches/<slug>.json...
python3 tools/validate.py && python3 tools/build.py
```

With Claude Code on your own machine (browser access available): `/research-church <slug>`.
To fan out: spawn the `church-researcher` subagent once per slug, each on its own `research/<slug>` branch.

## Coordinates

Records created without internet access have `geocode: "missing"` or `"approximate"`. Run
`python3 tools/geocode.py` on a normal connection to fill or upgrade them (Nominatim or the US Census geocoder).

## Current studies

- [`research/fbc-tucson/`](research/fbc-tucson/) - Fellowship Bible Church Tucson vs. Alistair Begg's 1 Thessalonians series (Truth For Life). Flagged, medium confidence: 8 of 9 sermons contain verbatim runs, up to 6.5% coverage, longest non-Scripture run 31 words.

## Ethics

Public sermons, public sources, reproducible tools, neutral language, and a correction path (GitHub issues)
on every church page. Attributed use is not plagiarism and is recorded as cleared.
