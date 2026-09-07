"""Exhibits for the report (SVG, matplotlib). Reads analysis/out/results_final.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
FIG = OUT / "figures"
FIG.mkdir(exist_ok=True)

# ---- typography & palette -------------------------------------------------------
for f in ["Inter-var.ttf", "SourceSerif4-var.ttf"]:
    p = HERE / "fonts" / f
    if p.exists():
        fm.fontManager.addfont(str(p))
SANS = "Inter" if any(f.name == "Inter" for f in fm.fontManager.ttflist) else "DejaVu Sans"

INK = "#0b0b0b"; INK2 = "#52514e"; MUTED = "#898781"; GRID = "#e1e0d9"; AXIS = "#c3c2b7"
NAVY = "#0d366b"
C_REUSE = "#1c5cab"      # Begg-derived commentary (near-verbatim)
C_SCRIP = "#eb6834"      # Scripture both preachers read
C_REST = "#e6e5df"       # everything else in the sermon body
C_EXACT = "#0d366b"      # 8-word exact runs (prior method)
C_BASE = "#898781"       # baselines / controls
SEQ = ["#ffffff", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#1c5cab", "#104281", "#0d366b"]

plt.rcParams.update({
    "font.family": SANS, "font.size": 9.5, "axes.edgecolor": AXIS, "axes.linewidth": 0.6,
    "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5, "axes.titlesize": 10, "svg.fonttype": "none", "figure.dpi": 100,
    "axes.spines.top": False, "axes.spines.right": False, "text.color": INK,
})

R = json.load(open(OUT / "results_final.json"))
SRC_TITLE = {s["key"]: s["title"] for s in R["sources"]}
SRC_ORDER = [s["key"] for s in R["sources"]]
FBC_ALL = R["fbc"]
FBC = [r for r in FBC_ALL if r["title"] != "Big Mess"]          # Big Mess = children's event, excluded
PAIRED = [r for r in FBC if r["paired_sources"]]
SHORT = {"God's Word... Not Man's": "God's Word... Not Man's", "The Faithfulness of God": "Faithfulness of God",
         "The Walk of Influence": "Walk of Influence"}


def short(t):
    return SHORT.get(t, t)


def label_date(r):
    d = r["date"]
    return f"{short(r['title'])}  ·  {d[5:7].lstrip('0')}/{d[8:].lstrip('0')}"


def save(fig, name):
    fig.savefig(FIG / f"{name}.svg", bbox_inches="tight", pad_inches=0.05)
    fig.savefig(FIG / f"{name}.png", bbox_inches="tight", pad_inches=0.05, dpi=200)
    plt.close(fig)


def clean(ax, x=True, y=True):
    ax.grid(axis="x" if x else "y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(AXIS)


# ---- Exhibit 1: share of sermon body reused --------------------------------------
def ex1_coverage():
    rows = FBC[::-1]
    fig, ax = plt.subplots(figsize=(7.6, 3.9))
    y = np.arange(len(rows))
    ns = [r["body"]["nonscripture_pct"] for r in rows]
    sc = [r["body"]["scripture_pct"] for r in rows]
    ex = [r["body"]["exact8_pct"] for r in rows]
    ax.barh(y, ns, color=C_REUSE, height=0.58, label="Near-verbatim Begg commentary")
    ax.barh(y, sc, left=[a + 0.35 if b else a for a, b in zip(ns, sc)], color=C_SCRIP, height=0.58, label="Scripture both preachers read")
    # exact-run tick (prior method) as a thin marker
    for yi, e in zip(y, ex):
        if e > 0:
            ax.plot([e, e], [yi - 0.36, yi + 0.36], color=C_EXACT, linewidth=1.6, solid_capstyle="butt")
    for yi, a, b, r in zip(y, ns, sc, rows):
        tot = a + b
        if tot > 0:
            ax.text(tot + 1.0, yi, f"{tot:.0f}%", va="center", ha="left", fontsize=9, color=INK, fontweight=600)
        else:
            ax.text(0.8, yi, "no Begg source found", va="center", ha="left", fontsize=8.5, color=MUTED, style="italic")
    ax.set_yticks(y)
    ax.set_yticklabels([label_date(r) for r in rows], fontsize=9, color=INK)
    ax.set_xlim(0, max(max(a + b for a, b in zip(ns, sc)) * 1.18, 10))
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(decimals=0))
    ax.set_xlabel("Share of sermon-body words inside a reused region", color=INK2)
    clean(ax)
    # legend
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    handles = [Patch(color=C_REUSE, label="Near-verbatim Begg commentary"),
               Patch(color=C_SCRIP, label="Scripture passages both preachers read"),
               Line2D([0], [0], color=C_EXACT, linewidth=1.6, label="Exact 8-word runs only (earlier report's method)")]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.45, -0.16), ncol=3, frameon=False, fontsize=8, handlelength=1.4, columnspacing=1.2)
    save(fig, "ex1_coverage")


# ---- Exhibit 2: heat map FBC x Begg ------------------------------------------------
def ex2_heatmap():
    rows = FBC
    M = np.zeros((len(rows), len(SRC_ORDER)))
    for i, r in enumerate(rows):
        for j, s in enumerate(SRC_ORDER):
            M[i, j] = R["matrix"][f"{r['key']}||{s}"]["fuzzy_cov_fbc_pct"]
    fig, ax = plt.subplots(figsize=(8.2, 3.6))
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("seq", SEQ)
    norm = matplotlib.colors.PowerNorm(gamma=0.55, vmin=0, vmax=max(M.max(), 1))
    ax.imshow(M, cmap=cmap, norm=norm, aspect="auto")
    # cell borders as 2px surface gaps
    for i in range(len(rows) + 1):
        ax.axhline(i - 0.5, color="white", linewidth=1.5)
    for j in range(len(SRC_ORDER) + 1):
        ax.axvline(j - 0.5, color="white", linewidth=1.5)
    for i in range(len(rows)):
        for j in range(len(SRC_ORDER)):
            v = M[i, j]
            if v >= 3:
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7.5, color="white", fontweight=600)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([short(r["title"]) for r in rows], fontsize=8.5, color=INK)
    ax.set_xticks(range(len(SRC_ORDER)))
    lbl = []
    for s in SRC_ORDER:
        vol, name = s.split("/")
        lbl.append(f"{vol[-1]}.{name.split('-')[0]}")
    ax.set_xticklabels(lbl, fontsize=7.5, rotation=0)
    ax.set_xlabel("Alistair Begg, A Study in 1 Thessalonians  ·  volume.track  (cells: % of FBC transcript words inside a reused region)", color=INK2, fontsize=8.5)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    # volume brackets
    vols = {}
    for j, s in enumerate(SRC_ORDER):
        vols.setdefault(s.split("/")[0], []).append(j)
    for v, js in vols.items():
        ax.annotate("", xy=(min(js) - 0.45, -0.75), xytext=(max(js) + 0.45, -0.75),
                    arrowprops=dict(arrowstyle="-", color=AXIS, lw=0.8), annotation_clip=False)
        ax.text((min(js) + max(js)) / 2, -1.05, f"Volume {v[-1]}", ha="center", va="bottom", fontsize=8, color=INK2, clip_on=False)
    ax.set_ylim(len(rows) - 0.5, -1.4)
    save(fig, "ex2_heatmap")


# ---- Exhibit 3: service timelines ------------------------------------------------
def ex3_timelines():
    rows = FBC
    fig, axes = plt.subplots(len(rows), 1, figsize=(7.8, 0.62 * len(rows) + 0.6), sharex=True)
    for ax, r in zip(axes, rows):
        pm = r["per_minute"]
        tot = np.array(pm["total"], float)
        cov = np.array(pm["covered"], float)
        scr = np.array(pm["scripture"], float)
        mins = np.arange(len(tot))
        with np.errstate(divide="ignore", invalid="ignore"):
            frac_ns = np.where(tot > 0, (cov - scr) / np.maximum(tot, 1), 0)
            frac_s = np.where(tot > 0, scr / np.maximum(tot, 1), 0)
        w0, w1 = pm["window_min"]
        ax.axvspan(w0, w1, color="#efeee9", zorder=0, lw=0)
        ax.bar(mins + 0.5, frac_ns, width=1.0, color=C_REUSE, lw=0, zorder=2)
        ax.bar(mins + 0.5, frac_s, bottom=frac_ns, width=1.0, color=C_SCRIP, lw=0, zorder=2)
        ax.set_ylim(0, 1)
        ax.set_yticks([])
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.set_ylabel(short(r["title"]), rotation=0, ha="right", va="center", fontsize=8.5, color=INK, labelpad=6)
        b = r["body"]
        txt = f"{b['reused_pct']:.0f}% of sermon" if r["paired_sources"] else "—"
        ax.text(1.005, 0.5, txt, transform=ax.transAxes, va="center", ha="left", fontsize=8, color=INK2)
        ax.tick_params(length=0)
    axes[-1].set_xlabel("Minutes into the livestream  (shaded band = sermon body; bar height = share of that minute's words inside a reused region)", color=INK2, fontsize=8.5)
    axes[-1].set_xlim(0, 105)
    axes[-1].set_xticks(range(0, 106, 15))
    save(fig, "ex3_timelines")


# ---- Exhibit 4: dot plots (order preservation) -----------------------------------
def ex4_dotplots():
    rows = PAIRED
    n = len(rows)
    cols = 3
    rws = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rws, cols, figsize=(7.8, 2.7 * rws))
    axes = np.array(axes).reshape(-1)
    for ax, r in zip(axes, rows):
        best = r["paired_sources"][0]
        w = r["window"]
        segs = [s for s in r["segments"] if s["source"] == best]
        src_n = next(s["tokens"] for s in R["sources"] if s["key"] == best)
        for s in segs:
            x0 = 100 * (s["fbc_start_tok"] - w["start_tok"]) / max(1, w["tokens"])
            x1 = 100 * (s["fbc_end_tok"] - w["start_tok"]) / max(1, w["tokens"])
            y0 = 100 * s["src_start_tok"] / src_n
            y1 = 100 * s["src_end_tok"] / src_n
            col = C_SCRIP if s["final_class"] == "scripture" else C_REUSE
            ax.plot([x0, x1], [y0, y1], color=col, linewidth=2.6, solid_capstyle="round", alpha=0.95)
        ax.plot([0, 100], [0, 100], color=GRID, linewidth=0.8, zorder=0)
        ax.set_xlim(-2, 102); ax.set_ylim(-2, 102)
        ax.set_xticks([0, 50, 100]); ax.set_yticks([0, 50, 100])
        ax.set_xticklabels(["start", "FBC sermon →", "end"], fontsize=7.5)
        ax.set_yticklabels(["start", "Begg →", "end"], fontsize=7.5, rotation=90, va="center")
        ax.set_title(f"{short(r['title'])}", fontsize=9.5, loc="left", color=INK, fontweight=600, pad=4)
        rho = r.get("order_rho")
        ax.text(0.98, 0.04, f"ρ = {rho:.2f}" if rho is not None else "", transform=ax.transAxes, ha="right", va="bottom", fontsize=8, color=INK2)
        ax.set_aspect("equal")
        clean(ax, x=False, y=False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(GRID)
    for ax in axes[n:]:
        ax.axis("off")
    fig.subplots_adjust(hspace=0.45, wspace=0.35)
    save(fig, "ex4_dotplots")


# ---- Exhibit 5: how much of each Begg sermon was consumed ------------------------
def ex5_consumption():
    items = []
    for r in PAIRED:
        for sc in r["source_consumption"]:
            items.append((short(r["title"]), sc["title"], sc["covered_pct"], sc["tokens"]))
    items = items[::-1]
    fig, ax = plt.subplots(figsize=(7.6, 0.5 * len(items) + 0.9))
    y = np.arange(len(items))
    ax.barh(y, [i[2] for i in items], color=C_REUSE, height=0.55)
    ax.barh(y, [100 - i[2] for i in items], left=[i[2] for i in items], color=C_REST, height=0.55)
    for yi, it in zip(y, items):
        ax.text(it[2] + 1.2, yi, f"{it[2]:.0f}%", va="center", fontsize=9, color=INK, fontweight=600)
    ax.set_yticks(y)
    ax.set_yticklabels([f"Begg, “{it[1]}”  ({it[3]:,} words)" for it in items], fontsize=8.8, color=INK)
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(decimals=0))
    ax.set_xlabel("Share of Begg's sermon words that reappear (near-verbatim) in the FBC sermon", color=INK2)
    clean(ax)
    save(fig, "ex5_consumption")


# ---- Exhibit 6: baselines ----------------------------------------------------------
def ex6_baselines():
    begg_self = [p["fuzzy_cov_pct"] for p in R["baselines"]["begg_self_pairs"]]
    unpaired = []
    for r in FBC:
        for s in SRC_ORDER:
            if s not in r["paired_sources"]:
                unpaired.append(R["matrix"][f"{r['key']}||{s}"]["fuzzy_cov_fbc_pct"])
    paired = [R["matrix"][f"{r['key']}||{r['paired_sources'][0]}"]["fuzzy_cov_fbc_pct"] for r in PAIRED]
    # express as share of sermon body for paired for comparability? keep whole-transcript for apples-to-apples
    groups = [("FBC sermon vs. its\nsame-title Begg sermon", paired, C_REUSE),
              (f"Begg vs. his own other\n1 Thess. sermons ({len(begg_self)} pairs)", begg_self, C_BASE),
              (f"FBC sermon vs. every\nother Begg sermon ({len(unpaired)} pairs)", unpaired, C_BASE)]
    fig, ax = plt.subplots(figsize=(7.6, 2.9))
    rng = np.random.default_rng(3)
    for gi, (name, vals, col) in enumerate(groups):
        vals = np.array(vals)
        jitter = rng.uniform(-0.22, 0.22, len(vals))
        ax.scatter(vals, gi + jitter, s=26 if gi == 0 else 14, color=col, alpha=0.9 if gi == 0 else 0.55, linewidths=0, zorder=3)
        med = np.median(vals)
        ax.plot([med, med], [gi - 0.32, gi + 0.32], color=INK, linewidth=1.2, zorder=4)
        ax.text(max(vals) + 0.6, gi, f"median {med:.1f}%  ·  max {vals.max():.1f}%", va="center", fontsize=8.3, color=INK2)
    ax.set_yticks(range(len(groups)))
    ax.set_yticklabels([g[0] for g in groups], fontsize=8.8, color=INK)
    ax.invert_yaxis()
    ax.set_xlim(-0.5, 27)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(decimals=0))
    ax.set_xlabel("Share of the first transcript's words inside a reused region (whole transcript, same detector)", color=INK2)
    clean(ax)
    save(fig, "ex6_baselines")


# ---- Exhibit 7: how verbatim? identity histogram ----------------------------------
def ex7_identity():
    vals = []
    lens = []
    for r in PAIRED:
        for s in r["segments"]:
            if s["final_class"] != "scripture":
                vals.append(s["identity"]); lens.append(s["fbc_len"])
    vals = np.array(vals); lens = np.array(lens)
    fig, ax = plt.subplots(figsize=(7.6, 2.6))
    bins = np.arange(0.4, 1.01, 0.05)
    w, _ = np.histogram(vals, bins=bins, weights=lens)
    ax.bar(bins[:-1] + 0.025, w, width=0.046, color=C_REUSE, lw=0)
    ax.set_xlim(0.4, 1.0)
    ax.set_xticks(np.arange(0.4, 1.01, 0.1))
    ax.set_xticklabels([f"{int(round(v*100))}%" for v in np.arange(0.4, 1.01, 0.1)])
    ax.set_xlabel("Token identity of the reused region (100% = word-for-word)", color=INK2)
    ax.set_ylabel("FBC words in regions", color=INK2)
    wm = np.average(vals, weights=lens)
    top = ax.get_ylim()[1] * 1.18
    ax.set_ylim(0, top)
    ax.axvline(wm, color=INK, linewidth=1, ymax=0.93)
    ax.text(wm + 0.008, top * 0.97, f"word-weighted mean identity {wm*100:.0f}%", fontsize=8.3, color=INK2, va="top")
    clean(ax, x=False, y=True)
    save(fig, "ex7_identity")


# ---- Exhibit 8: reviewer dependence ratings -----------------------------------------
def ex8_ratings():
    rows = [r for r in FBC if r.get("rating") is not None]
    if not rows:
        return
    fig, ax = plt.subplots(figsize=(7.6, 0.48 * len(rows) + 0.8))
    y = np.arange(len(rows))
    vals = [r["rating"] for r in rows][::-1]
    labs = [label_date(r) for r in rows][::-1]
    ax.barh(y, vals, color=[C_REUSE if v >= 5 else C_BASE for v in vals], height=0.55)
    for yi, v in zip(y, vals):
        ax.text(v + 0.15, yi, f"{v}/10", va="center", fontsize=9, color=INK, fontweight=600)
    ax.set_yticks(y); ax.set_yticklabels(labs, fontsize=9, color=INK)
    ax.set_xlim(0, 10.8); ax.set_xticks(range(0, 11, 2))
    ax.set_xlabel("Reviewer dependence rating (0 = independent, 10 = read aloud from Begg)", color=INK2)
    clean(ax)
    save(fig, "ex8_ratings")


if __name__ == "__main__":
    ex1_coverage(); ex2_heatmap(); ex3_timelines(); ex4_dotplots(); ex5_consumption(); ex6_baselines(); ex7_identity(); ex8_ratings()
    print("figures:", sorted(p.name for p in FIG.glob("*.svg")))
