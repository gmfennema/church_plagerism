"""Assemble the PDF report from results_final.json, the reviewer JSON files and the exhibits."""
from __future__ import annotations

import html
import json
import subprocess
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
REP = HERE / "report"
REP.mkdir(exist_ok=True)
R = json.load(open(OUT / "results_final.json"))
FBC = [r for r in R["fbc"] if r["title"] != "Big Mess"]
PAIRED = [r for r in FBC if r["paired_sources"]]
CTRL = [r for r in FBC if not r["paired_sources"]]
BIGMESS = next(r for r in R["fbc"] if r["title"] == "Big Mess")
SRC = {s["key"]: s for s in R["sources"]}
T = R["totals"]
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

DATE = "September 7, 2026"


def e(s):
    return html.escape(str(s))


def fmt_date(d):
    m = {"04": "April", "05": "May", "06": "June", "07": "July", "08": "August"}
    return f"{m[d[5:7]]} {int(d[8:])}, {d[:4]}"


def svg(name):
    return (OUT / "figures" / f"{name}.svg").read_text()


def fig(name, cls=""):
    s = svg(name)
    # strip fixed width/height so CSS controls size
    import re
    s = re.sub(r'<svg([^>]*?)\swidth="[^"]*"', r"<svg\1", s, count=1)
    s = re.sub(r'<svg([^>]*?)\sheight="[^"]*"', r"<svg\1", s, count=1)
    return f'<div class="fig {cls}">{s}</div>'


# ---------------------------------------------------------------- derived numbers
body_tok = sum(r["body"]["tokens"] for r in PAIRED)
reused = sum(r["body"]["reused_tokens"] for r in PAIRED)
nonscr = sum(r["body"]["nonscripture_tokens"] for r in PAIRED)
scr = sum(r["body"]["scripture_tokens"] for r in PAIRED)
pct_reused = 100 * reused / body_tok
pct_nonscr = 100 * nonscr / body_tok
ratings = [r["rating"] for r in PAIRED]
regions = sum(len(r["segments"]) for r in PAIRED)
regions_ns = sum(1 for r in PAIRED for s in r["segments"] if s["final_class"] != "scripture")
longest_ns = max(s["fbc_len"] for r in PAIRED for s in r["segments"] if s["final_class"] != "scripture")
longest_exact = max(r["coverage"]["longest_exact_run"] for r in PAIRED)
begg_self = [p["fuzzy_cov_pct"] for p in R["baselines"]["begg_self_pairs"]]
unpaired = [R["matrix"][f"{r['key']}||{s}"]["fuzzy_cov_fbc_pct"] for r in FBC for s in SRC if s not in r["paired_sources"]]
paired_whole = [R["matrix"][f"{r['key']}||{r['paired_sources'][0]}"]["fuzzy_cov_fbc_pct"] for r in PAIRED]
import statistics as st
borrowed = Counter()
n_borrowed = 0
for r in PAIRED:
    for b in r["review"]["borrowed_elements"]:
        borrowed[b["type"]] += 1
        n_borrowed += 1
attrib_named = sum(1 for r in PAIRED if r["review"]["attribution"]["begg_named"] or r["review"]["attribution"]["truth_for_life_named"])
exact8_all = sum(r["coverage"]["exact8_tokens"] for r in R["fbc"])
minutes_paired = sum(r["window"]["minutes"] for r in PAIRED)
minutes_reused = sum(r["window"]["minutes"] * r["body"]["reused_pct"] / 100 for r in PAIRED)


def rng(vals, f="{:.0f}%"):
    return f"{f.format(min(vals))} to {f.format(max(vals))}".replace("%% to", "% to")


