"""Figures, Table II and number macros of the short TeraMove paper.

Reads teramove_eval/results_short/*.json (written by run_short.py) and writes
TeraHertz-short/figures/*.pdf, TeraHertz-short/tables/tiers.tex and
TeraHertz-short/numbers.tex.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Wedge  # noqa: E402

from chsr_sim.config import RAIL_SPEED, TARGET_COVERAGE  # noqa: E402
from chsr_sim.physics import calculate_sinr  # noqa: E402
from teramove_eval.make_assets import ci, f1, pfmt, pval, room_axes, walls  # noqa: E402
from teramove_eval.run import DENSITY_LEVELS, WALLS, density  # noqa: E402
from teramove_eval.run_short import ARMS, SEQ_CROWD, load  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "TeraHertz-short"
FIG, TAB = OUT / "figures", OUT / "tables"
FIG.mkdir(parents=True, exist_ok=True)
TAB.mkdir(parents=True, exist_ok=True)
INK, INK2 = "#0b0b0b", "#52514e"
# categorical slots 1-6 of the reference palette, fixed order (validated, light mode)
ARM_STYLE = {
    "fixed": ("Static, fixed association", "#2a78d6"),
    "handover": ("Static + handover", "#eb6834"),
    "ho_t2": ("Handover + Tier 2", "#1baf7a"),
    "teramove": ("HPSO (TeraMove)", "#eda100"),
    "greedy": ("Greedy re-placement", "#e87ba4"),
    "pso": ("Standard PSO", "#008300"),
    "ga": ("GA", "#6250d6"),
}
plt.rcParams.update({
    "font.family": "serif", "font.size": 8, "axes.labelsize": 8, "legend.fontsize": 6.5,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#e4e3df", "grid.linewidth": 0.5, "axes.edgecolor": INK2,
    "pdf.fonttype": 42, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
})
COL_W = 3.45
NUM = {}
EMPTY = np.zeros((32, 20))


def macro(k, v):
    NUM[k] = v


def save(fig, name):
    fig.savefig(FIG / f"{name}.pdf")
    plt.close(fig)


# ------------------------------------------------------------------------ commissioning
def commission():
    c = load("commission")
    macro("MilpSimEmpty", f1(100 * c["milp_empty_coverage"]))
    macro("CommEmpty", f1(100 * c["commissioned_empty_coverage"]))
    # the Table II crowds without body loss: shows that the outages come from blockage
    import chsr_sim.physics as lp
    from teramove_eval.run_short import N_SEEDS, TIER_CROWD
    routers = c["routers"]
    with_b, without = [], []
    for s in range(N_SEEDS):
        d = density(TIER_CROWD + s)
        with_b.append(calculate_sinr(routers, d, WALLS)[1])
        saved = lp.HUMAN_PENALTY_DB
        lp.HUMAN_PENALTY_DB = 0.0
        lp._ROUTER_STATIC_CACHE.clear()
        lp._HUMAN_DENSITY_CACHE_ID = None
        without.append(calculate_sinr(routers, d, WALLS)[1])
        lp.HUMAN_PENALTY_DB = saved
        lp._ROUTER_STATIC_CACHE.clear()
        lp._HUMAN_DENSITY_CACHE_ID = None
    macro("NoBlockCov", f1(100 * np.mean(without)))
    macro("BlockCov", f1(100 * np.mean(with_b)))
    return c


# ------------------------------------------------------------------------ Table II
def tiers():
    rows = load("tiers")
    cov = np.array([[e["coverage"] for e in r["log"]] for r in rows]) * 100       # (seeds, 4)
    disp = np.array([[e["disp"] for e in r["log"]] for r in rows])
    act = np.array([[e["max_ap_disp"] for e in r["log"]] for r in rows]) / RAIL_SPEED
    wall = np.array([[e["wall_s"] for e in r["log"]] for r in rows])
    nn = np.array([r["log"][-1]["disp_nn"] for r in rows])
    m = cov.mean(axis=0)
    rnd = [round(x, 1) for x in m]
    c_ci = [ci(cov[:, k]) for k in range(4)]
    names = ["Baseline", "Tier~2", "Tier~3", "Tier~4"]
    kinds = ["None", "Electronic (beam steering)", "Minor physical (Z-axis)", "Full 3D repositioning"]
    lines = [r"\begin{tabular}{@{} l c c c l @{}}", r"\toprule",
             r"\textbf{Tier} & \textbf{Coverage (\%)} & \textbf{Displ.\ (m)} & \textbf{Actuation (s)} & "
             r"\textbf{Adjustment Type} \\", r"\midrule"]
    for k in range(4):
        cov_s = f"{f1(m[k])} $\\pm$ {f1(c_ci[k][1])}"
        if k > 0:
            cov_s += f" ({'+' if rnd[k] - rnd[k - 1] >= 0 else ''}{f1(rnd[k] - rnd[k - 1])})"
        a = "0" if k <= 1 else f1(act[:, k].mean())
        lines.append(f"{names[k]} & {cov_s} & {f1(disp[:, k].mean())} & {a} & {kinds[k]} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TAB / "tiers.tex").write_text("\n".join(lines) + "\n")
    for k, tag in enumerate(("Base", "Two", "Three", "Four")):
        macro(f"Tier{tag}", f1(m[k]))
        macro(f"TierDisp{tag}", f1(disp[:, k].mean()))
        macro(f"TierAct{tag}", f1(act[:, k].mean()))
        macro(f"TierWall{tag}", f1(wall[:, k].mean()))
    for k, tag in ((1, "Two"), (2, "Three"), (3, "Four")):
        macro(f"TierGain{tag}", f1(rnd[k] - rnd[k - 1]))
    tot = rnd[3] - rnd[0]
    macro("TierGainTotal", f1(tot))
    macro("TierGainTwoThree", f1(rnd[2] - rnd[0]))
    macro("TierTwoShare", f1(100 * (rnd[1] - rnd[0]) / tot) if tot > 0 else "0.0")
    macro("TierFourReach", f1(100 * np.mean(cov[:, 3] >= 100 * TARGET_COVERAGE)))
    macro("TierFourMax", f1(cov[:, 3].max()))
    macro("HungNN", f1(nn.mean()))
    macro("HungHu", f1(disp[:, 3].mean()))
    macro("HungSaving", f1(round(nn.mean(), 1) - round(disp[:, 3].mean(), 1)))
    macro("HungSavingPct", f1(100 * (1 - round(disp[:, 3].mean(), 1) / round(nn.mean(), 1)))
          if nn.mean() > 0 else "0.0")
    macro("HungP", pfmt(pval(nn, disp[:, 3])))
    macro("Seeds", str(len(rows)))
    return rows


# ------------------------------------------------------------------------ temporal
def temporal():
    rows = load("temporal")
    by = {a: sorted([r for r in rows if r["arm"] == a], key=lambda r: r["seed"]) for a in ARMS}
    key = {"fixed": "Fix", "handover": "Ho", "ho_t2": "HoT", "teramove": "Tm", "greedy": "Gr", "pso": "Pso", "ga": "Ga"}
    for a in ARMS:
        b = np.array([[s["cov_before"] for s in r["steps"]] for r in by[a]]) * 100
        c = np.array([[s["cov_after"] for s in r["steps"]] for r in by[a]]) * 100
        d = np.array([[s["disp"] for s in r["steps"]] for r in by[a]])
        for t in range(3):
            macro(f"Seq{key[a]}Before{'ABC'[t]}", f1(b[:, t].mean()))
            macro(f"Seq{key[a]}After{'ABC'[t]}", f1(c[:, t].mean()))
            macro(f"Seq{key[a]}Disp{'ABC'[t]}", f1(d[:, t].mean()))
        macro(f"Seq{key[a]}CovAvg", f1(c.mean()))
        macro(f"Seq{key[a]}DispTot", f1(d.sum(axis=1).mean()))
        macro(f"Seq{key[a]}Reach", f1(100 * np.mean(c >= 100 * TARGET_COVERAGE)))
    tot = {a: np.array([sum(s["disp"] for s in r["steps"]) for r in by[a]]) for a in ARMS}
    avg = {a: np.array([np.mean([s["cov_after"] for s in r["steps"]]) for r in by[a]]) for a in ARMS}
    for a in ("pso", "ga", "greedy"):
        k = key[a]
        macro(f"Seq{k}DispP", pfmt(pval(tot['teramove'], tot[a])))
        macro(f"Seq{k}CovP", pfmt(pval(avg['teramove'], avg[a])))
        h, o = round(tot["teramove"].mean(), 1), round(tot[a].mean(), 1)
        macro(f"SeqDispRed{k}", f1(100 * (1 - h / o)) if o > 0 else "0.0")
        macro(f"SeqCovGap{k}", f1(round(100 * avg[a].mean(), 1) - round(100 * avg["teramove"].mean(), 1)))
    same = all(abs(a["cov_after"] - b["cov_after"]) < 1e-12 and abs(a["disp"] - b["disp"]) < 1e-9
               for ra, rb in zip(by["teramove"], by["greedy"]) for a, b in zip(ra["steps"], rb["steps"]))
    assert same, "paper text says Tier 4 equals the greedy seed in every temporal run"
    tiers_ = np.array([[s["tier"] for s in r["steps"]] for r in by["teramove"]], dtype=object)
    for t in range(3):
        col = [x for x in tiers_[:, t]]
        macro(f"SeqTierFour{'ABC'[t]}", f1(100 * np.mean([x == 4 for x in col]), 0))
        macro(f"SeqTierOne{'ABC'[t]}", f1(100 * np.mean([x == 1 for x in col]), 0))
    return by


# ------------------------------------------------------------------------ Fig. 2
def ap_panel(ax, routers, title=None):
    walls(ax)
    for r in routers:
        th = 90.0 - r["phi"]                     # compass bearing -> math angle
        ax.add_patch(Wedge((r["x"], r["y"]), 2.5, th - r["alpha"] / 2, th + r["alpha"] / 2,
                           facecolor="#2a78d6", alpha=0.35, edgecolor="#2a78d6", lw=0.4, zorder=2))
        ax.scatter([r["x"]], [r["y"]], marker="^", s=16, color="#eb6834", edgecolor="white", lw=0.4, zorder=5)
    room_axes(ax)
    if title:
        ax.set_title(title, fontsize=7.5)


def sinr_panel(ax, routers, dens, title=None):
    s, cov = calculate_sinr(routers, dens, WALLS)
    im = ax.imshow(np.clip(s.T, -10, 30), origin="lower", extent=(0, 32, 0, 20), cmap="Blues", vmin=-10, vmax=30)
    walls(ax)
    ax.scatter([r["x"] for r in routers], [r["y"] for r in routers], marker="^", s=14, color="#eb6834",
               edgecolor="white", lw=0.4, zorder=5)
    room_axes(ax)
    if title:
        ax.set_title(title, fontsize=7.5)
    return im, cov


def single(name, draw, cbar=None):
    fig, ax = plt.subplots(figsize=(COL_W, COL_W * 20 / 32 + 0.25))
    out = draw(ax)
    if cbar is not None:
        cb = fig.colorbar(out[0], ax=ax, fraction=0.03, pad=0.01)
        cb.set_label(cbar)
    save(fig, name)
    return out


def fig2(by):
    r0 = by["teramove"][0]                        # optimiser seed 0
    steps = r0["steps"]
    pick = next((s for s in steps if s["tier"] is not None and s["tier"] >= 3), None)
    if pick is None:
        pick = max(steps, key=lambda s: s["cov_after"] - s["cov_before"])
    t = pick["t"]
    prev_dens = EMPTY if t == 0 else density(SEQ_CROWD + 3 * 0 + t - 1)
    dens = density(SEQ_CROWD + 3 * 0 + t)
    before, after = pick["routers_before"], pick["routers_after"]
    single("fig2a_aps_before", lambda ax: ap_panel(ax, before))
    _, c_prev = single("fig2b_sinr_prev", lambda ax: sinr_panel(ax, before, prev_dens), "SINR (dB)")

    def dens_draw(ax):
        im = ax.imshow(dens.T, origin="lower", extent=(0, 32, 0, 20), cmap="Reds", vmin=0, vmax=1)
        walls(ax)
        room_axes(ax)
        return (im,)
    single("fig2c_density", dens_draw, "Human density $D_h$")
    _, c_before = single("fig2d_sinr_before", lambda ax: sinr_panel(ax, before, dens), "SINR (dB)")
    single("fig2e_aps_after", lambda ax: ap_panel(ax, after))
    _, c_after = single("fig2f_sinr_after", lambda ax: sinr_panel(ax, after, dens), "SINR (dB)")
    assert abs(c_before - pick["cov_before"]) < 1e-12 and abs(c_after - pick["cov_after"]) < 1e-12
    macro("FigTwoStep", str(t))
    macro("FigTwoPrevStep", "the empty floor" if t == 0 else f"$t_{t - 1}$")
    macro("FigTwoLayout", "commissioned" if t == 0 else f"$t_{t - 1}$-optimized")
    macro("FigTwoPrev", f1(100 * c_prev))
    macro("FigTwoBefore", f1(100 * c_before))
    macro("FigTwoAfter", f1(100 * c_after))
    macro("FigTwoDisp", f1(pick["disp"]))
    macro("FigTwoTier", str(pick["tier"]))


# ------------------------------------------------------------------------ Fig. 3
def fig3():
    rows = load("density")
    levels = list(DENSITY_LEVELS)
    fig, ax = plt.subplots(figsize=(COL_W, 2.2))
    n = len(ARMS)
    w = 0.8 / n
    res = {}
    for j, a in enumerate(ARMS):
        name, col = ARM_STYLE[a]
        cc = [ci([100 * r["coverage"] for r in rows if r["level"] == lv and r["arm"] == a]) for lv in levels]
        dd = [np.mean([r["disp"] for r in rows if r["level"] == lv and r["arm"] == a]) for lv in levels]
        res[a] = (cc, dd)
        x = np.arange(len(levels)) - 0.4 + (j + 0.5) * w
        ax.bar(x, [c[0] for c in cc], w * 0.88, yerr=[c[1] for c in cc], color=col, label=name,
               edgecolor=INK2, linewidth=0.3, capsize=1.2, error_kw={"elinewidth": 0.6, "ecolor": INK})
    ax.axhline(100 * TARGET_COVERAGE, color=INK2, lw=0.6, ls="--", label="90% target")
    ax.set_xticks(range(len(levels)), [f"{lv}\n({DENSITY_LEVELS[lv]} clusters)" for lv in levels])
    ax.set_ylabel("Coverage (%)")
    ax.set_ylim(0, 100)
    ax.grid(axis="x", visible=False)
    ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.30), columnspacing=0.6,
              handlelength=1.2)
    save(fig, "fig3_coverage_density")
    key = {"fixed": "Fix", "handover": "Ho", "ho_t2": "HoT", "teramove": "Tm", "greedy": "Gr", "pso": "Pso", "ga": "Ga"}
    for a in ARMS:
        cc, dd = res[a]
        for k, lv in enumerate(levels):
            macro(f"Den{key[a]}Cov{'ABCD'[k]}", f1(cc[k][0]))
            macro(f"Den{key[a]}Ci{'ABCD'[k]}", f1(cc[k][1]))
            macro(f"Den{key[a]}Disp{'ABCD'[k]}", f1(dd[k]))
        allc = [100 * r["coverage"] for r in rows if r["arm"] == a]
        alld = [r["disp"] for r in rows if r["arm"] == a]
        macro(f"Den{key[a]}CovAll", f1(np.mean(allc)))
        macro(f"Den{key[a]}DispAll", f1(np.mean(alld)))
    srt = {a: sorted([r for r in rows if r["arm"] == a], key=lambda r: (r["level"], r["seed"])) for a in ARMS}
    for a in ("pso", "ga", "ho_t2", "handover", "greedy"):
        macro(f"Den{key[a]}CovP", pfmt(pval([r['coverage'] for r in srt['teramove']], [r['coverage'] for r in srt[a]])))
    for a in ("pso", "ga", "greedy"):
        macro(f"Den{key[a]}DispP", pfmt(pval([r['disp'] for r in srt['teramove']], [r['disp'] for r in srt[a]])))
    gain = [100 * (t["coverage"] - h["coverage"]) for t, h in zip(srt["teramove"], srt["handover"])]
    macro("DenTmGainAll", f1(np.mean(gain)))
    fixgap = [100 * (h["coverage"] - f["coverage"]) for h, f in zip(srt["handover"], srt["fixed"])]
    macro("DenHoGainAll", f1(np.mean(fixgap)))
    same = [abs(t["coverage"] - g["coverage"]) < 1e-12 and abs(t["disp"] - g["disp"]) < 1e-9
            for t, g in zip(srt["teramove"], srt["greedy"])]
    macro("DenSeedSame", f1(100 * np.mean(same)))
    macro("DenTmReach", f1(100 * np.mean([r["coverage"] >= TARGET_COVERAGE for r in srt["teramove"]])))
    macro("DenTriggered", f1(100 * np.mean([r["cov_before"] < TARGET_COVERAGE for r in srt["teramove"]])))


def serving_agreement():
    """Share of the crowd (density-weighted) whose strongest AP under the crowd is still
    its design-time AP, over the Fig. 3 crowds."""
    from teramove_eval.run_short import DEN_CROWD, N_SEEDS, commissioned
    routers, serving = commissioned()
    w = []
    for k in DENSITY_LEVELS.values():
        for s in range(N_SEEDS):
            d = density(DEN_CROWD + s, k)
            _, _, used = calculate_sinr(routers, d, WALLS, return_serving=True)
            w.append((d * (used == serving)).sum() / d.sum())
    macro("SameServer", f1(100 * np.mean(w)))


def write_numbers():
    lines = ["% Auto-generated by teramove_eval/make_short_assets.py -- do not edit."]
    lines += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in sorted(NUM.items())]
    (OUT / "numbers.tex").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    commission()
    tiers()
    by = temporal()
    fig2(by)
    fig3()
    serving_agreement()
    write_numbers()
    print(f"{len(NUM)} macros")
