# Signs of AI Writing — Reference Sheet for Sermon Review

A field guide for checking a sermon (transcript or manuscript) for indicators of
LLM-generated text. Adapted for homiletical material from Wikipedia's
[Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)
(WP:AISIGNS), retrieved 2026-09-08, with sermon-specific caveats added.

**Intended reader: a future AI agent asked to evaluate a sermon in this repo.**
Read the whole file before scoring anything. Sections 1 and 6 are not optional
preamble — they are the parts that keep this from producing false accusations.

---

## 1. Read this first: the accuracy ceiling

These are *signs*, not proof. Nothing below establishes AI authorship on its own.

- **Do not use, cite, or simulate AI-detection tools.** GPTZero, Pangram, and
  similar classifiers have non-trivial error rates and are defeated by
  paraphrase, reformatting, or any model they weren't trained on. A "94% AI"
  score is not evidence.
- **Do not trust your own gut read.** A 2025 study found humans distinguish LLM
  from human text at roughly chance. A German-thesis study found ~57% accuracy
  on AI texts, ~64% on human ones. Heavy LLM users reach ~90% — which still
  means one false positive in ten accusations.
- **The training data includes human writing.** Every pattern below appears in
  human editorials, blogs, devotionals, and — importantly here — sermons.
- **Human writing is converging with LLM writing.** Measurable LLM influence on
  human speech was already documented in 2024, including in spoken/conversational
  media. A 2026 sermon written entirely by hand will sound more like ChatGPT than
  a 2019 one did.
- **Writers adapt.** Someone who knows em dashes are "an AI tell" removes them.
  Absence of signs is weak evidence of human authorship.

**Operating rule:** report *density and co-occurrence of multiple independent
signs*, with quoted evidence, as a graded likelihood. Never as a verdict.

---

## 2. Which signs are usable on which artifact

This matters enormously and is the most common analytical error.

| Artifact | What survives | What is unusable |
|---|---|---|
| **ASR / auto-caption transcript** (e.g. YouTube captions, Whisper output) | Word choice, phrasing, rhetorical structure, argument shape | All punctuation, capitalization, em dashes, curly quotes, boldface, headings, Markdown, emoji, lists |
| **Written manuscript / handout / blog post** | Everything | — |
| **Slide deck or outline** | Structure signs, headings, formatting | Prose-level signs are thin |

> **Do not report punctuation or formatting findings from an ASR transcript.**
> The transcriber chose those characters, not the preacher. Likewise, ASR
> mis-hearings ("grace" → "grays") are not vocabulary evidence.

A further wrinkle unique to preaching: a sermon *delivered* from an AI-written
manuscript still gets ad-libbed. Expect signs to cluster in the composed
sections (introduction, points, conclusion) and thin out in illustrations,
asides, and audience interaction.

---

## 3. Content-level signs (survive speech — use these first)

These are the load-bearing indicators for transcript work.

### 3.1 Undue emphasis on significance, legacy, and broader trends
LLMs inflate importance by asserting that a detail represents or contributes to
something larger. The repertoire is narrow and recognizable.

Watch for: *stands/serves as*, *is a testament/reminder*, *a crucial / pivotal /
vital / significant / key role/moment*, *underscores/highlights its importance*,
*reflects broader*, *symbolizing its ongoing/enduring/lasting*, *contributing to
the*, *setting the stage for*, *marking/shaping the*, *represents/marks a shift*,
*key turning point*, *evolving landscape*, *focal point*, *indelible mark*,
*deeply rooted*.

Underlying mechanism: statistical regression to the mean. The model drops the
specific, rare, concrete fact and substitutes a generic superlative. Specificity
goes down while intensity goes up. In a sermon this looks like a text being
praised as "a pivotal moment in redemptive history" rather than exegeted.

### 3.2 Superficial analysis, usually via trailing "-ing" clauses
A sentence states something, then a present-participle phrase appends unearned
significance.

Watch for: *highlighting / underscoring / emphasizing …*, *ensuring …*,
*reflecting / symbolizing …*, *contributing to …*, *cultivating / fostering …*,
*encompassing …*, *enhancing …*, *valuable insights*, *align/resonate with*.

> "Paul writes from Corinth, underscoring the depth of his pastoral concern for
> the young church."

The tell is that the trailing clause adds no information and could be attached
to almost any sentence in the sermon.

### 3.3 Promotional / advertisement-like language
Watch for: *boasts a*, *vibrant*, *rich*, *profound*, *enhancing*, *showcasing*,
*exemplifies*, *commitment to*, *groundbreaking*, *renowned*, *featuring*,
*diverse array*, *nestled*, *in the heart of*.

Sermon-specific form: the biblical text, the author, or the congregation
described in brochure language — "Paul's rich and profound theology,"
"this vibrant community of believers."