# ---------------------------------------------------------------- side-by-side picks
PICKS = {
    "Faith, Hope and Love": [0, 4, 5],
    "No Clever Tricks": [0, 1, 5],
    "God's Word... Not Man's": [0, 1, 5],
    "Our Glory and Joy": [0, 2, 5],
    "Sexual Purity": [0, 1, 5],
    "The Faithfulness of God": [0, 1, 5],
}
SOURCE_NOTE = {
    "Faith, Hope and Love": ("Volume 1, “Faith, Hope and Love”", "1 Thessalonians 1:1-3"),
    "No Clever Tricks": ("Volume 1, “No Clever Tricks”", "1 Thessalonians 2:1-8"),
    "God's Word... Not Man's": ("Volume 1, “The Word of God, Not Men”", "1 Thessalonians 2:13-16"),
    "Our Glory and Joy": ("Volume 1, “Our Glory and Joy”", "1 Thessalonians 2:17-20"),
    "Sexual Purity": ("Volume 2, “Sexual Purity, Part One” (with Part Two)", "1 Thessalonians 4:1-8"),
    "The Faithfulness of God": ("Volume 3, “The Faithfulness of God”", "1 Thessalonians 5:23-24"),
}
PROFILE_LEAD = {
    "Faith, Hope and Love": "From verse 1 onward the sermon is Begg’s exposition re-delivered: the same headings, the same anonymous commentator, the same Pennsylvania etymology, the same closing tagline and a closing prayer that follows Begg’s clause by clause. Begg’s 25-minute Acts background is dropped and replaced with a 2026 Barna survey opener.",
    "No Clever Tricks": "The closest tracking in the series. The sermon follows Begg from its first sentence (“Romans reveals his mind, 1 Thessalonians reveals his heart”) to its peroration (“no seminary can ever make a pastor … only God can do that”) without leaving his sequence, reproducing even Begg’s act of quoting an unnamed commentator and his dating aside.",
    "God's Word... Not Man's": "Begg’s alliterated four-P outline (Process, Product, Persecution, Pronouncement) arrives with three headings word-for-word and the fourth renamed. The Leon Morris quotation, the “imitate Parkside Church” application with its four-item list, and the closing prayer all transfer. The preacher’s own contribution is a 13-minute expansion of Begg’s two-sentence point about a praying congregation.",
    "Our Glory and Joy": "Begg’s “source, force and course” outline, his opening prayer over the text, his Greek word study, his commentaries aside, his only named authority (John Stott, with Begg’s words of introduction) and his three-question peroration are all present in Begg’s order. The FBC additions are illustrations and call-and-response.",
    "Sexual Purity": "The lowest token overlap in the series, but the reviewer judged the machine figure a floor: the sermon’s organising device, reading 1 Thessalonians 4:3-8 as one half of a conversation, is Begg’s, run with the same objections in the same order for about twenty minutes. Roughly half the clock is genuinely the preacher’s own autobiography and dating counsel.",
    "The Faithfulness of God": "A re-preached manuscript: the hapax word study and Thessalonian tombstones, the pivot to Romans 8, the Westminster Confession line, the Packer list and the final take-home (“carve that into your mind … God is for me”) all arrive in order. Begg’s first-person confession about his own week is preached as the FBC pastor’s own.",
}

# ---------------------------------------------------------------- HTML pieces
CSS = (HERE / "report" / "report.css").read_text() if (HERE / "report" / "report.css").exists() else ""


def page(body, section="", num=None, cls=""):
    return f'''<section class="page {cls}">
  <header class="ph"><span class="ph-left">FBC Tucson × Alistair Begg · Sermon dependence review</span><span class="ph-right">{e(section)}</span></header>
  {body}
  <footer class="pf"><span>Prepared {DATE} · Private research review. Evidence of textual dependence, not a legal or ecclesiastical verdict.</span><span class="pnum"></span></footer>
</section>'''


def stat(value, label, sub=""):
    return f'<div class="stat"><div class="v">{value}</div><div class="l">{e(label)}</div>{f"<div class=s>{e(sub)}</div>" if sub else ""}</div>'


def exhibit(n, title, figname, source, cls="", note=""):
    return f'''<div class="exhibit {cls}">
  <div class="ex-head"><span class="ex-num">Exhibit {n}</span><h3>{title}</h3></div>
  {fig(figname)}
  {f'<p class="ex-note">{note}</p>' if note else ''}
  <p class="ex-src">{source}</p>
</div>'''


def sbs(fbc_time, fbc, begg, comment=""):
    return f'''<div class="sbs">
  <div class="col fbc"><div class="who">FBC Tucson <span class="t">{e(fbc_time)}</span></div><p>“{e(fbc)}”</p></div>
  <div class="col begg"><div class="who">Alistair Begg</div><p>“{e(begg)}”</p></div>
  {f'<div class="cmt">{e(comment)}</div>' if comment else ''}
</div>'''


def trunc(s, n):
    s = s.strip()
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(" ", 1)[0]
    return cut.rstrip(",;:") + " …"


pages = []

# ---------------------------------------------------------------- cover
pages.append(f'''<section class="page cover">
  <div class="cover-band"></div>
  <div class="cover-body">
    <div class="kicker">Sermon dependence review · Private research</div>
    <h1>Borrowed Pulpit</h1>
    <h2>How closely FBC Tucson’s 2026 “A Church of Irresistible Influence” series tracks Alistair Begg’s <em>A Study in 1 Thessalonians</em></h2>
    <div class="cover-stats">
      {stat(f"{pct_reused:.0f}%", "of the senior pastor’s sermon words sit inside near-verbatim Begg passages", "six sermons in the 1 Thessalonians series, sermon body only")}
      {stat("6 of 6", "sermons by the senior pastor map one-to-one onto a same-titled Begg sermon", "the two sermons by other preachers: 0%")}
      {stat("0", "mentions of Alistair Begg or Truth For Life in any of the nine transcripts", "119 borrowed non-Scripture elements catalogued")}
    </div>
    <div class="cover-meta">
      <div><span>Prepared</span>{DATE}</div>
      <div><span>Corpus</span>9 FBC Tucson livestream captions · 22 Truth For Life sermon transcripts</div>
      <div><span>Method</span>Fuzzy sequence alignment + independent full-transcript close reading</div>
    </div>
  </div>
</section>''')

