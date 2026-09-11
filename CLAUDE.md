# Claude Code notes for this repository

Read `AGENTS.md` first. It is the standard workflow and decision rubric for researching a church, and every
record must pass `python3 tools/validate.py` before it is committed.

Quick commands:

```bash
python3 -m pip install -r tools/requirements.txt   # once
python3 tools/validate.py                          # check all records
python3 tools/build.py && python3 -m http.server -d site 8000   # preview the site at http://localhost:8000
python3 tools/new_church.py --help                 # scaffold a record
python3 tools/fetch_transcripts.py --help          # YouTube captions -> research/<slug>/transcripts
python3 tools/compare_transcripts.py --help        # exact-run comparison -> research/<slug>/reports
python3 tools/ai_writing_signals.py --help         # stylometric signals -> research/<slug>/reports
python3 tools/geocode.py --help                    # fill lat/lng (needs internet)
```

Use the `/research-church <slug or church name>` skill to run a full review with browser access on your own
machine. Subagent definition for parallel work: `.claude/agents/church-researcher.md` (Opus).

Do not edit `site/data/` or `site/reports/`; they are generated. Do not commit audio.
