# Plan: auditing the listed churches with subagents

Status as of 2026-09-11: 84 records, 78 in scope with at least one named pastor (about 130 pastors),
63 of those with a YouTube channel or playlist. One church (FBC Tucson) is reviewed. Everything else is
`unchecked`.

## Principle: split mechanical work from judgment work

The review has three very different kinds of work, and they should not share one agent:

| Phase | Nature | Bottleneck | Who does it |
|---|---|---|---|
| 1. Fetch transcripts | Mechanical I/O (`yt-dlp`, caption API) | YouTube rate limits from one IP | One throttled script, sequential |
| 2. Source hunt + compare + decide | Judgment, web-search heavy | Model cost, WebSearch quota | `church-researcher` agents, one church each, 4 to 6 at a time |
| 3. Verify flags | Adversarial re-check of evidence | Human time | Second agent per flagged pastor, then the maintainer |

Running 10 agents that all call `fetch_transcripts.py` at once from one machine will get the IP blocked
by YouTube's caption endpoint and waste the run. Fetch first, fan out second.

## Phase 0: pilot (3 churches, one batch)

Pick three churches that differ in shape so the agent prompt gets tested on each case:

- single pastor, YouTube channel, many videos (e.g. `casas-church`, `tucson-bible-church`)
- multiple preaching pastors (e.g. `catalina-foothills-church`, `christ-community-church-tucson`)
- liturgical tradition with short homilies (e.g. `grace-st-pauls-episcopal`, `st-philips-in-the-hills`)

Run Phase 1 and Phase 2 for these only. Read the three README files and the statuses set. Fix the agent
prompt and any tool bugs before scaling. Expect the pilot to surface: preacher-to-video mapping problems,
churches whose "sermon" videos are full services, and Scripture-dominated matches.

## Phase 1: transcript sweep (script, not agents)

Add `tools/fetch_all.py` (maintainer tool) that loops over in-scope records with a `youtube.channel_url`
or playlist, runs `fetch_transcripts.py --limit 30` per church with a sleep between churches, skips churches
that already have transcripts, and writes a one-line-per-church summary: videos found, captions obtained,
captions disabled. Run it in the background; it will take hours, not minutes.

Output of this phase decides the fan-out list:

- 8 or more transcripts: eligible for a full review.
- 1 to 7 transcripts: eligible only with `--audio-fallback` plus Whisper. Install `faster-whisper` first
  (it is not installed on this machine yet). Queue these after the easy ones.
- 0 transcripts or no YouTube (15 churches): send to a cheap "media discovery" agent instead (see Phase 4).

## Phase 2: fan-out of `church-researcher` agents

One church per agent, batches of 4 to 6 concurrent agents, next batch when the previous finishes.
Each agent gets a prompt of this form:

```
Review church <slug> following AGENTS.md. Transcripts are already in research/<slug>/transcripts;
do NOT re-run fetch_transcripts.py unless a pastor has fewer than 8 and --audio-fallback is needed.
Map each transcript to its preacher. Do the source hunt, collect source transcripts, run
compare_transcripts.py and ai_writing_signals.py per pastor, decide with the rubric, write findings,
validate, commit on branch research/<slug>. Do not touch any other church's files.
Report back: status per pastor with the rubric line, sermon count, sources compared, top 3 evidence
items, and anything a human must double-check.
```

Isolation: launch each agent with `isolation: "worktree"` so that several agents doing
`git checkout -b research/<slug>` never fight over one working tree. Each church touches only
`data/churches/<slug>.json` and `research/<slug>/`, so the branches merge cleanly.

Ordering inside the fan-out: churches with the most transcripts and a single preacher first (fastest,
cleanest results), then multi-pastor churches, then audio-fallback churches last.

Shared source corpus: any source transcripts an agent collects (Begg, Piper, Keller, MacArthur series) are
worth keeping for reuse. After each batch, copy new `source_transcripts/<source-slug>/` folders into
`research/_sources/` so later agents can run a cheap all-against-known-sources comparison before the
expensive phrase-by-phrase web hunt.

Cheap triage that should run before the web hunt in every agent: compare the church's sermon series titles
and per-sermon titles against the big libraries' series titles. That one check caught FBC Tucson.

## Phase 3: verification before anything is published

- Any `flagged` result gets a second, independent agent whose only job is to attack the finding: re-read the
  matched passages, confirm they are not Scripture, liturgy, a hymn, or a shared public-domain source,
  and check attribution in the opening and closing minutes of the sermons (transcripts, notes, bulletin).
- The maintainer reads every flagged report by hand before merge. `cleared` and `inconclusive` PRs can be
  reviewed from the agent summary plus `python3 tools/validate.py`.
- Merge one PR per church. Never batch-merge flags.

## Phase 4: the churches without usable YouTube

15 in-scope churches have pastors but no YouTube link; 5 more have no pastor named. These need a different,
cheaper agent pass (Explore or general-purpose, not the full researcher): find the sermon media source
(website audio, podcast feed, Facebook video, Vimeo), confirm the preaching pastor from the staff page,
and update the record's `youtube` / `other_media` / `pastors` fields. Do not attempt a review in this pass.
Churches with no discoverable sermon media get `inconclusive` with the reason, so nobody repeats the work.

## Coordination choice: git branches vs the Convex lease API

AGENTS.md prefers the Convex task/lease API for independent agents. For agents launched from this machine
by the maintainer, the git-branch path is simpler and explicitly supported. Two practical facts:

- Reading the agent secret from Keychain was blocked by the auto-mode permission classifier in this
  session. Agents will hit the same block unless the maintainer exports `SERMON_API_TOKEN` into the
  environment before launching, or adds a Bash permission rule for `security find-generic-password`.
- With one orchestrator assigning slugs deterministically, the lease adds no collision protection.

Recommendation: run the first batches on the git path with worktree isolation. Move to the Convex submission
flow once it is confirmed the task table is seeded and the token is reachable from an agent shell.

## Rough budget

- Phase 1: a few hours of wall clock, no model cost.
- Phase 2: each full review is a long Opus run (FBC took a full working session). 63 churches at 5 concurrent
  is roughly 13 batches. Plan for several days of background runs, not one afternoon.
- The web hunt dominates cost: 3 to 5 searches per sermon, 8+ sermons per pastor. The series-title triage
  and the shared source corpus are what make this affordable.

## Definition of done for this round

Every in-scope pastor has a status other than `unchecked`, every `flagged` has passed Phase 3, and
`python3 tools/validate.py` passes on main.