# ---------------------------------------------------------------- executive summary
pages.append(page(f'''
<h1 class="title">Executive summary</h1>
<p class="lede">Six of the nine FBC Tucson recordings are sermons by the senior pastor (“Pastor Pat”) in a 1 Thessalonians series. Each one is a re-delivery of Alistair Begg’s sermon on the same passage, usually under Begg’s own title, with about a quarter of the sermon’s words falling inside near-verbatim Begg passages and the outline, illustrations, commentator quotations, closing lines and even closing prayers carried across. The two sermons preached by other FBC staff on the same book show no Begg material at all.</p>
<div class="stats4">
  {stat(f"{pct_reused:.0f}%", "of sermon-body words in reused regions", f"{reused:,} of {body_tok:,} words; {pct_nonscr:.0f}% after removing Scripture both men read")}
  {stat(f"{min(r['body']['reused_pct'] for r in PAIRED):.0f}–{max(r['body']['reused_pct'] for r in PAIRED):.0f}%", "range across the six sermons", "Sexual Purity lowest; No Clever Tricks highest")}
  {stat(f"{st.median(ratings):g}/10", "median reviewer dependence rating", "0 = independent, 10 = read aloud. Range 7–9; controls 0")}
  {stat(f"{min(s['covered_pct'] for r in PAIRED for s in r['source_consumption'][:1]):.0f}–{max(s['covered_pct'] for r in PAIRED for s in r['source_consumption'][:1]):.0f}%", "of each Begg sermon reappears in the FBC version", f"Begg’s {min(s['tokens'] for s in SRC.values() if any(s['key'] in r['paired_sources'] for r in PAIRED)):,}–{max(s['tokens'] for s in SRC.values() if any(s['key'] in r['paired_sources'] for r in PAIRED)):,}-word sermons feed FBC sermon bodies of {min(r['body']['tokens'] for r in PAIRED):,}–{max(r['body']['tokens'] for r in PAIRED):,} words")}
</div>
<h2>Key findings</h2>
<ol class="findings">
  <li><b>The pattern is consistent across all six sermons.</b> Every one of the senior pastor’s six sermons pairs with exactly one Begg sermon, the one on the same verses, and with none of the other 21. Overlap with the paired sermon runs {rng(paired_whole)} of the full livestream transcript against a ceiling of {max(unpaired):.1f}% for any non-paired Begg sermon and {max(begg_self):.1f}% for Begg reusing his own material across his own series (Exhibits 2 and 3).</li>
  <li><b>The earlier report understated it by roughly seven-fold.</b> Counting only exact eight-word runs, and dividing by whole-service transcripts of which a third to a half is songs and announcements, gave 3.7%. Aligning near-verbatim passages that caption errors and light paraphrase had broken, and measuring against the sermon itself, gives {pct_reused:.0f}% (Exhibit 1).</li>
  <li><b>Begg’s outline is the sermon’s skeleton.</b> In all six sermons the reused passages march through Begg’s sermon in order (rank correlation {min(r['order_rho'] for r in PAIRED):.2f} to {max(r['order_rho'] for r in PAIRED):.2f}), and the reviewer found the same headings, the same sequence of proof texts and the same closing lines in every pair (Exhibit 4).</li>
  <li><b>What travels is the distinctive material.</b> The reviewer catalogued {n_borrowed} borrowed non-Scripture elements: {borrowed['illustration']} illustrations, {borrowed['commentator_quote']} commentator quotations, {borrowed['prayer']} prayers, {borrowed['wordplay']} wordplays and {borrowed['structure']} structural devices among them. Four end on Begg’s closing line or peroration and a fifth on his closing prayer; two pray Begg’s closing prayer clause by clause and a third opens with his prayer over the text.</li>
  <li><b>The borrowing is presented as personal.</b> Begg’s “I found John Stott to be so helpful” becomes “I found John Stott, a great theologian, so helpful”; Begg’s confession about his own week is preached as the FBC pastor’s own week; “Parkside Church” becomes “FBC”; British tea becomes American coffee. Begg himself is never named.</li>
  <li><b>The pattern is specific to one preacher.</b> Pastor Kevin’s “The Walk of Influence” and an associate’s “Your True Identity”, on the same book in the same series, share only Scripture with Begg. They serve as the study’s natural control.</li>
</ol>
<div class="callout"><b>What this review is and is not.</b> It establishes textual dependence from transcripts: what was said, in what order, and whether a source was named. It does not establish intent, and it does not assess whether Truth For Life’s usage terms permit re-preaching; those terms were not reviewed. Both transcripts are machine-generated, so word-level figures are floors rather than ceilings.</div>
''', "Executive summary"))

# ---------------------------------------------------------------- Exhibit 1 page
pages.append(page(f'''
<h1 class="title">A tenth to two-fifths of each of the senior pastor’s sermons is Begg, near-verbatim</h1>
{exhibit(1, "Share of sermon-body words inside a reused Begg region, by sermon (chronological)", "ex1_coverage",
  "Source: YouTube auto-captions of FBC Tucson livestreams; Whisper transcripts of Truth For Life audio. Sermon body = reviewer-marked start and end of the sermon proper (excludes songs, announcements, altar call). Reused region = chain of exact 4-word seeds re-scored by token alignment, ≥12 words, ≥45% identity. Scripture classification by reviewer, region by region.")}
<div class="two-col">
<div>
<h2>Reading the exhibit</h2>
<p>The blue bar is commentary: Begg’s own sentences, illustrations and applications reappearing in the FBC sermon. The orange segment is Bible text that both men read aloud from the same translation and is not evidence of anything. The dark tick marks what the earlier report’s method would credit: only unbroken eight-word exact runs.</p>
<p>The two sermons by other FBC preachers register nothing. Their transcripts were scanned against all 22 Begg sermons with the same detector; the reviewers’ independent n-gram sweeps found only Scripture.</p>
</div>
<div>
<h2>Why the earlier figure was low</h2>
<ul>
<li><b>Wrong denominator.</b> The captions cover the whole service. Songs, announcements and the altar call are 33–55% of each transcript and contain no Begg.</li>
<li><b>Brittle detector.</b> Exact runs break at every caption error (“John Stodd” for Stott, “thorough affairs” for thoroughfares) and every Americanisation (“tea” to “coffee”). Word-weighted identity inside reused regions averages 61%, so most borrowed passages never form an eight-word exact run.</li>
<li><b>Still a floor.</b> Reviewers flagged whole borrowed paragraphs the aligner missed (e.g. the “speaking freely, openly, fearlessly” word study in No Clever Tricks) and structural borrowing it cannot see (the 20-minute dialogue device in Sexual Purity).</li>
</ul>
</div>
</div>
''', "Findings · Extent"))

