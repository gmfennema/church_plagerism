# Close-read brief (one FBC sermon)

You are an expert reviewer assessing whether a sermon preached at FBC Tucson (2026, playlist
"A Church of Irresistible Influence", 1 Thessalonians) depends on Alistair Begg's Truth For Life
1 Thessalonians series (public archive; transcripts made locally with Whisper).

Working directory: /home/user/church_plagerism/fbc_tucson

Files:
- FBC transcript (YouTube auto-captions of the WHOLE service: worship songs, announcements,
  scripture reading, sermon, closing prayer, closing song): transcripts/<fbc>.txt
  Lines look like `[h:mm:ss.mmm] text`. `>>` marks a speaker change. `[music]`/`[singing]` mark songs.
- Begg source transcript(s): source_transcripts/<volume>/<file>.txt (Whisper ASR; no timestamps).
- Machine alignment of near-verbatim regions (if any): analysis/out/alignments/<fbc>.txt
  Regions are numbered "=== Region N". Identity is a token-overlap ratio.

Read the ENTIRE FBC transcript and the ENTIRE paired Begg transcript(s) with `cat`/`sed`.
Do not skim. Then write ONE JSON file to analysis/out/reviews/<fbc_key>.json with exactly this shape:

{
  "fbc_key": "<fbc file stem>",
  "speaker_notes": "who is preaching (self-references, name if given), audience cues",
  "sermon_start": "h:mm:ss",   // first words of the sermon proper (after the scripture reading / opening ritual is fine to include; exclude songs and announcements)
  "sermon_end": "h:mm:ss",     // last words before the closing prayer ends / band starts
  "boundary_note": "how you decided",
  "passage": "e.g. 1 Thessalonians 2:1-6",
  "attribution": {
    "begg_named": false,
    "truth_for_life_named": false,
    "other_sources_named": ["e.g. 'one commentator', 'the hymnwriter', 'C.S. Lewis'"],
    "notes": "Does the preacher ever signal borrowed material (\"I read\", \"one preacher said\")? Quote exact lines with timestamps."
  },
  "outline_fbc": ["main point 1 (h:mm:ss)", "..."],
  "outline_begg": ["main point 1", "..."],
  "outline_comparison": "same skeleton / partly / different — explain in 2-4 sentences",
  "borrowed_elements": [
    {"type": "illustration|quotation|joke|application|transition|structure|commentator_quote|prayer|wordplay|exegesis",
     "fbc_time": "h:mm:ss", "fbc_excerpt": "<=60 words verbatim from captions",
     "begg_excerpt": "<=60 words verbatim from source", "note": "why this is distinctive / not Scripture / not generic"}
  ],
  "paraphrase_examples": [   // the 4-6 MOST telling NON-Scripture examples, quote-ready for a report
    {"fbc_time": "h:mm:ss", "fbc": "...", "begg": "...", "comment": "..."}
  ],
  "region_classification": {"1": "scripture", "2": "non_scripture", "3": "mixed", ...},  // every region number in the alignment file; "scripture" = the words are essentially a Bible quotation both preachers are reading
  "original_material": {
    "summary": "what the FBC preacher adds that is NOT in Begg: personal stories, local application, different points",
    "examples": ["... (h:mm:ss)"],
    "estimated_share_of_sermon_pct": 0
  },
  "personalisation_patterns": ["e.g. Begg's 'let me quote one commentator' becomes 'I like to quote from one commentator'"],
  "dependence_rating": 0,   // 0 = independent, 10 = read Begg's manuscript aloud
  "rating_rationale": "3-5 sentences",
  "report_quotes": ["1-3 short, striking side-by-side pairs formatted as 'FBC: ... | BEGG: ...'"],
  "caveats": ["caption errors, Scripture, common evangelical stock phrases, etc."]
}

Rules:
- Be precise and evidence-based; quote captions verbatim (with timestamps). Never invent text.
- Scripture read aloud by both preachers is NOT evidence of borrowing. Say so where relevant.
- Common evangelical stock phrases are weak evidence; distinctive phrasing, illustrations, jokes,
  commentator quotes, sermon structure and sequence of ideas are strong evidence.
- Also note if the FBC sermon seems to draw on any OTHER Begg sermon in source_transcripts/ (grep distinctive phrases across all of them).
- Keep your final chat reply to <=150 words: the rating, the boundaries, and the 2 most striking findings. The JSON file is the deliverable.
