# Tucson Sermon Review

A public map of Protestant churches in the Tucson, Arizona area that shows, for each church's preaching
pastors, whether their sermons have been reviewed for **plagiarism** (delivering another preacher's material
without credit) and for **AI-written text**, with the evidence behind every finding available for download.

Public outcomes are shown separately for **text-source reuse** and **AI-writing indicators**. The site uses
plain-language outcomes—**evidence threshold met**, **no concern found**, **inconclusive**, and **not reviewed**—instead
of a letter grade or an invented probability. Every substantive finding carries a separate confidence level,
methods, compared sources, short evidence receipts, and downloadable reports. This is an evidence review, not a verdict.

Parallel research is coordinated through a Convex API. Agents claim leased tasks, upload transcripts/reports,
and submit standardized proposals. A human review gate is required before a proposal changes the public site.

## Layout

```
data/churches/<slug>.json     one record per church (schema: data/schema/church.schema.json)
research/<slug>/              transcripts, source transcripts and generated reports for a deep dive
convex/                       database schema, task leases, storage, submissions and approval workflow
docs/agent-api.md             agent workflow, authentication and endpoint examples
docs/submission.schema.json   machine-readable submission contract
tools/                        Python CLI: validate, build, fetch_transcripts, transcribe_audio,
                              compare_transcripts, ai_writing_signals, new_church, geocode
site/                         static Leaflet site; site/data and site/reports are generated
AGENTS.md                     the research workflow and decision rubric (read this first)
docs/ai-writing-signs.md      field guide for reading AI-writing signals in a sermon
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

The public site reads approved data from `https://resilient-anteater-921.convex.site` and falls back to the
generated JSON snapshot if the API is unavailable.

## Research API

The production API and database are deployed in the Convex project `tucson-sermon-integrity`. On this Mac,
agent and admin secrets live in Keychain under `tucson-sermon-integrity-agent-prod` and
`tucson-sermon-integrity-admin-prod`; secrets are never stored in Git. See [`docs/agent-api.md`](docs/agent-api.md)
for the complete claim → upload → submit → review flow.

To validate backend code against the development deployment:

```bash
npm install
npx convex dev --once
```

The initial Convex import contains 82 in-scope churches, 127 pastors, and 116 active-pastor research tasks.

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

- [`research/fbc-tucson/`](research/fbc-tucson/) - Fellowship Bible Church Tucson vs. Alistair Begg's 1 Thessalonians series (Truth For Life). Flagged, high confidence: six sermons by Pat McClanahan contain 10% to 40% sermon-body overlap (27.2% overall; 25.0% after shared Scripture), with no attribution to Begg or Truth For Life found in the six transcripts.

## Ethics

Public sermons, public sources, reproducible tools, neutral language, and a correction path (GitHub issues)
on every church page. Attributed use is not plagiarism and is recorded as cleared.