# ---------------------------------------------------------------- Exhibit 2 + 6
pages.append(page(f'''
<h1 class="title">Each sermon maps onto exactly one Begg sermon, at three to ten times any natural overlap</h1>
{exhibit(2, "Reused-region coverage of each FBC transcript against all 22 Begg sermons", "ex2_heatmap",
  "Source: as Exhibit 1. Cell value is the share of the full FBC transcript (not just the sermon body) inside a reused region with that Begg sermon; cells ≥3% labelled. Volume 1 covers 1 Thess. 1–2, Volume 2 covers 4–5, Volume 3 (“Reminders for the Local Church”) covers 5:12–28.")}
{exhibit(3, "Natural overlap between preachers on the same book is small; the paired sermons are not", "ex6_baselines",
  f"Source: as Exhibit 1, whole-transcript basis for comparability. Begg-vs-Begg: all {len(begg_self)} pairs of his own 1 Thessalonians sermons, capturing a preacher’s normal self-repetition. FBC-vs-other: the {len(unpaired)} FBC/Begg pairs that are not the same passage.")}
<p class="body-note">Two things stand out in the heat map. First, the diagonal: each FBC sermon lights up only the Begg sermon on its own verses. The faint cells elsewhere (1–2%) are Begg quoting the same benediction across his series, or shared Bible readings. Second, the rows for Your True Identity and The Walk of Influence are as faint as any non-paired cell even though Begg preached the same passages (Volume 2, Parts 1–3; Volume 3, tracks 1–9). Two men preaching the same verses independently produce about what those rows show, which is the baseline the six paired sermons exceed three- to ten-fold.</p>
''', "Findings · Specificity"))

# ---------------------------------------------------------------- Exhibit 4 + 5
pages.append(page(f'''
<h1 class="title">The sermons follow Begg’s outline from beginning to end, consuming up to 43% of his text</h1>
{exhibit(4, "Where each reused passage sits in the FBC sermon (x) and in Begg’s sermon (y)", "ex4_dotplots",
  "Source: as Exhibit 1. Each mark is one reused region, drawn from its start to its end; blue = commentary, orange = shared Scripture. A mark on the diagonal means the passage occurs at the same relative point in both sermons. ρ = Spearman rank correlation of positions.", cls="tall")}
<p class="body-note">A preacher who consulted Begg for a few ideas would produce scattered marks. Instead the marks form staircases: the FBC sermon proceeds through Begg’s sermon in Begg’s order, and the flat stretches are the pastor’s own insertions (a Mother’s Day frame, a Barna survey, a 13-minute prayer appeal) between Begg’s points. Above the diagonal (Faith, Hope and Love) he skipped Begg’s opening; below it (Sexual Purity) he added a long opening of his own before joining Begg’s text.</p>
{exhibit(5, "Share of each Begg sermon’s words that reappear near-verbatim in the FBC sermon", "ex5_consumption",
  "Source: as Exhibit 1, source-side coverage. Begg’s paired sermons are {min(s['tokens'] for s in SRC.values() if any(s['key'] in r['paired_sources'] for r in PAIRED)):,}–{max(s['tokens'] for s in SRC.values() if any(s['key'] in r['paired_sources'] for r in PAIRED)):,} words; the FBC sermon bodies are {min(r['body']['tokens'] for r in PAIRED):,}–{max(r['body']['tokens'] for r in PAIRED):,} words.")}
''', "Findings · Structure"))

# ---------------------------------------------------------------- Exhibit 3 timelines + 7
pages.append(page(f'''
<h1 class="title">The reuse is spread through the whole sermon and delivered as light paraphrase</h1>
{exhibit(6, "Minute-by-minute share of words inside a reused region, across each livestream", "ex3_timelines",
  "Source: as Exhibit 1. Shaded band marks the reviewer’s sermon start and end.", cls="tall")}
<div class="two-col">
<div>
{exhibit(7, "Token identity of non-Scripture reused regions, weighted by length", "ex7_identity",
  "Source: as Exhibit 1. Identity = matched tokens ÷ region length after alignment.")}
</div>
<div class="pad-top">
<h2>Not read aloud, but not rewritten either</h2>
<p>Verbatim reading would cluster identity near 100%; genuine re-composition from notes would leave little that aligns at all. The distribution sits in between, centred on 55–70%. That is the signature of a manuscript being paraphrased as it is spoken: word order kept, connectives kept, nouns and idioms swapped for local ones.</p>
<p>The longest single reused region outside the pure Bible readings runs {longest_ns} words (The Faithfulness of God, from the Zinzendorf hymn through the Phillips rendering of verse 24; Begg’s commentary interleaved with the verses he quotes). The longest unbroken exact run is {longest_exact} words. Across the six sermons the detector found {regions} reused regions, {regions_ns} of them commentary rather than Scripture.</p>
<p>Roughly {minutes_reused:.0f} of the {minutes_paired:.0f} minutes the senior pastor spent preaching these six sermons were spent inside a Begg passage.</p>
</div>
</div>
''', "Findings · Texture"))

