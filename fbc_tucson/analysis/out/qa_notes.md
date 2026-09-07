# QA notes — fact-check of analysis/report/report.html (2026-09-07)

Checked: every number and quoted passage in the rendered report against
`analysis/out/results_final.json`, `analysis/out/reviews/*.json`,
`analysis/out/alignments/`, `transcripts/*.txt`, `source_transcripts/*/*.txt`,
`playlist.json`, `plagiarism_report.md`.

## Verified correct (no action)

| Claim | Source of truth |
|---|---|
| 27% / 8,943 of 32,920 / 25% non-Scripture | `totals.paired_body_*` (27.2 / 8943 / 32920 / 25.0) |
| 0 mentions of Begg / Truth For Life / Parkside in 9 transcripts | grep; only hit is "beggars" (God's Word, 00:24:43) |
| 119 borrowed elements; 32/18/18/13/11/9/8/5/4/1 by type | Counter over the 6 paired reviews — exact match |
| "10–40% range" | body.reused_pct 10.5 … 40.4 |
| "13–43% of each Begg sermon" | source_consumption covered_pct 12.53 … 42.85 |
| "7% to 21% of the full livestream transcript" | matrix fuzzy_cov_fbc_pct 6.53 … 21.47 |
| baselines: 16.4/21.5, 2.0/4.4, 0.0/1.8 | computed; 231 Begg-self pairs, 170 FBC-vs-other |
| ρ 0.49–0.89 and all six per-sermon ρ | order_rho |
| 151 regions, 115 commentary, 36 Scripture | segments final_class (79 non_scripture + 36 mixed = 115) |
| word-weighted identity 61% | 0.6077 over the 115 commentary regions |
| longest exact run 31 words; longest region 361 words | coverage.longest_exact_run / longest_segment_tokens |
| 212 minutes; ~58 inside Begg | Σ window.minutes = 212.2; 27.2% → 57.7 |
| every Appendix A cell (body, words, reused, commentary, exact-8, of-Begg, ρ, rating) | results_final — exact |
| every profile stat block and "estimated original material" % (40/30/45/35/50/35) | reviews `original_material.estimated_share_of_sermon_pct` |
| Exhibits 1, 2, 4, 5, 6, 8 label values | results_final, all round correctly |
| named authorities Stott, Morris, Packer, Phillips, Lewis, Zinzendorf | all present in the Begg source .txt files |
| 25 playlist entries = 17 titled Sunday + 1 children's event + 7 removed; 16 without captions | playlist.json |
| Scope table title pairings (incl. Truth and Love → vol1/05, Living to Please God → vol2/01) | source_transcripts/ |
| personalisation items 1–5 (Stott, "dig up", Begg's week, Parkside→FBC, tea→coffee, cinema→movie, "wee bit over the top", devil→enemy, evening→morning, "source…Say that with me" @0:43:10, "God is for me") | reviews `personalisation_patterns` + transcript greps |
| all 18 profile side-by-side quotes | each traces to the matching review's `paraphrase_examples` (index picks in build_report.py:81-87); each FBC quote found in its caption transcript 0–8 s from the printed timestamp |
| Truth For Life terms disclaimed twice, not asserted | exec summary + Methodology |

## Detailed evidence for the flagged items

### 1. Prayers (HIGH)
All four `type: "prayer"` borrowed_elements in the corpus:
- Faith, Hope and Love 1:17:30 — **closing** prayer, "clause by clause" (~100 words).
- God's Word… Not Man's 1:30:33 — **closing** prayer, near-verbatim (~100 words), incl. "thoroughfares of our lives".
- Our Glory and Joy 0:40:36 — Begg's **opening prayer over the text**. The same review's
  `original_material` lists "Closing prayer, entirely his own" (1:08:14-1:09:55).
- Sexual Purity 1:17:14 — closing appeal; reviewer note: *"Weaker evidence on its own
  (the Pharisee is a common trope)"*.
The Faithfulness of God review: "his own closing prayer".
⇒ "four pray Begg's closing prayer" and "Four of six closing prayers follow Begg's prayer
clause by clause" are both unsupported; **two** do, a third reproduces his *opening* prayer.

### 2. Perorations (HIGH)
Firm: No Clever Tricks 1:18:13 ("no seminary can ever make a pastor"); Our Glory and Joy
1:06:27 ("The whole peroration, three questions and three answers in order, is Begg's");
The Faithfulness of God 1:13:33 ("Both sermons END on the same instruction… This is the
peroration"); Faith, Hope and Love 1:16:59 ("The sermon's closing tagline").
Not a peroration: God's Word… Not Man's ends on the borrowed closing prayer.
Weak: Sexual Purity (see above). ⇒ four, not six.

### 3. Median rating (MED)
ratings = [8, 9, 8, 9, 7, 9] → sorted 7,8,8,9,9,9 → median **8.5**.
`build_report.py:176` uses `f"{st.median(ratings):.0f}"` → prints "8".

### 4. Exhibit 6 note (MED)
`per_minute` for Faith, Hope and Love: window_min = [34.24, 78.51]; covered[] is 0 for every
minute ≤ 34; first covered minute is 35 (48 words, all Scripture). `body.outside_window_reused`
is 0 for all nine transcripts. The only out-of-band covered minutes anywhere are the *boundary*
minutes 57 (God's Word) and 43 (Faithfulness).

### 5. 361-word region (MED)
`fbc_time` 0:50:04, `final_class` "mixed", identity 0.68. Text opens
"who began a good work in you will bring it to completion… count ludri von zeninsorf…"
and runs through verse 24 / "the philips translation". Appendix B row 1 prints exactly this.
"God decided to justify you" is at 01:07:00.799 in the caption file — a different region.

### 6. Non-sermon share (MED)
1 − body.tokens/tokens: Faith Hope & Love 32.8%, Sexual Purity 37.6%, Walk of Influence 42.5%,
Our Glory 46.2%, No Clever Tricks 46.9%, Faithfulness 47.0%, God's Word 52.2%,
Your True Identity 54.7%. Report says "40–55% of each transcript" and "40% worship lyrics".

### 7. 3.5% (MED)
2,809 / 80,984 = 3.47% — the *current* pipeline's exact-8 share, computed at
`build_report.py:182`. `plagiarism_report.md` (the earlier report) states
**3,067 of 82,461 words (3.72%)**, per-sermon 2.03%–6.48%.
Note also that the earlier report found non-zero exact-8 for both controls
(Walk of Influence 0.40%, Your True Identity 0.81%) where the new pipeline reports 0.0%.

### 8. 169 vs 170 (MED)
`charts.py:260` hardcodes "(169 pairs)"; `FBC` there excludes Big Mess, so
8 × 22 − 6 = **170**, which is what the exhibit source note and the Methodology page say.

### 9. Scope arithmetic (MED/LOW)
Rows marked "— / not in local corpus": The Secret Place, Chosen and Changed,
The Inevitable Affliction, Abound in Love, About Date and Time,
Attitudes of a Healthy Church = **six**, not "five".
Title-matched rows = 8, but the first row covers two recordings (Apr 12 + Apr 19),
so **nine of the seventeen** recordings carry a Begg title; three untranscribed
recordings (not two) carry a checkable Begg title.

### 10. "thirty Begg files" (MED)
Controls page, The Walk of Influence blurb (quoted from the review):
"a direct 5-gram comparison of the sermon window (5,269 tokens) against all thirty Begg files".
The corpus is 22 files (`ls source_transcripts/*/*.txt | wc -l` = 22), and the adjacent
Your True Identity blurb says "twenty-two". The review's token count (5,269) also differs
from `window.tokens` (5,336); Your True Identity's review says 4,421 vs `window.tokens` 4,402.

### 11. Begg sermon durations (MED)
`results_final.sources[*].duration_s` is absent; the Begg .txt files carry no timestamps.
Only token counts exist (4,021–6,409 for the six paired). "Begg's 30–40 minute sermons"
has no basis in the data.

### 12. Quotation fidelity nits (LOW)
- The Faithfulness of God 1:01:01: caption reads "troubled by the **by the** memory of a
  moral lapse"; the report prints it without the stammer, under a footnote saying
  quotations are verbatim.
- Our Glory and Joy 0:59:37, Begg column: printed as "again I found John Stark **[Stott]**
  to be so helpful". The source transcript reads "John Stark"; "[Stott]" is the reviewer's
  gloss, shown inside the quotation marks.
- Appendix B identity uses `int(identity*100)` (build_report.py:439), i.e. truncation:
  0.557 → "55%" (should be 56%), 0.647 → "64%".

### 13. "one commentator" — 3 sermons (LOW)
Caption greps: "A commentator" (Faith, Hope and Love 1:00:41), "one commentator"
(No Clever Tricks 1:01:47), "commentaries" (Our Glory and Joy 0:59:26 — a plural aside,
matching Begg's "you read the commentaries…"). Three sermons keep Begg's unnamed-source
formula; only two use the literal phrase "one commentator".
Note also that Begg's *named* authority I. H. Marshall is dropped in Sexual Purity —
the "Begg's named authorities kept" row lists only the ones kept.

### 14. Intent language (MED)
Report caveat (twice): "It does not establish intent." Against that:
cover title "Borrowed Pulpit"; key finding "The reuse is systematic, not incidental";
key finding "The borrowing is **disguised** as personal"; Character page headline
"it is **re-voiced as the pastor's own**"; Exhibit 4 note "A preacher who consulted Begg
for a few ideas would produce scattered marks."
