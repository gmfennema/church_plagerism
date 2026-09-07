"""Exact and fuzzy text-reuse detection between two token streams.

Two detectors are used:

1. Exact runs: maximal contiguous runs of identical normalized tokens of at
   least `min_run` words (the classic n-gram fingerprint approach).
2. Fuzzy alignment: exact 4-gram seeds are chained along a diagonal band and
   the resulting region is re-scored with a token-level sequence matcher, so a
   passage broken by a caption/ASR error still counts as one reused region.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher


@dataclass
class ExactRun:
    a_start: int
    b_start: int
    length: int


@dataclass
class Segment:
    a_start: int
    a_end: int          # exclusive
    b_start: int
    b_end: int          # exclusive
    matched: int        # tokens in matching blocks
    identity: float     # matched / max(len_a, len_b)
    seeds: int

    @property
    def a_len(self):
        return self.a_end - self.a_start

    @property
    def b_len(self):
        return self.b_end - self.b_start

    def to_dict(self):
        d = asdict(self)
        d["a_len"] = self.a_len
        d["b_len"] = self.b_len
        return d


def ngram_index(tokens: list[str], n: int) -> dict[tuple, list[int]]:
    idx: dict[tuple, list[int]] = defaultdict(list)
    for i in range(len(tokens) - n + 1):
        idx[tuple(tokens[i:i + n])].append(i)
    return idx


def exact_runs(a: list[str], b: list[str], min_run: int = 8, n_seed: int = 4) -> list[ExactRun]:
    """Maximal exact runs of >= min_run tokens (each run reported once)."""
    idx = ngram_index(b, n_seed)
    seen: set[tuple[int, int]] = set()
    runs = []
    for i in range(len(a) - n_seed + 1):
        for j in idx.get(tuple(a[i:i + n_seed]), ()):
            if (i, j) in seen:
                continue
            # extend right
            k = n_seed
            while i + k < len(a) and j + k < len(b) and a[i + k] == b[j + k]:
                k += 1
            # is this run maximal on the left?
            if i > 0 and j > 0 and a[i - 1] == b[j - 1]:
                # the run starting one earlier will be (or was) reported
                for off in range(k - n_seed + 1):
                    seen.add((i + off, j + off))
                continue
            for off in range(k - n_seed + 1):
                seen.add((i + off, j + off))
            if k >= min_run:
                runs.append(ExactRun(i, j, k))
    return runs


def coverage_from_runs(runs: list[ExactRun], n: int, side: str = "a") -> list[bool]:
    cov = [False] * n
    for r in runs:
        s = r.a_start if side == "a" else r.b_start
        for t in range(s, s + r.length):
            cov[t] = True
    return cov


def fuzzy_segments(a: list[str], b: list[str], n_seed: int = 4, max_gap: int = 40,
                   band: int = 25, min_len: int = 12, min_identity: float = 0.45,
                   max_seed_occ: int = 12) -> list[Segment]:
    """Chain exact seeds on a common diagonal into near-verbatim regions.

    max_seed_occ drops very common 4-grams (e.g. 'the word of god') from the
    seed set so chains are anchored by distinctive phrasing.
    """
    idx = ngram_index(b, n_seed)
    seeds = []
    for i in range(len(a) - n_seed + 1):
        js = idx.get(tuple(a[i:i + n_seed]))
        if not js or len(js) > max_seed_occ:
            continue
        for j in js:
            seeds.append((i, j))
    if not seeds:
        return []
    # Greedy chaining: sort by a-position, attach each seed to an open chain
    # whose last seed is within max_gap in a and within band in diagonal.
    seeds.sort()
    chains: list[list[tuple[int, int]]] = []
    open_chains: list[list[tuple[int, int]]] = []
    for (i, j) in seeds:
        d = i - j
        best, best_cost = None, None
        still_open = []
        for ch in open_chains:
            li, lj = ch[-1]
            if i - li > max_gap:
                chains.append(ch)
                continue
            still_open.append(ch)
            if i >= li and j >= lj and abs(d - (li - lj)) <= band:
                cost = abs(d - (li - lj)) + (i - li) * 0.1
                if best_cost is None or cost < best_cost:
                    best, best_cost = ch, cost
        open_chains = still_open
        if best is not None:
            best.append((i, j))
        else:
            open_chains.append([(i, j)])
    chains.extend(open_chains)

    segs: list[Segment] = []
    for ch in chains:
        a0 = ch[0][0]
        a1 = ch[-1][0] + n_seed
        b0 = min(j for _, j in ch)
        b1 = max(j for _, j in ch) + n_seed
        if a1 - a0 < min_len and b1 - b0 < min_len:
            continue
        # small extension to catch trailing near-matches
        a0e, a1e = max(0, a0 - 3), min(len(a), a1 + 3)
        b0e, b1e = max(0, b0 - 3), min(len(b), b1 + 3)
        sm = SequenceMatcher(None, a[a0e:a1e], b[b0e:b1e], autojunk=False)
        blocks = [bl for bl in sm.get_matching_blocks() if bl.size > 0]
        if not blocks:
            continue
        matched = sum(bl.size for bl in blocks)
        # trim to first/last matching block
        fa0 = a0e + blocks[0].a
        fa1 = a0e + blocks[-1].a + blocks[-1].size
        fb0 = b0e + blocks[0].b
        fb1 = b0e + blocks[-1].b + blocks[-1].size
        ident = matched / max(fa1 - fa0, fb1 - fb0)
        if (fa1 - fa0) < min_len or ident < min_identity:
            continue
        segs.append(Segment(fa0, fa1, fb0, fb1, matched, round(ident, 3), len(ch)))
    # merge overlapping segments on the a-side (keep the union)
    segs.sort(key=lambda s: (s.a_start, s.a_end))
    merged: list[Segment] = []
    for s in segs:
        if merged and s.a_start < merged[-1].a_end and abs((s.a_start - s.b_start) - (merged[-1].a_start - merged[-1].b_start)) <= band * 2:
            m = merged[-1]
            m.a_end = max(m.a_end, s.a_end)
            m.b_start = min(m.b_start, s.b_start)
            m.b_end = max(m.b_end, s.b_end)
            m.matched = max(m.matched, s.matched)
            m.identity = round(m.matched / max(m.a_len, m.b_len), 3)
            m.seeds += s.seeds
        else:
            merged.append(s)
    return merged


def coverage_from_segments(segs: list[Segment], n: int, side: str = "a") -> list[bool]:
    cov = [False] * n
    for s in segs:
        lo, hi = (s.a_start, s.a_end) if side == "a" else (s.b_start, s.b_end)
        for t in range(lo, hi):
            cov[t] = True
    return cov


def matched_token_mask(a: list[str], b: list[str], segs: list[Segment]) -> list[bool]:
    """Tokens of `a` that sit inside a matching block of some segment."""
    mask = [False] * len(a)
    for s in segs:
        sm = SequenceMatcher(None, a[s.a_start:s.a_end], b[s.b_start:s.b_end], autojunk=False)
        for bl in sm.get_matching_blocks():
            for t in range(s.a_start + bl.a, s.a_start + bl.a + bl.size):
                mask[t] = True
    return mask