# ---------------------------------------------------------------- qualitative page
top_types = borrowed.most_common()
type_rows = "".join(f"<tr><td>{e(t.replace('_',' ').capitalize())}</td><td class=num>{c}</td></tr>" for t, c in top_types)
pages.append(page(f'''
<h1 class="title">What travels is the distinctive material, and it is re-voiced in the first person</h1>
<div class="two-col wide-right">
<div>
<h2>Borrowed elements catalogued by the reviewers</h2>
<table class="mini"><thead><tr><th>Type</th><th class=num>Count</th></tr></thead><tbody>{type_rows}<tr class=tot><td>Total, six sermons</td><td class=num>{n_borrowed}</td></tr></tbody></table>
<p class="small">Each element is a non-Scripture item the reviewer judged too specific to be coincidence or shared stock phrasing, quoted with timestamps in the review files. Scripture read by both preachers was excluded before counting.</p>
<h2>Attribution</h2>
<table class="mini"><tbody>
<tr><td>Sermons naming Alistair Begg</td><td class=num>{attrib_named} of 6</td></tr>
<tr><td>Sermons naming Truth For Life or Parkside</td><td class=num>0 of 6</td></tr>
<tr><td>Any “I heard a preacher say…” hedge</td><td class=num>0 of 6</td></tr>
<tr><td>Begg’s named authorities kept</td><td class=num>Stott, Morris, Packer, Phillips, Lewis, Zinzendorf</td></tr>
<tr><td>Begg’s anonymous “one commentator” kept anonymous</td><td class=num>2 sermons</td></tr>
</tbody></table>
</div>
<div>
<h2>Six ways the borrowing is personalised</h2>
<ol class="tight">
<li><b>Second-hand reading presented as first-hand.</b> Begg: “again I found John Stott to be so helpful.” FBC: “I found John Stodd, a great theologian, so helpful.” Begg: “to notice this little driving phrase in Paul’s life.” FBC: “It took me a while to dig up this phrase in Paul’s life.”</li>
<li><b>Begg’s life becomes the pastor’s life.</b> Begg: “that’s been true this week. It has for me. I have not lived and done all the good for which I longed.” FBC: “that’s been true this week. At least for me … I haven’t done all the good that I long to do.” Begg’s eleven years since leaving Scotland becomes 37 years since Little Rock.</li>
<li><b>Church names swapped, sentence kept.</b> “If people came from other churches to imitate Parkside Church, what would we give them to imitate?” becomes the same question about Fellowship Bible Church, followed by Begg’s four-item answer.</li>
<li><b>Britain becomes Arizona.</b> Tea to coffee; cinema to movie; “wee bit over the top” to “reading it over the top”; “the devil” to “the enemy”; Begg’s Sunday-evening markers to Sunday morning.</li>
<li><b>Statements become call-and-response.</b> “The source, the force and the course” becomes “the source. Say that with me.” Begg’s “God is for us” becomes “Now, let’s say it out loud. God is for me.”</li>
<li><b>Even the prayers are borrowed.</b> Two of the six closing prayers follow Begg’s prayer clause by clause and a third sermon opens with Begg’s prayer over the text, including the rare phrase “the thoroughfares of our lives”, captioned at FBC as “thorough affairs”.</li>
</ol>
{sbs("1:01:47", "I like to quote from one commentator where he says this in Thessalonica. There’s probably never been such a variety of religious cults and philosophic systems as in Paul’s day. Now again, this commentator is writing before the late 20th century. You know what? I think that our culture might be able to rival that.", "Let me quote from one commentator. There has probably never been such a variety of religious cults and philosophic systems as in Paul’s day. This was written before the late 20th century. We might be able to rival it now.", "No Clever Tricks. The pastor reproduces not only Begg’s anonymous quotation but Begg’s act of quoting it and his dating aside, recast as a personal habit.")}
</div>
</div>
''', "Findings · Character"))

