# Research agent API

The API is the coordination and submission layer for parallel sermon research. Agents claim a task, do the CPU- and browser-heavy work locally, upload durable artifacts, and submit a structured proposal. Submissions are private until an administrator approves them.

## Connection

- Production base URL: `https://resilient-anteater-921.convex.site`
- Authentication: `Authorization: Bearer <agent-id>:<secret>`
- On this Mac, the production research secret is stored in Keychain under `tucson-sermon-integrity-agent-prod`.
- The machine-readable submission contract is [`submission.schema.json`](submission.schema.json).

An agent can prepare its environment without printing the secret:

```bash
export SERMON_API_URL=https://resilient-anteater-921.convex.site
export SERMON_API_TOKEN="research-agent:$(security find-generic-password -w -s tucson-sermon-integrity-agent-prod)"
```

Never commit or paste the token into a research report.

## Workflow

### 1. Find and claim work

```bash
curl -sS -H "Authorization: Bearer $SERMON_API_TOKEN" \
  "$SERMON_API_URL/api/v1/tasks?limit=20"

curl -sS -X POST \
  -H "Authorization: Bearer $SERMON_API_TOKEN" \
  -H "Content-Type: application/json" \
  "$SERMON_API_URL/api/v1/tasks/claim" \
  -d '{"task_id":"<task id>","lease_minutes":120}'
```

A lease replaces the old `in_progress` Git commit used to prevent two agents from researching the same pastor. Finish or submit within the lease. A future version will add heartbeat and release endpoints; for now, reclaiming the same task renews the lease.

### 2. Upload transcripts and reports

Ask for an upload URL, then send the file directly to it. The upload response contains a `storageId`; include that ID in the final submission.

```bash
UPLOAD_URL=$(curl -sS -X POST \
  -H "Authorization: Bearer $SERMON_API_TOKEN" \
  "$SERMON_API_URL/api/v1/uploads" | python3 -c 'import json,sys; print(json.load(sys.stdin)["uploadUrl"])')

curl -sS -X POST -H "Content-Type: text/plain" \
  --data-binary @research/example/transcripts/sermon.txt "$UPLOAD_URL"
```

Upload full transcripts and machine-readable reports. Do not place full transcript text in the JSON submission. Audio is not uploaded by default.

### 3. Submit one finding per check

Submit plagiarism and AI-writing findings separately, even when the task scope is `both`. Use a globally unique `submission_key`; retrying the same key returns the original submission instead of creating a duplicate.

```bash
curl -sS -X POST \
  -H "Authorization: Bearer $SERMON_API_TOKEN" \
  -H "Content-Type: application/json" \
  "$SERMON_API_URL/api/v1/submissions" \
  --data-binary @finding.json
```

Example `finding.json`:

```json
{
  "schema_version": "1.0",
  "rubric_version": "2026-09-10",
  "submission_key": "agent-run-20260910-fbc-plagiarism-v1",
  "task_id": "<claimed task id>",
  "church_slug": "fbc-tucson",
  "pastor_name": "Pat McClanahan",
  "pastor_role": "Senior Pastor",
  "finding": {
    "kind": "plagiarism",
    "status": "flagged",
    "confidence": "medium",
    "summary": "Eight of nine reviewed sermons contained qualifying exact overlap with Alistair Begg material. Spoken or printed attribution has not yet been verified.",
    "sermons_reviewed": 9,
    "methods": ["ngram_exact_run_comparison", "manual_side_by_side"],
    "metrics": {
      "sermons_with_matches": 8,
      "max_sermon_coverage_pct": 6.48,
      "longest_non_scripture_run_words": 31
    }
  },
  "review_period": { "from": "2026-04-19", "to": "2026-08-01" },
  "sources_compared": [
    {
      "author": "Alistair Begg",
      "title": "A Study in 1 Thessalonians",
      "url": "https://www.truthforlife.org/",
      "attributed_in_sermon": null
    }
  ],
  "evidence": [
    {
      "type": "verbatim_overlap",
      "description": "A 31-word non-Scripture run appears in both sermons.",
      "sermon_title": "No Clever Tricks",
      "sermon_url": "https://www.youtube.com/watch?v=example",
      "sermon_excerpt": "Short excerpt from the local sermon.",
      "source_author": "Alistair Begg",
      "source_title": "No Clever Tricks",
      "source_excerpt": "Short excerpt from the compared source.",
      "matched_words": 31,
      "scripture_excluded": false,
      "attribution_status": "not_checked"
    },
    {
      "type": "verbatim_overlap",
      "description": "A second qualifying non-Scripture overlap appears in another sermon.",
      "sermon_title": "Our Glory and Joy",
      "matched_words": 25,
      "scripture_excluded": false,
      "attribution_status": "not_checked"
    }
  ],
  "artifacts": [
    {
      "storage_id": "<storage id returned by the upload>",
      "kind": "comparison_report",
      "file_name": "plagiarism_analysis.json",
      "content_type": "application/json"
    }
  ],
  "attestation": {
    "rubric_reviewed": true,
    "scripture_liturgy_exclusions_reviewed": true
  },
  "notes": "Private note for the reviewer."
}
```

### 4. Check review status

```bash
curl -sS -H "Authorization: Bearer $SERMON_API_TOKEN" \
  "$SERMON_API_URL/api/v1/submissions/status?id=<submission id>"
```

Statuses are `pending`, `approved`, `changes_requested`, or `rejected`. Approval is the only operation that updates the public church record.

## Server-enforced guardrails

- Final proposals may be `cleared`, `flagged`, or `inconclusive`; workflow states do not belong in a published finding.
- `cleared` or `flagged` requires a confidence level.
- `flagged` cannot use low confidence.
- A plagiarism clearance needs at least eight sermons.
- A plagiarism flag needs at least two reviewed sermons and two non-Scripture evidence items with at least 20 matched words.
- An AI-writing flag needs at least two stylometric-shift items plus corroborating evidence.
- Both rubric attestations are required.
- JSON requests are capped at 500 KB. Full transcripts belong in file storage.

These checks catch structurally invalid proposals. The reviewer still applies the full rubric in [`../AGENTS.md`](../AGENTS.md).

## Administrator endpoints

Admin authentication uses `Authorization: Bearer admin:<secret>`. The production secret is in Keychain under `tucson-sermon-integrity-admin-prod`.

- `POST /api/v1/admin/tasks` — add an idempotent task using `task_key`.
- `GET /api/v1/admin/submissions?status=pending` — list the review queue.
- `POST /api/v1/admin/reviews` — decide a submission with `submission_id`, `decision`, optional `reviewer`, and optional `notes`.
- `POST /api/v1/admin/import-church` — idempotently import a legacy church snapshot.

Do not expose the admin key in a browser-based admin screen. Until human login is added, review from a trusted local terminal.
