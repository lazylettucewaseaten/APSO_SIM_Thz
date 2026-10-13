"""Figures, tables and number macros of the corrected TeraMove paper.

Reads teramove_eval/results/*.json, writes teramove_paper/figures/*.pdf,
teramove_paper/tables/*.tex and teramove_paper/numbers.tex.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

from chsr_sim.config import TARGET_COVERAGE  # noqa: E402
from chsr_sim.physics import calculate_sinr  # noqa: E402
from teramove_eval.run import (CONFIGS, DENSITY_LEVELS, MILP, RES, WALLS, density,  # noqa: E402
                               load, milp_routers)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "teramove_paper"
FIG, TAB = OUT / "figures", OUT / "tables"
FIG.mkdir(parents=True, exist_ok=True)
TAB.mkdir(parents=True, exist_ok=True)

BLUE, ORANGE, AQUA, GRAY, INK, INK2 = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984", "#0b0b0b", "#52514e"
METHOD = {"hpso": ("HPSO (TeraMove)", BLUE, "o"), "pso": ("Standard PSO", ORANGE, "s"),
          "ga": ("GA", AQUA, "^")}
plt.rcParams.update({
    "font.family": "serif", "font.size": 8, "axes.labelsize": 8, "legend.fontsize": 7,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#e4e3df", "grid.linewidth": 0.5, "axes.edgecolor": INK2,
    "pdf.fonttype": 42, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
})
COL_W = 3.45
NUM = {}


def macro(k, v):
    NUM[k] = v


def f1(x, d=1):
    s = f"{x:.{d}f}"
    return s[1:] if s.startswith("-") and float(s) == 0 else s


def ci(x):
    x = np.asarray(x, float)
    return float(x.mean()), float(stats.t.ppf(0.975, len(x) - 1) * stats.sem(x)) if len(x) > 1 else 0.0


def pval(a, b):
    a, b = np.asarray(a), np.asarray(b)
    if np.allclose(a, b):
        return 1.0
    return float(stats.wilcoxon(a, b).pvalue)


def pfmt(p):
    """Relation and p-value for use inside math mode, e.g. $p\\Macro$ -> p=0.33 or p<0.001."""
    return f"={p:.2f}" if p >= 0.01 else ("<0.01" if p >= 0.001 else "<0.001")


def save(fig, name):
    fig.savefig(FIG / f"{name}.pdf")
    plt.close(fig)


def walls(ax):
    for w in WALLS:
        full = w["h"] >= 3.0
        col = {"solid": INK, "wood": "#8b5a2b", "glass": "#5aa9e6"}[w["m"]] if full else "#c9b28f"
        xs, ys = ([w["s"], w["e"]], [w["p"], w["p"]]) if w["o"] == "h" else ([w["p"], w["p"]], [w["s"], w["e"]])
        ax.plot(xs, ys, color=col, lw=1.2 if full else 0.7, solid_capstyle="butt", zorder=3)


def room_axes(ax):
    ax.set_xlim(0, 32)
    ax.set_ylim(0, 20)
    ax.set_aspect("equal")
    ax.grid(False)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")


def sinr_panel(ax, routers, dens, title=None):
    s, cov = calculate_sinr(routers, dens, WALLS)
    im = ax.imshow(np.clip(s.T, -10, 30), origin="lower", extent=(-0.5, 31.5, -0.5, 19.5), cmap="Blues",
                   vmin=-10, vmax=30)
    walls(ax)
    ax.scatter([r["x"] for r in routers], [r["y"] for r in routers], marker="^", s=14, color=ORANGE,
               edgecolor="white", lw=0.4, zorder=5)
    room_axes(ax)
    if title:
        ax.set_title(title, fontsize=7.5)
    return im, cov


# ------------------------------------------------------------------------ Fig. 1
def fig_static():
    com = load("commission")
    macro("MilpEmptyCov", f1(100 * com["milp_empty_coverage"]))
    macro("CommEmptyCov", f1(100 * com["commissioned_empty_coverage"]))
    fig, ax = plt.subplots(figsize=(COL_W, COL_W * 20 / 32 + 0.2))
    im, cov = sinr_panel(ax, com["routers"], np.zeros((32, 20)))
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.01)
    cb.set_label("SINR (dB)")
    save(fig, "static_sinr")
    # sanity: the figure shows the same coverage as the stored value
    assert abs(cov - com["commissioned_empty_coverage"]) < 1e-12
    _ = milp_routers, MILP


# ------------------------------------------------------------------------ Fig. 2 / Table III
def tiers():
    rows = load("tiers")
    cov = np.array([[e["coverage"] for e in r["log"]] for r in rows]) * 100   # (seeds, 4)
    disp = np.array([[e["disp"] for e in r["log"]] for r in rows])
    nn = np.array([r["log"][-1]["disp_nn"] for r in rows])
    hu = disp[:, -1]
    labels = ["Baseline", "Tier 2", "Tier 3", "Tier 4"]
    m = cov.mean(axis=0)
    fig, axes = plt.subplots(1, 2, figsize=(COL_W, 1.7))
    c_ci = [ci(cov[:, k]) for k in range(4)]
    d_ci = [ci(disp[:, k]) for k in range(4)]
    axes[0].bar(range(4), [c[0] for c in c_ci], yerr=[c[1] for c in c_ci], color=[GRAY, BLUE, BLUE, BLUE],
                width=0.6, capsize=1.5, error_kw={"elinewidth": 0.6})
    axes[0].set_ylabel("Coverage (%)")
    axes[1].bar(range(4), [d[0] for d in d_ci], yerr=[d[1] for d in d_ci], color=[GRAY, BLUE, BLUE, BLUE],
                width=0.6, capsize=1.5, error_kw={"elinewidth": 0.6})
    axes[1].set_ylabel("Cum. displacement (m)")
    for ax in axes:
        ax.set_xticks(range(4), labels, rotation=30)
        ax.grid(axis="x", visible=False)
    for k, (v, h) in enumerate(c_ci):
        axes[0].text(k, v + h + 2, f1(v), ha="center", fontsize=6)
    dmax = max(d[0] + d[1] for d in d_ci)
    for k, (v, h) in enumerate(d_ci):
        axes[1].text(k, v + h + 0.03 * dmax, f1(v), ha="center", fontsize=6)
    axes[0].set_ylim(0, 118)
    axes[1].set_ylim(0, dmax * 1.2)
    fig.tight_layout(w_pad=1.0)
    save(fig, "tiers")
    rnd = [round(x, 1) for x in m]
    lines = [r"\begin{tabular}{@{}lrrr@{}}", r"\toprule",
             r"Tier & Coverage (\%) & Gain (pp) & Cum.\ displ.\ (m)\\", r"\midrule"]
    names = ["Baseline (Tier 1)", "Tier 2 (beams)", "Tier 3 (+ height)", "Tier 4 (+ position)"]
    for k in range(4):
        g = "--" if k == 0 else f1(rnd[k] - rnd[k - 1])
        lines.append(f"{names[k]} & {f1(m[k])}$\\pm${f1(c_ci[k][1])} & {g} & {f1(disp[:, k].mean())} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TAB / "tiers.tex").write_text("\n".join(lines) + "\n")
    macro("TierBase", f1(m[0]))
    macro("TierTwo", f1(m[1]))
    macro("TierThree", f1(m[2]))
    macro("TierFour", f1(m[3]))
    macro("TierGainTwo", f1(rnd[1] - rnd[0]))
    macro("TierGainThree", f1(rnd[2] - rnd[1]))
    macro("TierGainFour", f1(rnd[3] - rnd[2]))
    tot = rnd[3] - rnd[0]
    macro("TierTwoShare", f1(100 * (rnd[1] - rnd[0]) / tot) if tot > 0 else "0.0")
    macro("TierDispThree", f1(disp[:, 2].mean()))
    macro("TierDispFour", f1(disp[:, 3].mean()))
    macro("TierDispTwo", f1(disp[:, 1].mean()))
    macro("HungNN", f1(nn.mean()))
    macro("HungHu", f1(hu.mean()))
    macro("HungSaving", f1(round(nn.mean(), 1) - round(hu.mean(), 1)))
    macro("HungSavingPct", f1(100 * (1 - round(hu.mean(), 1) / round(nn.mean(), 1))))
    macro("HungP", pfmt(pval(nn, hu)))
    macro("TierSeeds", str(len(rows)))
    macro("TierFourReach", f1(100 * np.mean(cov[:, 3] >= 100 * TARGET_COVERAGE)))
    return rows


# ------------------------------------------------------------------------ Fig. 3 / Fig. 4
def temporal():
    rows = load("temporal")
    fig, axes = plt.subplots(1, 2, figsize=(COL_W, 2.0))
    w = 0.26
    for j, mth in enumerate(("hpso", "pso", "ga")):
        rs = [r for r in rows if r["method"] == mth]
        name, col, mk = METHOD[mth]
        cov = np.array([[s["cov_after"] for s in r["steps"]] for r in rs]) * 100
        dsp = np.array([[s["disp"] for s in r["steps"]] for r in rs])
        cc = [ci(cov[:, t]) for t in range(3)]
        dd = [ci(dsp[:, t]) for t in range(3)]
        x = np.arange(3) + (j - 1) * w
        axes[0].bar(x, [c[0] for c in cc], w, yerr=[c[1] for c in cc], color=col, label=name,
                    capsize=1, error_kw={"elinewidth": 0.5})
        axes[1].bar(x, [d[0] for d in dd], w, yerr=[d[1] for d in dd], color=col, label=name,
                    capsize=1, error_kw={"elinewidth": 0.5})
        key = {"hpso": "H", "pso": "P", "ga": "G"}[mth]
        for t in range(3):
            macro(f"Seq{key}Cov{'ABC'[t]}", f1(cc[t][0]))
            macro(f"Seq{key}Disp{'ABC'[t]}", f1(dd[t][0]))
        macro(f"Seq{key}DispTot", f1(dsp.sum(axis=1).mean()))
        macro(f"Seq{key}Reach", f1(100 * np.mean(cov >= 100 * TARGET_COVERAGE)))
        for t in range(3):
            macro(f"Seq{key}Reach{'ABC'[t]}", f1(100 * np.mean(cov[:, t] >= 100 * TARGET_COVERAGE)))
        macro(f"Seq{key}CovAvg", f1(cov.mean()))
        if mth == "hpso":
            before = np.array([[s["cov_before"] for s in r["steps"]] for r in rs]) * 100
            for t in range(3):
                macro(f"SeqBefore{'ABC'[t]}", f1(before[:, t].mean()))
            tiers_ = np.array([[s["tier"] for s in r["steps"]] for r in rs])
            for t in range(3):
                macro(f"SeqTierFour{'ABC'[t]}", f1(100 * np.mean(tiers_[:, t] == 4), 0))
                macro(f"SeqTierLow{'ABC'[t]}", f1(100 * np.mean(tiers_[:, t] <= 2), 0))
    # totals and p-values
    tot = {m: np.array([sum(s["disp"] for s in r["steps"]) for r in sorted(
        [r for r in rows if r["method"] == m], key=lambda r: r["seed"])]) for m in METHOD}
    avg = {m: np.array([np.mean([s["cov_after"] for s in r["steps"]]) for r in sorted(
        [r for r in rows if r["method"] == m], key=lambda r: r["seed"])]) for m in METHOD}
    gaps = [round(100 * avg[m].mean(), 1) - round(100 * avg["hpso"].mean(), 1) for m in ("pso", "ga")]
    macro("SeqCovGapMax", f1(max(abs(g) for g in gaps)))
    for m, k in (("pso", "P"), ("ga", "G")):
        macro(f"Seq{k}DispPval", pfmt(pval(tot["hpso"], tot[m])))
        macro(f"Seq{k}CovPval", pfmt(pval(avg["hpso"], avg[m])))
        macro(f"SeqDispRed{k}", f1(100 * (1 - round(tot["hpso"].mean(), 1) / round(tot[m].mean(), 1))))
    for ax in axes:
        ax.set_xticks(range(3), ["$t_0$", "$t_1$", "$t_2$"])
        ax.set_xlabel("Time step")
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Coverage after (%)")
    axes[0].axhline(100 * TARGET_COVERAGE, color=INK2, lw=0.6, ls="--")
    axes[0].set_ylim(0, 110)
    axes[1].set_ylabel("Displacement (m)")
    h, lab = axes[0].get_legend_handles_labels()
    fig.legend(h, lab, frameon=False, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.06))
    fig.subplots_adjust(wspace=0.45)
    save(fig, "temporal")
    # Fig. 4: six-panel adaptation at t2 (optimiser seed 0; at t1 no adaptation was needed)
    r0 = [r for r in rows if r["method"] == "hpso" and r["seed"] == 0][0]
    s1 = r0["steps"][2]
    d0, d1 = density(1), density(2)
    fig, axes = plt.subplots(2, 3, figsize=(COL_W * 2.05, 3.5))
    sinr_panel(axes[0, 0], s1["routers_before"], np.zeros((32, 20)), "(a) APs before $t_2$ (empty floor)")
    sinr_panel(axes[1, 0], s1["routers_before"], d0, "(b) SINR with the $t_1$ crowd")
    ax = axes[0, 1]
    ax.imshow(d1.T, origin="lower", extent=(-0.5, 31.5, -0.5, 19.5), cmap="Reds", vmin=0, vmax=1)
    walls(ax)
    room_axes(ax)
    ax.set_title("(c) Crowd density $D_h$ at $t_2$", fontsize=7.5)
    _, cb = sinr_panel(axes[1, 1], s1["routers_before"], d1, "(d) $t_2$ crowd, before adaptation")
    sinr_panel(axes[0, 2], s1["routers_after"], np.zeros((32, 20)), "(e) APs after adaptation (empty)")
    im, ca = sinr_panel(axes[1, 2], s1["routers_after"], d1, "(f) $t_2$ crowd, after adaptation")
    for a in axes.ravel():
        a.set_xlabel("")
        a.set_ylabel("")
        a.tick_params(labelsize=6)
    fig.subplots_adjust(hspace=0.32, wspace=0.12)
    cbar = fig.colorbar(im, ax=axes, fraction=0.02, pad=0.01)
    cbar.set_label("SINR (dB)")
    save(fig, "sequence_t2")
    macro("FigFourBefore", f1(100 * cb))
    macro("FigFourAfter", f1(100 * ca))
    macro("FigFourDisp", f1(s1["disp"]))
    macro("FigFourTier", str(s1["tier"]))
    return rows


# ------------------------------------------------------------------------ Fig. 5 / Fig. 6
def density_cmp():
    rows_all = load("density")
    levels = list(DENSITY_LEVELS)
    # Only events whose coverage before adaptation is below the target trigger any method;
    # the triggered seeds are identical for all methods (same crowd, same start).
    trig = {(r["level"], r["seed"]) for r in rows_all if r["method"] == "hpso" and r["cov_before"] < TARGET_COVERAGE}
    rows = [r for r in rows_all if (r["level"], r["seed"]) in trig]
    for k, lv in enumerate(levels):
        macro(f"DenTrig{'ABCD'[k]}", str(sum(1 for (lv_, _) in trig if lv_ == lv)))
    macro("DenTrigAll", str(len(trig)))
    fig, axes = plt.subplots(1, 2, figsize=(COL_W * 2.05, 2.0))
    w = 0.26
    table = {}
    for j, mth in enumerate(("hpso", "pso", "ga")):
        name, col, _ = METHOD[mth]
        cc = [ci([100 * r["coverage"] for r in rows if r["level"] == lv and r["method"] == mth]) for lv in levels]
        dd = [ci([r["disp"] for r in rows if r["level"] == lv and r["method"] == mth]) for lv in levels]
        table[mth] = (cc, dd)
        x = np.arange(len(levels)) + (j - 1) * w
        axes[0].bar(x, [c[0] for c in cc], w, yerr=[c[1] for c in cc], color=col, label=name, capsize=1,
                    error_kw={"elinewidth": 0.5})
        axes[1].bar(x, [d[0] for d in dd], w, yerr=[d[1] for d in dd], color=col, label=name, capsize=1,
                    error_kw={"elinewidth": 0.5})
    before = [np.mean([100 * r["cov_before"] for r in rows if r["level"] == lv and r["method"] == "hpso"])
              for lv in levels]
    axes[0].plot(np.arange(len(levels)), before, color=INK2, marker="x", ls=":", lw=1, label="Before adaptation")
    for ax in axes:
        ax.set_xticks(range(len(levels)), [f"{lv} ({DENSITY_LEVELS[lv]})" for lv in levels], rotation=12)
        ax.set_xlabel("Crowd level (number of clusters)")
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Density-weighted coverage (%)")
    axes[0].set_ylim(0, 110)
    axes[1].set_ylabel("Total displacement (m)")
    h, lab = axes[0].get_legend_handles_labels()
    fig.legend(h, lab, frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.06))
    fig.subplots_adjust(wspace=0.25)
    save(fig, "density")
    for k, lv in enumerate(levels):
        tag = "ABCD"[k]
        macro(f"DenBefore{tag}", f1(before[k]))
        for mth, mk in (("hpso", "H"), ("pso", "P"), ("ga", "G")):
            macro(f"Den{mk}Cov{tag}", f1(table[mth][0][k][0]))
            macro(f"Den{mk}Disp{tag}", f1(table[mth][1][k][0]))
    hp = {m: [r for r in sorted(rows, key=lambda r: (r["level"], r["seed"])) if r["method"] == m]
          for m in METHOD}
    for m, k in (("pso", "P"), ("ga", "G")):
        macro(f"Den{k}CovPval", pfmt(pval([r["coverage"] for r in hp["hpso"]], [r["coverage"] for r in hp[m]])))
        macro(f"Den{k}DispPval", pfmt(pval([r["disp"] for r in hp["hpso"]], [r["disp"] for r in hp[m]])))
        h_d, o_d = np.mean([r["disp"] for r in hp["hpso"]]), np.mean([r["disp"] for r in hp[m]])
        macro(f"DenDispRed{k}", f1(100 * (1 - round(h_d, 1) / round(o_d, 1))))
        h_c, o_c = np.mean([r["coverage"] for r in hp["hpso"]]), np.mean([r["coverage"] for r in hp[m]])
        macro(f"DenCovDiff{k}", f1(round(100 * h_c, 1) - round(100 * o_c, 1)))
        macro(f"DenCovGap{k}", f1(round(100 * o_c, 1) - round(100 * h_c, 1)))
    macro("DenHCovAll", f1(100 * np.mean([r["coverage"] for r in hp["hpso"]])))
    macro("DenPCovAll", f1(100 * np.mean([r["coverage"] for r in hp["pso"]])))
    macro("DenGCovAll", f1(100 * np.mean([r["coverage"] for r in hp["ga"]])))
    macro("DenHDispAll", f1(np.mean([r["disp"] for r in hp["hpso"]])))
    macro("DenPDispAll", f1(np.mean([r["disp"] for r in hp["pso"]])))
    macro("DenGDispAll", f1(np.mean([r["disp"] for r in hp["ga"]])))

    # convergence at the default density ("High", 9 clusters)
    tiers_rows = load("tiers")
    S = 50
    fig, ax = plt.subplots(figsize=(COL_W, 1.9))
    curves = {}
    curves["hpso"] = np.mean([r["history"] for r in tiers_rows], axis=0)
    conv = load("convergence")
    for m in ("pso", "ga"):
        hs = [r["history"] for r in conv if r["method"] == m]
        assert len(hs) == len(tiers_rows)
        curves[m] = np.mean(hs, axis=0)
    finals = {}
    for m, c in curves.items():
        name, col, mk = METHOD[m]
        x = np.arange(1, len(c) + 1) * S
        ax.plot(x, c, color=col, marker=mk, markevery=max(1, len(c) // 6), ms=3, label=name)
        finals[m] = c[-1]
    ax.set_xlabel("Fitness evaluations")
    ax.set_ylabel("Best fitness $F$ (mean)")
    ax.legend(frameon=False, loc="lower right")
    save(fig, "convergence")
    for m, k in (("hpso", "H"), ("pso", "P"), ("ga", "G")):
        macro(f"Conv{k}Final", f1(finals[m], 3))
    macro("ConvSeeds", str(len(tiers_rows)))


# ------------------------------------------------------------------------ Table IV
def sensitivity():
    rows = load("sensitivity")
    lines = [r"\begin{tabular}{@{}lrrrrrr@{}}", r"\toprule",
             r"Config. & $w_c$ & $w_d$ & $\beta$ & $\gamma$ & Avg.\ cov.\ (\%) & Total disp.\ (m)\\",
             r"\midrule"]
    res = {}
    for c, (wc, wd, b, g) in CONFIGS.items():
        rs = [r for r in rows if r["cfg"] == c]
        cv, dp = ci([100 * r["avg_cov"] for r in rs]), ci([r["total_disp"] for r in rs])
        res[c] = (cv, dp)
        lines.append(f"{c} & {wc} & {wd} & {b} & {g} & {f1(cv[0])}$\\pm${f1(cv[1])} & "
                     f"{f1(dp[0])}$\\pm${f1(dp[1])} \\\\")
        macro(f"Sens{c}Cov", f1(cv[0]))
        macro(f"Sens{c}Disp", f1(dp[0]))
    macro("SensCovMin", f1(min(v[0][0] for v in res.values())))
    macro("SensCovMax", f1(max(v[0][0] for v in res.values())))
    macro("SensDispMin", f1(min(v[1][0] for v in res.values())))
    macro("SensDispMax", f1(max(v[1][0] for v in res.values())))
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TAB / "sensitivity.tex").write_text("\n".join(lines) + "\n")
    srt = {c: sorted([r for r in rows if r["cfg"] == c], key=lambda r: r["seed"]) for c in CONFIGS}
    ps = []
    for c in "ABC":
        for k in ("avg_cov", "total_disp"):
            ps.append(pval([r[k] for r in srt[c]], [r[k] for r in srt["D"]]))
    macro("SensMinP", f"{min(ps):.2f}")
    return res


def write_numbers():
    lines = ["% Auto-generated by teramove_eval/make_assets.py -- do not edit."]
    lines += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in sorted(NUM.items())]
    (OUT / "numbers.tex").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    fig_static()
    tiers()
    temporal()
    density_cmp()
    sens = sensitivity()
    write_numbers()
    print(f"{len(NUM)} macros")
    for c, (cv, dp) in sens.items():
        print(c, cv, dp)
    print("RES", RES)