# ---------------------------------------------------------------- per-sermon profiles
for i, r in enumerate(PAIRED, 1):
    rv = r["review"]
    b = r["body"]
    src_note, passage = SOURCE_NOTE[r["title"]]
    cons = r["source_consumption"][0]
    ex = rv["paraphrase_examples"]
    picks = [ex[k] for k in PICKS[r["title"]] if k < len(ex)]
    quotes = "".join(sbs(p["fbc_time"], trunc(p["fbc"], 240), trunc(p["begg"].replace(" [Stott]", ""), 240), trunc(p["comment"], 175)) for p in picks)
    orig = rv["original_material"]
    stats = f'''
<div class="prof-stats">
  {stat(f"{b['reused_pct']:.0f}%", "of sermon words in reused regions", f"{b['nonscripture_pct']:.0f}% commentary · {b['scripture_pct']:.0f}% shared Scripture")}
  {stat(f"{cons['covered_pct']:.0f}%", "of Begg’s sermon reappears", f"{cons['covered_tokens']:,} of {cons['tokens']:,} words")}
  {stat(f"{rv['dependence_rating']}/10", "reviewer dependence rating", f"order correlation ρ = {r['order_rho']:.2f}")}
  {stat(f"{orig.get('estimated_share_of_sermon_pct', '—')}%", "estimated original material", "reviewer estimate of the sermon")}
</div>'''
    pages.append(page(f'''
<div class="prof-head">
  <div class="prof-kicker">Sermon profile {i} of {len(PAIRED)} · {fmt_date(r['date'])} · {e(passage)}</div>
  <h1 class="title">“{e(r['title'])}” <span class="vs">tracks</span> Begg, {e(src_note)}</h1>
</div>
{stats}
<p class="lede small-lede">{PROFILE_LEAD[r['title']]}</p>
<div class="two-col">
<div>
<h2>Outline comparison</h2>
<p class="small">{e(trunc(rv['outline_comparison'], 560))}</p>
<h2>What is the pastor’s own</h2>
<p class="small">{e(trunc(orig['summary'], 460))}</p>
</div>
<div>
<h2>Side by side</h2>
{quotes}
</div>
</div>
<p class="ex-src">Sermon body {r['window']['start_time']}–{r['window']['end_time']} of the livestream ({r['window']['minutes']:.0f} min, {b['tokens']:,} words). Quotations are verbatim from the auto-captions and Whisper transcripts, so proper nouns may be garbled (“John Stodd” = John Stott). Full region list with timestamps: analysis/out/alignments/.</p>
''', f"Sermon profiles · {i}/{len(PAIRED)}", cls="profile"))

# ---------------------------------------------------------------- controls page
def ctrl_block(r):
    rv = r["review"]
    return f'''<div class="ctrl">
<h2>“{e(r['title'])}” · {fmt_date(r['date'])} · {e(rv['passage'].split(' (')[0])}</h2>
<p class="small"><b>Preacher:</b> {e(trunc(rv['speaker_notes'], 260))}</p>
<p class="small">{e(trunc(rv['rating_rationale'].replace('all thirty Begg files', 'all 22 Begg transcripts'), 900))}</p>
</div>'''

pages.append(page(f'''
<h1 class="title">The control: two other FBC preachers on the same book share only Scripture with Begg</h1>
<p class="lede">The series is not a one-preacher series. Two of the nine recordings were preached by other FBC staff, on passages Begg also preached (Volume 2, Parts 1–3; Volume 3, tracks 1–9). They went through exactly the same detector and the same full-transcript review. Both came back at 0% commentary overlap and a dependence rating of 0. This is what independent preaching on the same verses looks like, and it is the yardstick against which the senior pastor’s six sermons should be read.</p>
<div class="two-col">
{ctrl_block(CTRL[0])}
{ctrl_block(CTRL[1])}
</div>
<div class="callout">
<b>Excluded recording: “Big Mess” (August 1, 2026).</b> {e(trunc(BIGMESS['review']['speaker_notes'], 330))} It contains no sermon on 1 Thessalonians and no Begg material, and is excluded from all sermon-level statistics.
</div>
''', "Controls"))

