"""Corpus loading and normalization for the FBC Tucson / Alistair Begg comparison.

FBC transcripts are YouTube auto-captions covering the whole service (worship
music, announcements, sermon). Source transcripts are Whisper ASR of the public
Truth For Life audio. Both are reduced to a normalized token stream; FBC tokens
keep their caption timestamp so findings can be located in the video.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FBC_DIR = ROOT / "transcripts"
SRC_DIR = ROOT / "source_transcripts"

TAG_RE = re.compile(r"\[[^\]]*\]")
LINE_RE = re.compile(r"^\[(\d\d):(\d\d):(\d\d)\.(\d+)\]\s*(.*)$")
WORD_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")

NUMBER_WORDS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
    "seven": "7", "eight": "8", "nine": "9", "ten": "10", "eleven": "11",
    "twelve": "12", "thirteen": "13", "fourteen": "14", "fifteen": "15",
    "sixteen": "16", "seventeen": "17", "eighteen": "18", "nineteen": "19",
    "twenty": "20", "first": "1", "second": "2", "third": "3",
}
# Ordinary ASR spelling drift that should not break a match.
ALIASES = {
    "thessalonica": "thessalonica", "thessalonika": "thessalonica",
    "thessalonian": "thessalonians", "thessalonians": "thessalonians",
    "ok": "okay", "alright": "all right", "toward": "towards", "afterward": "afterwards",
    "wanna": "want to", "gonna": "going to", "gotta": "got to", "cuz": "because", "cause": "because",
    "saviour": "savior", "favour": "favor", "honour": "honor", "behaviour": "behavior",
    "labour": "labor", "colour": "color", "centre": "center", "practise": "practice",
    "grey": "gray", "judgement": "judgment", "uh": "", "um": "", "eh": "", "mm": "", "hmm": "",
}

STOPWORDS = set("""
a an the and or but if of to in on at by for with from as is are was were be been being am
i me my we our you your he him his she her it its they them their this that these those there
here what which who whom whose when where why how not no yes so do does did done have has had
having will would shall should can could may might must just very then than too also into out
up down over under again further once all any both each few more most other some such only own
same about above after before because between during through until while against off says say
said know think going want like get got go come came one two
""".split())


@dataclass
class Doc:
    key: str
    title: str
    kind: str                       # "fbc" or "source"
    tokens: list[str]
    times: list[float] | None = None  # per-token timestamp (fbc only)
    raw_words: list[str] = field(default_factory=list)  # display form per token
    meta: dict = field(default_factory=dict)

    @property
    def n(self) -> int:
        return len(self.tokens)


def _normalize_text(text: str) -> list[tuple[str, str]]:
    """Return (normalized_token, display_word) pairs for a chunk of text."""
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = text.replace("-", " ").replace("—", " ").replace("–", " ")
    out = []
    for m in re.finditer(r"\S+", text):
        display = m.group(0)
        low = display.lower()
        for w in WORD_RE.findall(low):
            w = ALIASES.get(w, w)
            if w == "":
                continue
            for part in w.split():
                part = NUMBER_WORDS.get(part, part)
                part = part.replace("'", "")
                if part:
                    out.append((part, display))
    return out


def load_fbc(path: Path) -> Doc:
    tokens, times, raws = [], [], []
    music_times: list[float] = []
    title, url, lang = path.stem, "", ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            body = line[2:].strip()
            if body.startswith("http"):
                url = body
            elif body.startswith("Language:"):
                lang = body
            elif not title or title == path.stem:
                title = body
            continue
        m = LINE_RE.match(line)
        if not m:
            continue
        h, mi, s, frac = m.group(1), m.group(2), m.group(3), m.group(4)
        t = int(h) * 3600 + int(mi) * 60 + int(s) + float("0." + frac)
        if re.search(r"\[(music|singing)", m.group(5)):
            music_times.append(t)
        text = TAG_RE.sub(" ", m.group(5)).replace(">>", " ")
        for tok, disp in _normalize_text(text):
            tokens.append(tok)
            times.append(t)
            raws.append(disp)
    m = re.search(r"([A-Za-z0-9_-]{11})$", path.stem)
    return Doc(key=path.stem, title=title, kind="fbc", tokens=tokens, times=times,
               raw_words=raws, meta={"url": url, "language": lang, "video_id": m.group(1) if m else "",
                                     "music_times": music_times})


def load_source(path: Path) -> Doc:
    lines = path.read_text(encoding="utf-8").splitlines()
    # Drop the Truth For Life boilerplate header lines.
    body = [ln for ln in lines if not ln.startswith("The following message by Alistair Begg")
            and not ln.startswith("For more information, visit us online")]
    tokens, raws = [], []
    for ln in body:
        for tok, disp in _normalize_text(ln):
            tokens.append(tok)
            raws.append(disp)
    vol = path.parent.name
    return Doc(key=f"{vol}/{path.stem}", title=path.stem, kind="source", tokens=tokens,
               raw_words=raws, meta={"volume": vol})


FBC_TITLES = {
    "Big_Mess_8-1-2026_rI2h_cc-Kj4": ("Big Mess", "2026-08-01"),
    "Faith_Hope_and_Love_-_041926_pgy_YF3x3gE": ("Faith, Hope and Love", "2026-04-19"),
    "God_s_Word...Not_Man_s_-_052426_UA--g_npTNA": ("God's Word... Not Man's", "2026-05-24"),
    "No_Clever_Tricks_-_051026_j9oaoRg6kZ8": ("No Clever Tricks", "2026-05-10"),
    "Our_Glory_and_Joy_-_053126_U1kxopCXoNY": ("Our Glory and Joy", "2026-05-31"),
    "Sexual_Purity_-_062826_B1H7S1-j6ag": ("Sexual Purity", "2026-06-28"),
    "The_Faithfulness_of_God_-_072626_MXAy4hKNfwc": ("The Faithfulness of God", "2026-07-26"),
    "The_Walk_of_Influence_-_071926_EuKaZ_afxRo": ("The Walk of Influence", "2026-07-19"),
    "Your_True_Identity_-_071226_T-_Xdtb-Ync": ("Your True Identity", "2026-07-12"),
}

SOURCE_TITLES = {
    "volume1/01-faithhopelove": "Faith, Hope and Love",
    "volume1/04-noclevertricks": "No Clever Tricks",
    "volume1/05-truthandlove": "Truth and Love",
    "volume1/06-thewordofgodnotmen": "The Word of God, Not Men",
    "volume1/07-ourgloryandjoy": "Our Glory and Joy",
    "volume2/01-pleasinggod": "Pleasing God",
    "volume2/02-sexualpuritypartone": "Sexual Purity, Part One",
    "volume2/03-sexualpurityparttwo": "Sexual Purity, Part Two",
    "volume2/06-thosewhohavehope": "Those Who Have Hope",
    "volume2/07-thecomingofthelordpartone": "The Coming of the Lord, Part One",
    "volume2/08-thecomingofthelordparttwo": "The Coming of the Lord, Part Two",
    "volume2/09-thecomingofthelordpartthree": "The Coming of the Lord, Part Three",
    "volume3/01-learningtorespectourleadership": "Learning to Respect Our Leadership",
    "volume3/02-learningtoliveinpeace": "Learning to Live in Peace",
    "volume3/03-practicingpatience": "Practicing Patience",
    "volume3/04-cultivatingkindness": "Cultivating Kindness",
    "volume3/05-learninghowtoworshipanintroduction": "Learning How to Worship: An Introduction",
    "volume3/06-givethanks": "Give Thanks",
    "volume3/07-donotgrievetheholyspirit": "Do Not Grieve the Holy Spirit",
    "volume3/08-listeningtothewordofgod": "Listening to the Word of God",
    "volume3/09-sanctification": "Sanctification",
    "volume3/10-thefaithfulnessofgod": "The Faithfulness of God",
}


def load_all() -> tuple[list[Doc], list[Doc]]:
    fbc = []
    for p in sorted(FBC_DIR.glob("*.txt")):
        d = load_fbc(p)
        nice, date = FBC_TITLES.get(p.stem, (d.title, ""))
        d.title = nice
        d.meta["date"] = date
        fbc.append(d)
    fbc.sort(key=lambda d: d.meta["date"])
    src = []
    for p in sorted(SRC_DIR.glob("volume*/*.txt")):
        d = load_source(p)
        d.title = SOURCE_TITLES.get(d.key, d.title)
        src.append(d)
    return fbc, src


def fmt_time(t: float) -> str:
    t = int(round(t))
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}"


if __name__ == "__main__":
    fbc, src = load_all()
    for d in fbc:
        print(f"FBC  {d.title:32s} {d.meta['date']} tokens={d.n}")
    for d in src:
        print(f"SRC  {d.key:50s} tokens={d.n}")