### 3.4 Vague attribution and overgeneralized opinion (weasel wording)
Watch for: *scholars argue*, *many commentators note*, *experts suggest*,
*some have observed*, *theologians widely agree*, *observers have cited*,
*several sources*, *such as* before a list presented as non-exhaustive.

The tell is quantity inflation: one commentator's view presented as consensus,
or "scholars" with no scholar ever named. **This is a high-value sign for
sermons** because preachers who study normally *name* their sources ("Carson
points out…", "as Lewis put it…"), while an LLM gestures at an anonymous guild.

Cross-check: does any named authority in the sermon actually hold the view
attributed? Hallucinated attributions to real people are a strong sign.

### 3.5 Outline-like "challenges and future prospects" conclusions
The rigid formula "Despite its [positive words], X faces several challenges…"
followed by a vaguely hopeful close. In sermons this surfaces as a mechanical
application section: challenge acknowledged, encouragement offered, nothing
specific to this congregation.

The sign is the *formula*, not the mention of difficulty. Preaching about
hardship is normal; preaching about hardship in this exact shape is not.

### 3.6 Vague expression of connection
*associated with*, *connected to*, *in connection with*, *linked to* where a
direct statement would serve. "Timothy was associated with Paul's missionary
work" instead of "Timothy traveled with Paul."

### 3.7 Knowledge-cutoff and source-availability disclaimers
Watch for: *as of my last knowledge update*, *up to my last training update*,
*while specific details are limited/scarce*, *not widely documented*,
*based on available information*, *in the provided sources*.

These are near-conclusive when present in a manuscript. They should never appear
in a sermon at all.

### 3.8 Leftover chatbot conversational artifacts
*Certainly!*, *Of course!*, *I hope this helps*, *Would you like me to…*,
*Let me know if…*, *Here is a…*, *In this section we will explore…*,
*as an AI language model*.

Also: bracketed placeholder text left unfilled — `[Insert illustration here]`,
`[Church Name]`, `[personal story]`, `[Scripture reference]`. Near-conclusive.

### 3.9 Section-summary tics (historical, still worth grepping)
*In summary*, *In conclusion*, *Overall*, plus paragraphs that restate their own
opening sentence. Weaker now than in 2023 output, and note that preachers
legitimately summarize — see §6.

### 3.10 Didactic disclaimers (historical, ~2022–2024)
*It's important to note*, *it's crucial to remember*, *worth noting*, *may vary*.
Useful mainly for dating older AI-assisted material.

---

## 4. Language and grammar signs

### 4.1 High-density "AI vocabulary"
Individually these words are ordinary. **Density is the signal.** Count
occurrences per 1,000 words and compare against the same preacher's older,
pre-2023 material where available.

Empirically overused by LLMs (each attested in the cited literature):
*additionally* (esp. sentence-initial), *align with*, *boasts*, *bolstered*,
*crucial*, *deep dive*, *delve*, *emphasizing*, *enduring*, *enhance*,
*fostering*, *garner*, *highlight* (verb), *interplay*, *intricate/intricacies*,
*key* (adjective), *landscape* (abstract), *meticulous/meticulously*, *pivotal*,
*robust*, *showcase*, *tapestry* (abstract), *testament*, *underscore* (verb),
*valuable*, *vibrant*.

### 4.2 Avoidance of plain "is" / "are"
LLMs replace copulas with *serves as*, *stands as*, *functions as*, *operates
as*, *represents*, *marks*, and replace *has* with *features*, *offers*,
*boasts*, *maintains*. Also *refers to* where *is* would do. Academic use of
*is*/*are* dropped over 10% in 2023 with no prior trend.

A sermon that never simply says "Grace is…" and always says "Grace serves as…"
is worth flagging.

### 4.3 Negative parallelism
Three related shapes:

- **Not just X, but Y** — "not only … but also," "it's not just … it's …"
- **Not X, but Y** — "it's not …, it's …," "no …, no …, just …"
- **X rather than Y** — the reversal; especially characteristic of Grok.

> ⚠️ **This is the single biggest false-positive risk in sermon analysis.**
> Antithesis is a core homiletical and biblical device, and has been for two
> millennia. "Not by works, but by grace" is Ephesians. Count it only if the
> construction is used *repeatedly and without rhetorical payoff* — where the
> "not X" half is a strawman nobody was thinking, invented so the sentence can
> have a shape. See §6.

### 4.4 Rule of three
Triads: "adjective, adjective, adjective" or three short parallel phrases,
frequently used to make a superficial analysis sound comprehensive.

> ⚠️ **Second-biggest false-positive risk.** The tricolon is standard preaching
> craft; three-point sermons are a genre convention. Flag only when triads are
> ubiquitous, semantically empty (the three items are near-synonyms), or appear
> in throwaway contexts where no one would bother with a flourish.

### 4.5 Elegant variation / repetition avoidance (historical)
Older models applied repetition penalties, producing chains of synonymous
re-descriptions of one thing ("the constraints of socialist realism" → "the
challenging climate of Soviet artistic constraints" → "state-imposed artistic
norms"). Note that many non-native English speakers are taught this too.

---

## 5. Style and markup signs — **manuscript only**

Skip this entire section for ASR transcripts.

- **Markdown in a non-Markdown context** — `**bold**`, `##` headings, `*` bullets
  pasted into Word, email, or a CMS. Strong sign; chatbots default to Markdown.
- **Title Case Headings** on every point.
- **A title heading duplicating the document title.**
- **Overuse of boldface**, especially bolded lead-ins on every list item.
- **Inline-header vertical lists** — `**Term**: explanation` repeated down a page.
- **Emoji as structural formatting** (✅, 🔑, 📌 as bullets or section markers).
- **Curly quotes and apostrophes** (" " ' ') — weak alone; Word, macOS, iOS, and
  Chicago-style typesetting all produce them. Note that Gemini and Claude
  typically do *not*.
- **Em dashes** — surrounded by spaces, used where a comma or colon would serve,
  in "punched-up" sales cadence. Weakening as a sign: newer models suppress them,
  and a 2026 study found only Claude exceeds professional-writer rates while
  ChatGPT now falls below.
- **Skipped heading levels**, thematic breaks (`---`) between every section,
  tables where prose belongs.
- **Provider-specific citation artifacts** — the highest-confidence signs
  available, since they are model output leakage with no innocent explanation:
  - ChatGPT: `contentReference`, `oaicite`, `oai_citation`, `turn0search0`,
    `attributableIndex`, stray `+1`
  - Gemini: `[cite: 1]`, `[span_1](start_span)`
  - Grok: `grok_card`, `grok_render_citation_card_json`
  - DeepSeek: lenticular brackets `【】`, dagger symbols
  - Perplexity: `attached_file`, `ppl-ai-file-upload`
- **Fabricated citations** — invalid DOIs/ISBNs, dead links, book references with
  no page numbers, commentaries or articles that do not exist. Verify any
  scholarly citation in a sermon manuscript; hallucinated sources are strong
  evidence and are independently worth reporting regardless of cause.

---

## 6. False-positive traps specific to preaching

Sermons are a genre that *natively* produces many WP:AISIGNS patterns. Before
flagging anything below, ask whether the genre already explains it.

| Pattern | Why it appears innocently in sermons |
|---|---|
| Rule of three / tricolon | Three-point sermons; classical rhetoric; "faith, hope, and love" is the text |
| "Not X, but Y" antithesis | Pauline and prophetic rhetoric; central to Reformation-shaped preaching |
| Significance and legacy language | Preaching *is* an argument that this text matters eternally |
| Repetition and restatement | Oral delivery requires it; hearers cannot re-read |
| "In conclusion" / summary | Explicit signposting is good oral-communication practice |
| Elevated or formal register | Homiletical convention, not AI |
| Anonymous "scholars say" | Common shorthand in preaching to spare the congregation citations — weaker here than on Wikipedia, though still worth noting |
| Rhetorical questions, direct address | Genre-standard |
| Alliterated points | Homiletical tradition, not model output |

Also treat as **ineffective indicators** (per WP:AISIGNS), meaning do not report
them at all:

- Perfect grammar (many preachers are trained writers)
- Mixed casual/formal register
- "Bland" or "robotic" feel
- "Fancy" or academic prose generally (only the *specific* listed words correlate)
- Transition words in isolation
- Absence of citations

---

## 7. Signs pointing toward human authorship

Actively look for these; they belong in the report as counter-evidence.

- **Date.** Text demonstrably written before 2022-11-30 (ChatGPT's public launch)
  can rule out AI. For sermons, check publication/delivery date and any reuse of
  the preacher's older material.
- **Plain syntax.** Simple *is*/*has* phrases, *there is a*, *it has a*.
- **Plain word choice** where a stiffer synonym exists: *wrote* not *authored*,
  *used* not *utilized*, *tried* not *attempted*, *died* not *passed away*,
  *moved* not *relocated*.
- **Superlative or definitive claims** — *the first*, *the only*, *one of the
  best*. LLMs hedge; humans commit.
- **Hedges and intensifiers** — *very*, *perhaps*, *tends to*, *pretty much*.
- **Wordy human constructions** — *in order to*, *as a result of*, *the fact
  that*, *all of the*.
- **Local, checkable specificity** — named people in the congregation, this
  week's weather, a named local business, a story with an unglamorous ending.
  LLMs cannot supply these and they are expensive to fake.
- **Disfluency in the transcript** — self-correction, false starts, tangents,
  "where was I." Note this is evidence about *delivery*, not composition: a
  fluent preacher can ad-lib an AI-written manuscript.
- **Consistency with the preacher's own back catalogue** — stable verbal tics,
  favorite illustrations, recurring phrases across pre-2023 and post-2023
  sermons.
- **Ability to explain choices.** If the preacher can produce study notes,
  earlier drafts, or an account of why a given commentary was consulted, that is
  ordinary human process.

**Watch also for the inverse:** a pronounced, unexplained shift in style between
a preacher's pre-2023 and post-2023 material — or between their extemporaneous
speech and their composed sections — is itself a sign. So is an English-variety
mismatch (American spelling and idiom from a preacher who otherwise writes
British or Australian English; most LLMs default to American English).

---

## 8. Analysis procedure

1. **Classify the artifact.** ASR transcript, manuscript, or both. Apply §5 only
   to manuscripts. Record which sermons have which.
2. **Establish a baseline.** Where possible, gather the same preacher's material
   from before 2022-11-30. Every frequency claim should be relative to that
   baseline, or to other preachers in the corpus, not to an absolute threshold.
3. **Segment the sermon.** Introduction, exposition, illustrations, application,
   conclusion. Signs concentrated in composed sections and absent from asides is
   itself a finding.
4. **Count, don't vibe.** For §4.1 vocabulary and §4.3–4.4 constructions, produce
   per-1,000-word rates with the raw counts. Save the tally so it is reproducible.
5. **Quote every finding.** Each reported sign gets the verbatim sentence and a
   timestamp or line reference. A sign without a quote does not go in the report.
6. **Run the §6 filter.** For each finding, state explicitly whether homiletical
   convention already explains it. Drop the ones it explains.
7. **Search for §3.7, §3.8, and the §5 provider artifacts.** These are the only
   near-conclusive items. A plain grep is worth running on every file.
8. **Verify citations.** Any named scholar, commentary, statistic, quotation, or
   historical claim. Fabrication is both a strong AI sign and independently
   reportable.
9. **Collect §7 counter-evidence** with the same rigor as the positive signs.
10. **Report a graded likelihood, never a verdict.**

### Suggested reporting bands

| Band | Basis |
|---|---|
| **No indication** | No signs beyond genre-explained patterns |
| **Weak** | Scattered §3–4 signs at rates comparable to baseline; genre explains most |
| **Moderate** | Multiple independent §3–4 signs, clearly elevated over the preacher's baseline, clustered in composed sections, with §7 counter-evidence thin |
| **Strong** | The above *plus* at least one near-conclusive item: knowledge-cutoff disclaimer, chatbot artifact, unfilled placeholder, provider citation leakage, or verified fabricated sources |

State the band, the evidence, the counter-evidence, and the limits of the method
in every report. If asked for a yes/no, explain why the method does not produce one.

---

## 9. Relationship to plagiarism analysis

AI-writing signs and source-overlap findings are independent and should be
reported separately. They can also interact:

- **Elegant variation over a source** (§4.5) — a passage that tracks a source
  sermon's argument order and illustrations while systematically substituting
  synonyms is consistent with running source text through a model to paraphrase.
  Look for high structural overlap with low verbatim overlap.
- **Paraphrase defeats string matching.** Near-zero exact-match scores against a
  known source do not clear a sermon if the outline, illustration sequence, and
  argument turns line up. Consider semantic or structural comparison for those.
- **Both can be true, and neither implies the other.** A sermon can be
  AI-assisted and original, or hand-written and derivative.

---

## 10. Source

Wikipedia, *Wikipedia:Signs of AI writing* (WP:AISIGNS / WP:AITELLS), retrieved
2026-09-08. CC BY-SA 4.0. Key underlying literature cited there and relied on
above: Reinhart et al., *PNAS* 122(8) 2025 (grammatical/rhetorical style
variation); Russell, Karpinska & Iyyer, ACL 2025 (expert human detection rates);
Cheng et al., *Advances in Simulation* 10(1) 2025 (detector and human accuracy);
Fiedler & Döpke, *IREE* 49 2025 (German theses); Geng & Trotta, arXiv:2404.08627
(copula decline); Huang et al. (Wikipedia in the era of LLMs); Juzek & Ward,
arXiv:2508.01930 (word overuse); Yakura et al., arXiv:2409.01754 (LLM influence
on human speech); *The Economist*, "How to spot AI writing," 30 July 2026.

The Wikipedia page is descriptive and updated continuously. Re-check it before
relying on the model-specific details in §5, which age fastest.