# ---------------------------------------------------------------- title fingerprint / scope
title_rows = [
    ("Faith, Hope and Love (Apr 12 and Apr 19)", "Faith, Hope and Love (Vol. 1)", "identical", "Apr 19 analysed: 20% reused · Apr 12: captions disabled"),
    ("The Secret Place (Apr 26)", "—", "not in local corpus", "captions disabled"),
    ("Chosen and Changed (May 3)", "—", "not in local corpus", "captions disabled"),
    ("No Clever Tricks (May 10)", "No Clever Tricks (Vol. 1)", "identical", "40% reused"),
    ("Truth and Love (May 17)", "Truth and Love (Vol. 1)", "identical", "captions disabled; not analysed"),
    ("God’s Word… Not Man’s (May 24)", "The Word of God, Not Men (Vol. 1)", "near-identical", "24% reused"),
    ("Our Glory and Joy (May 31)", "Our Glory and Joy (Vol. 1)", "identical", "39% reused"),
    ("The Inevitable Affliction (Jun 7)", "—", "not in local corpus", "captions disabled"),
    ("Abound in Love (Jun 14)", "—", "not in local corpus", "captions disabled"),
    ("Living to Please God (Jun 21)", "Pleasing God (Vol. 2)", "near-identical", "captions disabled; not analysed"),
    ("Sexual Purity (Jun 28)", "Sexual Purity, Parts One and Two (Vol. 2)", "identical", "10% reused"),
    ("About Date and Time (Jul 5)", "—", "not in local corpus", "captions disabled"),
    ("Your True Identity (Jul 12)", "The Coming of the Lord, Part Three (Vol. 2)", "different", "0% · other preacher"),
    ("The Walk of Influence (Jul 19)", "Learning to Respect Our Leadership … Do Not Grieve the Holy Spirit (Vol. 3)", "different", "0% · Pastor Kevin"),
    ("The Faithfulness of God (Jul 26)", "The Faithfulness of God (Vol. 3)", "identical", "36% reused"),
    ("Attitudes of a Healthy Church (Aug 2)", "—", "not in local corpus", "captions disabled"),
]
trs = "".join(f"<tr class='{ 'hit' if m in ('identical','near-identical') else ''}'><td>{e(a)}</td><td>{e(b)}</td><td>{e(m)}</td><td>{e(n)}</td></tr>" for a, b, m, n in title_rows)
pages.append(page(f'''
<h1 class="title">Even the sermon titles are Begg’s, including three recordings we could not transcribe</h1>
<p class="lede">Of the 17 titled Sunday recordings in the playlist, nine (under eight titles) carry a title identical or near-identical to a Begg sermon in the 22-sermon comparison corpus. Six of the nine are the sermons analysed above. The other three, the April 12 “Faith, Hope and Love”, “Truth and Love” and “Living to Please God”, have captions disabled and could not be checked, but their titles match Begg’s Volume 1 tracks 1 and 5 and Volume 2 track 1. The six remaining untranscribed titles could not be compared: the Begg volumes contain sermons that are not in the local corpus, and the publisher’s site was unreachable from this environment.</p>
<table class="grid">
<thead><tr><th>FBC Tucson video (2026)</th><th>Nearest Alistair Begg title</th><th>Title match</th><th>Status</th></tr></thead>
<tbody>{trs}</tbody>
</table>
<p class="ex-src">Source: playlist.json (25 entries: 17 titled Sunday recordings, 1 children’s event, 7 removed videos). Title comparison against the 22 locally transcribed Begg sermons only.</p>
<div class="callout"><b>Implication.</b> The six analysed sermons are the ones whose captions happened to be enabled. Nothing in the pattern suggests they are unrepresentative: the three untranscribed recordings whose titles can be checked also carry Begg’s titles, and the senior pastor’s 1 Thessalonians preaching in this playlist runs from April through late July. Obtaining audio for the caption-disabled videos would allow the same analysis to be completed for the series as a whole.</div>
''', "Scope"))

# ---------------------------------------------------------------- methodology
pages.append(page(f'''
<h1 class="title">Methodology and limitations</h1>
<div class="two-col">
<div>
<h2>Corpus</h2>
<p class="small">FBC Tucson: the 9 videos in the “A Church of Irresistible Influence” playlist that have YouTube auto-captions (16 of 25 entries had captions disabled or were removed). Captions were downloaded with youtube-transcript-api and keep per-line timestamps. Alistair Begg: the 22 sermons of Truth For Life’s <i>A Study in 1 Thessalonians</i>, Volumes 1–3, transcribed locally with Whisper from the public audio.</p>
<h2>Normalisation</h2>
<p class="small">Lower-case; punctuation, caption tags and speaker markers removed; contractions collapsed; spelled-out numbers to digits; British spellings and a dozen ASR variants (“Thessalonika”, “gonna”) mapped to one form.</p>
<h2>Detection</h2>
<p class="small"><b>Exact runs.</b> Maximal runs of identical tokens of ≥8 words (the earlier report’s measure) and ≥5 words.<br>
<b>Reused regions.</b> Exact 4-word seeds (excluding 4-grams occurring &gt;12 times in the source) are chained when consecutive seeds lie within 40 words and 25 positions of the same diagonal; the chained span is re-scored with a token-level sequence matcher and kept if ≥12 words and ≥45% identity. Overlapping regions are merged. This recovers passages that caption errors and light paraphrase break into fragments.<br>
<b>Pairing.</b> A Begg sermon is “paired” when ≥4% of the FBC transcript falls inside reused regions with it. Coverage is the union over paired sources, so overlapping regions are not double-counted.</p>
<h2>Sermon body</h2>
<p class="small">Start and end timestamps were set by the reviewer after reading each transcript (first words of the sermon proper to the end of the closing prayer). Percentages in Exhibits 1, 4 and 6 and in the profiles use this denominator; the heat map and baselines use the whole transcript so that all 22 sources are comparable.</p>
</div>
<div>
<h2>Scripture handling</h2>
<p class="small">A heuristic flagged regions as likely Scripture using fuzzy overlap with public-domain translations (KJV, BBE), quotation cues (“verse 6”), and recurrence across ≥2 other Begg sermons. Because both preachers read the NIV, which is not public domain, the heuristic under-flags; the reviewer therefore classified every one of the {regions} regions by hand as Scripture, commentary or mixed, and the final figures use those labels. Mixed regions count as commentary.</p>
<h2>Close reading</h2>
<p class="small">Each FBC transcript and its paired Begg transcript(s) were read in full by an independent large-language-model reviewer (Claude Opus 5), separately for each sermon, with instructions to quote captions verbatim with timestamps, to discount Scripture and stock evangelical phrasing, to search all 22 Begg transcripts for the FBC sermon’s distinctive phrases, and to rate dependence from 0 to 10. Outputs are structured JSON in analysis/out/reviews/ and were spot-checked against the alignments.</p>
<h2>Baselines</h2>
<p class="small">The same detector was run on all {len(begg_self)} Begg-vs-Begg pairs (a preacher’s normal self-repetition) and all {len(unpaired)} FBC-vs-non-paired-Begg pairs (two preachers on related texts).</p>
<h2>Limitations</h2>
<ul class="small">
<li>Both texts are machine transcripts. Errors lower identity scores and can occasionally create false matches; the reviewer verified every quoted passage in context.</li>
<li>Coverage figures are floors. Structural borrowing (an outline, a dialogue device) and heavy paraphrase are invisible to token alignment and appear only in the qualitative findings.</li>
<li>Only 6 of the senior pastor’s sermons in the series had captions; the remainder could not be analysed.</li>
<li>Transcripts show what was said, not intent, permission or the preacher’s own view of his practice. Truth For Life’s usage terms were not reviewed.</li>
<li>Reproducible code: analysis/analyze.py, finalize.py, charts.py, build_report.py.</li>
</ul>
</div>
</div>
''', "Methodology"))

# ---------------------------------------------------------------- appendix: table + ratings
rows = ""
for r in FBC:
    b = r["body"]; c = r["coverage"]
    src_t = SRC[r["paired_sources"][0]]["title"] if r["paired_sources"] else "—"
    cons = f"{r['source_consumption'][0]['covered_pct']:.0f}%" if r["paired_sources"] else "—"
    rho = f"{r['order_rho']:.2f}" if r["order_rho"] is not None else "—"
    rows += f"<tr><td>{e(r['title'])}</td><td>{fmt_date(r['date'])[:-6]}</td><td>{e(r['review']['passage'].split(' (')[0].replace('1 Thessalonians', '1 Thess.').split(',')[0][:22])}</td><td>{r['window']['start_time']}–{r['window']['end_time']}</td><td class=num>{b['tokens']:,}</td><td>{e(src_t)}</td><td class=num>{b['reused_pct']:.1f}%</td><td class=num>{b['nonscripture_pct']:.1f}%</td><td class=num>{b['exact8_pct']:.1f}%</td><td class=num>{cons}</td><td class=num>{rho}</td><td class=num>{r['rating']}</td></tr>"
pages.append(page(f'''
<h1 class="title">Appendix A · Sermon-level data</h1>
<table class="grid dense">
<thead><tr><th>FBC sermon</th><th>Date</th><th>Passage</th><th>Sermon body</th><th class=num>Words</th><th>Paired Begg sermon</th><th class=num>Reused</th><th class=num>Commentary</th><th class=num>Exact-8</th><th class=num>Of Begg</th><th class=num>ρ</th><th class=num>Rating</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<p class="ex-src">Reused = share of sermon-body words inside any reused region. Commentary = the same after removing reviewer-classified Scripture. Exact-8 = share inside unbroken 8-word exact runs (earlier report’s measure, sermon-body basis). Of Begg = share of the paired Begg sermon’s words that reappear. ρ = Spearman rank correlation of reused-region positions. Rating = reviewer dependence rating, 0–10.</p>
{exhibit(8, "Reviewer dependence ratings, by sermon", "ex8_ratings", "Source: analysis/out/reviews/*.json. Rating scale: 0 = independent treatment of the passage; 10 = Begg’s manuscript read aloud.")}
''', "Appendix A"))

# ---------------------------------------------------------------- appendix: longest regions
segs = []
for r in PAIRED:
    for s in r["segments"]:
        if s["final_class"] != "scripture":
            segs.append((r, s))
segs.sort(key=lambda rs: -rs[1]["fbc_len"])
lrows = ""
for r, s in segs[:11]:
    lrows += f"<tr><td>{e(r['title'])}</td><td class=mono>{s['fbc_time']}</td><td class=num>{s['fbc_len']}</td><td class=num>{round(s['identity']*100)}%</td><td class=quote>{e(trunc(s['fbc_text'], 165))}</td><td class=quote>{e(trunc(s['src_text'], 165))}</td></tr>"
pages.append(page(f'''
<h1 class="title">Appendix B · The eleven longest reused commentary passages</h1>
<table class="grid dense regions">
<thead><tr><th>FBC sermon</th><th>Time</th><th class=num>Words</th><th class=num>Identity</th><th>FBC Tucson (normalised captions, opening)</th><th>Alistair Begg (normalised transcript, opening)</th></tr></thead>
<tbody>{lrows}</tbody>
</table>
<p class="ex-src">Regions are shown lower-cased and stripped of punctuation as the detector sees them; only the opening of each region is printed. The complete list of {regions_ns} commentary regions and {regions - regions_ns} Scripture regions, with both texts in full, is in analysis/out/alignments/ and analysis/out/results_final.json.</p>
''', "Appendix B"))

HTML = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Borrowed Pulpit · FBC Tucson × Alistair Begg</title>
<link rel="stylesheet" href="../fonts/fonts.css"><link rel="stylesheet" href="report.css"></head>
<body>{"".join(pages)}
<script>document.querySelectorAll('.page').forEach((p,i)=>{{const n=p.querySelector('.pnum'); if(n) n.textContent=(i+1)+' / '+document.querySelectorAll('.page').length;}});</script>
</body></html>'''
(REP / "report.html").write_text(HTML)
print("pages:", len(pages))
