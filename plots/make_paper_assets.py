"""Build every figure, table and number used in the paper from results/*.json.

Nothing in the paper is typed by hand: figures go to paper/figures/, LaTeX
tables to paper/tables/, scalar numbers to paper/numbers.tex as macros.
"""
import json
import math
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Wedge  # noqa: E402

from experiments.common import commission, mean_ci, wilcoxon_p  # noqa: E402
from teramove_h.antenna import ap_main_gain_dbi, ue_main_lobe_halfangle_deg  # noqa: E402
from teramove_h.config import CANDIDATE_ALPHA, DEFAULT as P  # noqa: E402
from teramove_h.crowd import generate_crowd  # noqa: E402
from teramove_h.geometry import WALLS, WIFI_POSITIONS  # noqa: E402
from teramove_h.network import Scenario, grid_coverage  # noqa: E402
from experiments.common import rng_for  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = Path(os.environ.get("TMH_RESULTS", ROOT / "results"))
FIG = ROOT / "paper" / "figures"
TAB = ROOT / "paper" / "tables"
FIG.mkdir(parents=True, exist_ok=True)
TAB.mkdir(parents=True, exist_ok=True)

# Validated categorical slots (dataviz reference palette, light mode) + neutral.
BLUE, ORANGE, AQUA, VIOLET, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7", "#8a8984"
INK, INK2 = "#0b0b0b", "#52514e"
plt.rcParams.update({
    "font.family": "serif", "font.size": 8, "axes.labelsize": 8, "legend.fontsize": 7,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "axes.edgecolor": INK2, "axes.labelcolor": INK,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#e4e3df", "grid.linewidth": 0.5, "lines.linewidth": 1.5,
    "pdf.fonttype": 42, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
})
COL_W = 3.45  # IEEE column width (in)

LABEL = {
    "static": "Static", "wifi_only": "Wi-Fi only", "teramove": "TeraMove",
    "thz_only": "THz-only cascade", "naive": "Threshold offload", "flat_pso": "Flat PSO",
    "ga": "Flat GA", "proposed": "TeraMove-H", "proposed_nopc": "w/o power ctrl",
    "proposed_nomove": "w/o movement", "proposed_hpso": "w/ HPSO tiers",
    "proposed_greedy": "w/ greedy assoc.",
}
NUM = {}


def load(name):
    p = RES / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def macro(name, value):
    NUM[name] = value


def fmt(x, d=1):
    out = f"{x:.{d}f}"
    return out[1:] if out.startswith("-") and float(out) == 0 else out   # no "-0.0"


def pfmt(p):
    """p-value for LaTeX text: two decimals, or a power-of-ten bound below 0.001."""
    if p >= 0.01:
        return f"{p:.2f}"
    if p >= 0.001:
        return f"{p:.3f}"
    e = math.ceil(math.log10(p))
    return f"$<10^{{{e}}}$"


def by(rows, **kw):
    return [r for r in rows if all(r.get(k) == v for k, v in kw.items())]


def save(fig, name):
    fig.savefig(FIG / f"{name}.pdf")
    plt.close(fig)


# ----------------------------------------------------------------------- floor plan
def draw_walls(ax):
    for o, p, s, e, h, m in WALLS:
        full = h >= 3.0 - 1e-9
        col = {0: INK, 1: "#8b5a2b", 2: "#5aa9e6"}[int(m)] if full else "#c9b28f"
        lw = 1.4 if full else 0.8
        if o == 0:
            ax.plot([s, e], [p, p], color=col, lw=lw, solid_capstyle="butt", zorder=2)
        else:
            ax.plot([p, p], [s, e], color=col, lw=lw, solid_capstyle="butt", zorder=2)


def fig_layout():
    cfg, _ = commission()
    sc = Scenario(P, generate_crowd(rng_for(0, "crowd"), P.crowd))
    fig, ax = plt.subplots(figsize=(COL_W, COL_W * 20 / 32 + 0.35))
    smap, cov, _ = grid_coverage(P, cfg, sc.true_view)
    im = ax.imshow(np.clip(smap.T, -10, 30), origin="lower", extent=(0, 32, 0, 20), cmap="Blues",
                   vmin=-10, vmax=30, alpha=0.85, zorder=0)
    draw_walls(ax)
    for i in range(cfg.n):
        a = np.radians(cfg.alpha[i])
        mid = 90.0 - cfg.phi[i]                     # compass -> math angle for drawing
        ax.add_patch(Wedge((cfg.x[i], cfg.y[i]), 1.6, mid - np.degrees(a) / 2, mid + np.degrees(a) / 2,
                           facecolor=ORANGE, alpha=0.35, edgecolor="none", zorder=3))
    ax.scatter(cfg.x, cfg.y, s=16, marker="^", color=ORANGE, edgecolor="white", lw=0.5, zorder=5,
               label="THz AP")
    ax.scatter(WIFI_POSITIONS[:, 0], WIFI_POSITIONS[:, 1], s=22, marker="s", color=VIOLET,
               edgecolor="white", lw=0.5, zorder=5, label="Wi-Fi AP")
    cr = sc.truth
    ax.scatter(cr.xy[~cr.active, 0], cr.xy[~cr.active, 1], s=3, color=INK2, zorder=4, label="Person")
    ax.scatter(cr.xy[cr.active, 0], cr.xy[cr.active, 1], s=5, color="#e34948", zorder=4, label="Active user")
    ax.set_xlim(0, 32)
    ax.set_ylim(0, 20)
    ax.set_aspect("equal")
    ax.grid(False)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.01)
    cb.set_label("THz SINR (dB)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.13), ncol=4, frameon=False, handletextpad=0.2,
              columnspacing=0.8)
    save(fig, "layout")
    macro("LayoutSeedCov", fmt(100 * cov))


# ----------------------------------------------------------------------- E1
def legacy_numbers():
    d = load("legacy")
    rows = d["rows"]
    get = lambda **kw: by(rows, **kw)[0]["coverage"] * 100  # noqa: E731
    macro("LegacyCovMath", fmt(get(model="legacy", convention="legacy_math")))
    macro("LegacyCovCompass", fmt(get(model="legacy", convention="compass")))
    macro("MilpCovCorrected", fmt(get(model="corrected", layout="milp")))
    macro("CommissionedCov", fmt(get(model="corrected", layout="commissioned")))


# ----------------------------------------------------------------------- E2
MAIN_ORDER = ["static", "wifi_only", "teramove", "thz_only", "naive", "flat_pso", "ga",
              "proposed_hpso", "proposed_greedy", "proposed_nopc", "proposed_nomove", "proposed"]


def main_results():
    d = load("main")
    rows = d["rows"]
    seeds = sorted({r["seed"] for r in rows})
    stats = {}
    ref = {r["seed"]: r for r in by(rows, method="proposed")}
    for m in MAIN_ORDER:
        rs = sorted(by(rows, method=m), key=lambda r: r["seed"])
        if not rs:
            continue
        s = [100 * r["satisfaction"] for r in rs]
        stats[m] = {
            "S": mean_ci(s), "disp": mean_ci([r["displacement_m"] for r in rs]),
            "moved": np.mean([r["n_moved"] for r in rs]),
            "lat": np.mean([r["latency_s"] for r in rs]),
            "pw": mean_ci([r["p_sum_w"] for r in rs]),
            "sleep": np.mean([r["n_asleep"] for r in rs]),
            "evals": np.mean([r["evals"] for r in rs]),
            "rt": np.mean([r["runtime_s"] for r in rs]),
            "thz": np.mean([r["n_thz_served"] for r in rs]),
            "wifi": np.mean([r["n_wifi_served"] for r in rs]),
            "users": np.mean([r["n_users"] for r in rs]),
            "p_S": wilcoxon_p(s, [100 * ref[r["seed"]]["satisfaction"] for r in rs]) if m != "proposed" else None,
            "p_D": wilcoxon_p([r["displacement_m"] for r in rs],
                              [ref[r["seed"]]["displacement_m"] for r in rs]) if m != "proposed" else None,
            "T0": mean_ci([100 * r["stages"][0][1] for r in rs]),
        }
    # Table
    lines = [r"\begin{tabular}{@{}lrrrrr@{}}", r"\toprule",
             r"Method & $S$ (\%) & Displ. (m) & $\sum p$ (W) & Off & Evals \\", r"\midrule"]
    for m in MAIN_ORDER:
        if m not in stats:
            continue
        st = stats[m]
        name = LABEL[m] if m != "proposed" else r"\textbf{TeraMove-H}"
        if m == "proposed_hpso":
            lines.append(r"\midrule")
        lines.append(f"{name} & {st['S'][0]:.1f}$\\pm${st['S'][1]:.1f} & {st['disp'][0]:.1f} & "
                     f"{st['pw'][0]:.2f} & {st['sleep']:.1f} & {st['evals']:.0f} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TAB / "main.tex").write_text("\n".join(lines) + "\n")

    def put(prefix, m):
        st = stats[m]
        macro(prefix + "S", fmt(st["S"][0]))
        macro(prefix + "SCI", fmt(st["S"][1]))
        macro(prefix + "Disp", fmt(st["disp"][0]))
        macro(prefix + "Pw", fmt(st["pw"][0], 2))
        macro(prefix + "Sleep", fmt(st["sleep"]))
        macro(prefix + "Moved", fmt(st["moved"]))
        macro(prefix + "Lat", fmt(st["lat"]))
        macro(prefix + "Rt", fmt(st["rt"]))
        macro(prefix + "Wifi", fmt(st["wifi"]))
        macro(prefix + "Thz", fmt(st["thz"]))
        if st["p_S"] is not None:
            macro(prefix + "PS", pfmt(st["p_S"]))
            macro(prefix + "PD", pfmt(st["p_D"]))
    for m, pre in (("static", "Static"), ("wifi_only", "Wifi"), ("teramove", "Tm"), ("thz_only", "Thz"),
                   ("naive", "Naive"), ("flat_pso", "Fpso"), ("ga", "Ga"), ("proposed", "Prop"),
                   ("proposed_nopc", "Nopc"), ("proposed_nomove", "Nomove"), ("proposed_hpso", "Hpso"),
                   ("proposed_greedy", "Greedy")):
        if m in stats:
            put(pre, m)
    macro("MainSeeds", str(len(seeds)))
    macro("MainUsers", fmt(stats["proposed"]["users"]))
    macro("PropTzero", fmt(stats["proposed"]["T0"][0]))
    # Derived numbers use the rounded values printed in the paper, so a reader who
    # recomputes them from the tables gets exactly the same result.
    r1 = lambda x: round(x, 1)  # noqa: E731
    r2 = lambda x: round(x, 2)  # noqa: E731
    S_ = {m: r1(stats[m]["S"][0]) for m in stats}
    D_ = {m: r1(stats[m]["disp"][0]) for m in stats}
    macro("PowerSaving", fmt(100 * (1 - r2(stats["proposed"]["pw"][0]) / r2(stats["static"]["pw"][0]))))
    macro("DispReductionVsGa", fmt(100 * (1 - D_["proposed"] / D_["ga"])))
    macro("GainVsTm", fmt(S_["proposed"] - S_["teramove"]))
    macro("GainVsStatic", fmt(S_["proposed"] - S_["static"]))
    macro("GainVsThz", fmt(S_["proposed"] - S_["thz_only"]))
    macro("GapToGa", fmt(S_["ga"] - S_["proposed"]))

    # Figure: satisfaction and displacement (two panels, shared method axis)
    order = [m for m in MAIN_ORDER if m in stats]
    fig, axes = plt.subplots(1, 2, figsize=(COL_W * 2.05, 2.0), sharey=True)
    ypos = np.arange(len(order))
    colors = [BLUE if m == "proposed" else (AQUA if m.startswith("proposed_") else GRAY) for m in order]
    for ax, key, xl in ((axes[0], "S", "Satisfied users $S$ (%)"), (axes[1], "disp", "Total AP displacement (m)")):
        vals = [stats[m][key][0] for m in order]
        errs = [stats[m][key][1] for m in order]
        ax.barh(ypos, vals, xerr=errs, color=colors, height=0.62, edgecolor="white", lw=0.5,
                error_kw={"elinewidth": 0.7, "capsize": 1.5, "ecolor": INK2})
        for y, v in zip(ypos, vals):
            ax.text(v + max(vals) * 0.02 + (errs[y] if errs[y] else 0), y, fmt(v), va="center",
                    fontsize=6.5, color=INK)
        ax.set_xlabel(xl)
        ax.grid(axis="y", visible=False)
        ax.set_xlim(0, max(vals) * 1.22)
    axes[0].set_yticks(ypos, [LABEL[m] for m in order])
    axes[0].invert_yaxis()
    save(fig, "main_bars")

    # Pareto scatter (ablation "w/o power ctrl" coincides with TeraMove-H and is omitted)
    pareto = ["static", "teramove", "thz_only", "naive", "flat_pso", "ga", "proposed_hpso",
              "proposed_nomove", "proposed"]
    offs = {"static": (5, -3), "teramove": (5, -9), "proposed_hpso": (-62, -2),
            "proposed_nomove": (5, -3), "ga": (6, 2)}
    # crowded cluster: labels placed in free space (data coordinates) with leader lines
    callout = {"proposed": (10.5, 90.0), "naive": (8.5, 84.5), "flat_pso": (29.5, 80.0),
               "thz_only": (28.0, 71.5)}
    fig, ax = plt.subplots(figsize=(COL_W, 2.3))
    for m in pareto:
        st = stats[m]
        c = BLUE if m == "proposed" else (AQUA if m.startswith("proposed_") else GRAY)
        ax.errorbar(st["disp"][0], st["S"][0], xerr=st["disp"][1], yerr=st["S"][1], fmt="o",
                    color=c, ms=4, elinewidth=0.6, capsize=1.2, mec="white", mew=0.5, zorder=3)
        if m in callout:
            ax.annotate(LABEL[m], (st["disp"][0], st["S"][0]), xytext=callout[m], textcoords="data",
                        fontsize=6, color=INK, zorder=4,
                        arrowprops={"arrowstyle": "-", "color": INK2, "lw": 0.5, "shrinkB": 3})
        else:
            ax.annotate(LABEL[m], (st["disp"][0], st["S"][0]), textcoords="offset points",
                        xytext=offs[m], fontsize=6, color=INK, zorder=4)
    ax.set_xlabel("Total AP displacement (m)")
    ax.set_ylabel("Satisfied users $S$ (%)")
    ax.set_xlim(-2, max(stats[m]["disp"][0] + stats[m]["disp"][1] for m in pareto) + 4)
    save(fig, "pareto")
    return stats


# ----------------------------------------------------------------------- convergence
def convergence():
    rows = load("main")["rows"]
    unit = P.opt.swarm * P.opt.iters
    fig, ax = plt.subplots(figsize=(COL_W, 2.0))
    out = {}
    for m, c, mk in (("proposed", BLUE, "o"), ("ga", ORANGE, "s"), ("flat_pso", AQUA, "^"),
                     ("proposed_hpso", VIOLET, "D")):
        curves = []
        for r in by(rows, method=m):
            cv = r["curves"]
            if not cv:
                continue
            if "flat" in cv:
                seq = cv["flat"]
                per = P.opt.swarm
                x = np.arange(1, len(seq) + 1) * per
            else:
                seq, x, off = [], [], 0
                for k in sorted(cv, key=int):
                    c_ = cv[k]
                    per = P.opt.swarm
                    seq += c_
                    x += list(off + np.arange(1, len(c_) + 1) * per)
                    off = x[-1]
                x = np.array(x)
            # best-so-far on a common evaluation grid (step function)
            grid = np.arange(per, 4 * unit + 1, per)
            y = np.array([seq[np.searchsorted(x, g, side="right") - 1] if g >= x[0] else np.nan
                          for g in grid])
            y = np.where(grid > x[-1], seq[-1], y)
            curves.append(np.maximum.accumulate(np.nan_to_num(y, nan=-np.inf)))
        if not curves:
            continue
        cm = np.mean(curves, axis=0)
        ax.plot(grid, cm, color=c, label=LABEL[m], marker=mk, markevery=len(grid) // 6, ms=3)
        out[m] = (len(curves), cm[-1])
    ax.set_xlabel("Fitness evaluations")
    ax.set_ylabel("Best fitness (mean)")
    ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=4,
              handletextpad=0.3, columnspacing=0.8)
    save(fig, "convergence")
    return out


# ----------------------------------------------------------------------- E3 regime
def regime():
    d = load("regime")
    if d is None:
        return
    rows, meta = d["rows"], d["meta"]
    R, N = meta["r_min"], meta["n_people"]
    eta = P.opt.target_satisfaction
    S = np.zeros((len(R), len(N)))
    E = np.zeros_like(S)      # fraction resolved electronically (S >= eta with zero displacement)
    D = np.zeros_like(S)
    G = np.zeros_like(S)      # flat GA displacement
    T0 = np.zeros_like(S)
    for i, r in enumerate(R):
        for j, n in enumerate(N):
            rs = by(rows, method="proposed", r_min=r, n_people=n)
            S[i, j] = 100 * np.mean([x["satisfaction"] for x in rs])
            E[i, j] = 100 * np.mean([(x["displacement_m"] == 0 and x["satisfaction"] >= eta) for x in rs])
            D[i, j] = np.mean([x["displacement_m"] for x in rs])
            T0[i, j] = 100 * np.mean([x["stages"][0][1] for x in rs])
            G[i, j] = np.mean([x["displacement_m"] for x in by(rows, method="ga", r_min=r, n_people=n)])
    fig, axes = plt.subplots(1, 3, figsize=(COL_W * 2.05, 1.75))
    for ax, M, title, fmt_ in ((axes[0], S, "TeraMove-H: satisfied users $S$ (%)", "{:.0f}"),
                               (axes[1], E, "Resolved without moving (%)", "{:.0f}"),
                               (axes[2], D, "TeraMove-H displacement (m)", "{:.1f}")):
        ax.imshow(M, cmap="Blues", aspect="auto", origin="lower")
        for i in range(len(R)):
            for j in range(len(N)):
                v = M[i, j]
                frac = (v - M.min()) / (M.max() - M.min() + 1e-12)
                ax.text(j, i, fmt_.format(v), ha="center", va="center", fontsize=6.5,
                        color="white" if frac > 0.55 else INK)
        ax.set_xticks(range(len(N)), [str(n) for n in N])
        ax.set_yticks(range(len(R)), [f"{r / 1e9:g}" for r in R])
        ax.set_xlabel("People in building")
        ax.set_title(title, fontsize=7.5)
        ax.grid(False)
    axes[0].set_ylabel("Demand $R_{\\min}$ (Gb/s)")
    for ax in axes[1:]:
        ax.set_yticklabels([])
    save(fig, "regime")
    macro("RegimeElecMax", fmt(E.max(), 0))
    macro("RegimeElecLowDemand", fmt(np.mean(E[0]), 0))
    macro("RegimeElecHighDemand", fmt(np.mean(E[-1]), 0))
    macro("RegimeSMin", fmt(S.min()))
    macro("RegimeSMax", fmt(S.max()))
    macro("RegimeSLowDemand", fmt(np.mean(S[0])))
    macro("RegimeDispRatio", fmt(100 * (1 - D.sum() / G.sum())))   # over all 20 grid cells
    macro("RegimeTzeroLow", fmt(np.mean(T0[0])))
    macro("RegimeTzeroHigh", fmt(np.mean(T0[-1])))
    # thz-only vs proposed at each demand (mean over crowd sizes)
    lines = [r"\begin{tabular}{@{}lrrrrr@{}}", r"\toprule",
             r"$R_{\min}$ (Gb/s) & " + " & ".join(f"{r / 1e9:g}" for r in R) + r" \\", r"\midrule"]
    for m in ("thz_only", "naive", "proposed", "ga"):
        vals = [100 * np.mean([x["satisfaction"] for x in by(rows, method=m, r_min=r)]) for r in R]
        lines.append(LABEL[m] + " $S$ (\\%) & " + " & ".join(fmt(v) for v in vals) + r" \\")
    for m in ("proposed", "ga"):
        vals = [np.mean([x["displacement_m"] for x in by(rows, method=m, r_min=r)]) for r in R]
        lines.append(LABEL[m] + " displ. (m) & " + " & ".join(fmt(v) for v in vals) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TAB / "regime.tex").write_text("\n".join(lines) + "\n")
    wifi_gain = [100 * (np.mean([x["satisfaction"] for x in by(rows, method="proposed", r_min=r)])
                        - np.mean([x["satisfaction"] for x in by(rows, method="thz_only", r_min=r)]))
                 for r in R]
    gap_gain = [round(100 * np.mean([x["satisfaction"] for x in by(rows, method="proposed", r_min=r)]), 1)
                - round(100 * np.mean([x["satisfaction"] for x in by(rows, method="naive", r_min=r)]), 1)
                for r in R]
    for r, g in zip(R, gap_gain):
        L = {0.1e9: "A", 0.25e9: "B", 0.5e9: "C", 1e9: "D", 2e9: "E"}[r]
        macro("GapVsNaive" + L, fmt(g))
        pr = sorted(by(rows, method="proposed", r_min=r), key=lambda x: (x["seed"], x["n_people"]))
        nv = sorted(by(rows, method="naive", r_min=r), key=lambda x: (x["seed"], x["n_people"]))
        pval = wilcoxon_p([x["satisfaction"] for x in pr], [x["satisfaction"] for x in nv])
        macro("GapVsNaiveP" + L, pfmt(pval))
        if L != "E" and pval >= 1e-3:
            raise RuntimeError("paper states p < 1e-3 for PACE vs threshold offload at 0.1-1 Gb/s")
    macro("WifiGainLow", fmt(wifi_gain[0]))
    macro("WifiGainHigh", fmt(wifi_gain[-1]))
    pace_vs_greedy(rows, R, eta)


RLET = {0.1e9: "A", 0.25e9: "B", 0.5e9: "C", 1e9: "D", 2e9: "E"}


def pace_vs_greedy(rows, R, eta):
    """PACE versus greedy association inside the same cascade (paired by seed and crowd).

    T0 runs at the same starting geometry for both, so its difference isolates the
    association algorithm; the final S and displacement include the search."""
    key = lambda x: (x["seed"], x["n_people"], x["r_min"])  # noqa: E731
    pg = {key(x): x for x in by(rows, method="proposed_greedy")}
    lines = [r"\begin{tabular}{@{}lrrrrr@{}}", r"\toprule",
             r"$R_{\min}$ (Gb/s) & " + " & ".join(f"{r / 1e9:g}" for r in R) + r" \\", r"\midrule"]
    t0p, t0g, sp, sg, dp, dg, ep, eg, pv = ([] for _ in range(9))
    for r in R:
        pr = by(rows, method="proposed", r_min=r)
        gr = [pg[key(x)] for x in pr]
        t0p.append(100 * np.mean([x["stages"][0][1] for x in pr]))
        t0g.append(100 * np.mean([x["stages"][0][1] for x in gr]))
        sp.append(100 * np.mean([x["satisfaction"] for x in pr]))
        sg.append(100 * np.mean([x["satisfaction"] for x in gr]))
        dp.append(np.mean([x["displacement_m"] for x in pr]))
        dg.append(np.mean([x["displacement_m"] for x in gr]))
        ep.append(100 * np.mean([x["displacement_m"] == 0 and x["satisfaction"] >= eta for x in pr]))
        eg.append(100 * np.mean([x["displacement_m"] == 0 and x["satisfaction"] >= eta for x in gr]))
        pv.append(wilcoxon_p([x["satisfaction"] for x in pr], [x["satisfaction"] for x in gr]))
    for name, vp, vg, d in (("T0 $S$ (\\%)", t0p, t0g, 1), ("Final $S$ (\\%)", sp, sg, 1),
                            ("No movement (\\%)", ep, eg, 0), ("Displ. (m)", dp, dg, 1)):
        lines.append(name + " & " + " & ".join(f"{fmt(a_, d)}/{fmt(b_, d)}" for a_, b_ in zip(vp, vg))
                     + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TAB / "pace_regime.tex").write_text("\n".join(lines) + "\n")
    for i, r in enumerate(R):
        L = RLET[r]
        macro("PaceTzeroGain" + L, fmt(round(t0p[i], 1) - round(t0g[i], 1)))
        macro("PaceSGain" + L, fmt(round(sp[i], 1) - round(sg[i], 1)))
        macro("PaceSP" + L, pfmt(pv[i]))
        macro("PaceElec" + L, fmt(ep[i], 0))
        macro("GreedyElec" + L, fmt(eg[i], 0))
        macro("PaceDisp" + L, fmt(dp[i]))
        macro("GreedyDisp" + L, fmt(dg[i]))
    macro("PaceSPMinRest", pfmt(min(pv[1:])))
    rt = [np.mean([x["runtime_s"] for x in by(rows, method=m_, r_min=R[0])]) for m_ in ("proposed", "proposed_greedy")]
    macro("PaceRtRatioA", fmt(rt[0] / rt[1]))
    # Certified escalation: share of snapshots that leave T0 for which the PACE dual
    # bound proves that no association at the starting geometry reaches eta.
    pr = by(rows, method="proposed")
    esc = [x for x in pr if x["stages"][0][1] < eta]
    nec = [x for x in esc if np.floor(x["t0_ub"] + 1e-9) < eta * x["n_users"] - 1e-9]
    macro("EscN", str(len(esc)))
    macro("EscCertPct", fmt(100 * len(nec) / max(len(esc), 1)))
    macro("TzeroCertPct", fmt(100 * np.mean([x["t0_certified"] for x in pr])))


# ----------------------------------------------------------------------- E4 temporal
def temporal():
    d = load("temporal")
    if d is None:
        return
    rows = d["rows"]
    ep = sorted({r["epoch"] for r in rows})
    fig, axes = plt.subplots(2, 1, figsize=(COL_W, 3.3), sharex=True)
    stats = {}
    for m, c, mk in (("static", GRAY, "x"), ("teramove", AQUA, "^"), ("ga", ORANGE, "s"),
                     ("proposed", BLUE, "o")):
        S = [mean_ci([100 * r["satisfaction"] for r in by(rows, method=m, epoch=e)]) for e in ep]
        seeds = sorted({r["seed"] for r in by(rows, method=m)})
        cum = np.array([np.cumsum([by(rows, method=m, epoch=e, seed=s)[0]["displacement_m"] for e in ep])
                        for s in seeds])
        axes[0].errorbar(ep, [s[0] for s in S], yerr=[s[1] for s in S], color=c, marker=mk, ms=3,
                         capsize=1.5, elinewidth=0.6, label=LABEL[m])
        axes[1].plot(ep, cum.mean(axis=0), color=c, marker=mk, ms=3, label=LABEL[m])
        ho = [r.get("ho_total", 0) for r in by(rows, method=m) if r["epoch"] > 0]
        hv = [r.get("ho_vertical", 0) for r in by(rows, method=m) if r["epoch"] > 0]
        sb = [r.get("served_both", 0) for r in by(rows, method=m) if r["epoch"] > 0]
        stats[m] = {"S": np.mean([s[0] for s in S]), "cum": cum.mean(axis=0)[-1],
                    "ho": 100 * np.sum(ho) / max(np.sum(sb), 1), "hv": 100 * np.sum(hv) / max(np.sum(sb), 1),
                    "pw": np.mean([r["p_sum_w"] for r in by(rows, method=m)])}
    axes[0].set_ylabel("Satisfied users $S$ (%)")
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("Cumulative displ. (m)")
    axes[0].legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=4,
                   handletextpad=0.3, columnspacing=0.8)
    save(fig, "temporal")
    for m, pre in (("static", "TStatic"), ("teramove", "TTm"), ("ga", "TGa"), ("proposed", "TProp")):
        if m in stats:
            macro(pre + "S", fmt(stats[m]["S"]))
            macro(pre + "Cum", fmt(stats[m]["cum"]))
            macro(pre + "Ho", fmt(stats[m]["ho"]))
            macro(pre + "Hv", fmt(stats[m]["hv"]))
            macro(pre + "Pw", fmt(stats[m]["pw"], 2))
    macro("TEpochs", str(len(ep)))
    if "ga" in stats and "proposed" in stats:
        macro("TCumReduction", fmt(100 * (1 - round(stats["proposed"]["cum"], 1) / round(stats["ga"]["cum"], 1))))


# ----------------------------------------------------------------------- E5 association
def assoc():
    d = load("assoc")
    if d is None:
        return
    rows = d["rows"]
    g = np.array([r["greedy"] for r in rows])
    p = np.array([r["pace"] for r in rows])
    e = np.array([r["exact"] for r in rows])
    cert = np.array([r["certified"] for r in rows])
    ub = np.array([r["ub"] for r in rows])
    if np.any(p < g) or np.any(p > e) or np.any(ub < e - 1e-9) or np.any(cert & (p != e)):
        raise RuntimeError("PACE property violated in results/assoc.json")
    macro("AssocInstances", str(len(rows)))
    macro("AssocOptimalPct", fmt(100 * np.mean(g == e)))
    macro("AssocPaceOptimalPct", fmt(100 * np.mean(p == e)))
    macro("AssocCertPct", fmt(100 * np.mean(cert)))
    macro("AssocShortGreedy", str(int(np.sum(e - g))))
    macro("AssocShortPace", str(int(np.sum(e - p))))
    macro("AssocShortReduction", fmt(100 * (1 - np.sum(e - p) / np.sum(e - g))))
    pos = e > 0
    macro("AssocWorstRatio", fmt(100 * np.min(g[pos] / e[pos])))
    macro("AssocPaceWorstRatio", fmt(100 * np.min(p[pos] / e[pos])))
    for name, gap in (("AssocMaxGap", e - g), ("AssocPaceMaxGap", e - p)):
        mg = int(np.max(gap))
        macro(name, str(mg))
        macro(name + "Text", "no user" if mg == 0 else f"{mg} user" + ("s" if mg > 1 else ""))
    macro("AssocWins", str(int(np.sum(p > g))))
    lp = np.floor(np.array([r["lp"] for r in rows]) + 1e-6)
    lps = np.floor(np.array([r["lp_slot"] for r in rows]) + 1e-6)
    if np.any(lps < e) or np.any(lp < lps):
        raise RuntimeError("LP bound below the optimum in results/assoc.json")
    macro("AssocLpTightPct", fmt(100 * np.mean(lp == e)))
    macro("AssocLpSlotTightPct", fmt(100 * np.mean(lps == e)))
    macro("AssocLpSlotMaxGap", str(int(np.max(lps - e))))
    macro("AssocLpMaxGap", str(int(np.max(lp - e))))
    for k, n, dd in (("t_greedy", "AssocTGreedy", 2), ("t_pace", "AssocTPace", 2), ("t_exact", "AssocTExact", 1)):
        t = 1e3 * np.array([r[k] for r in rows])
        macro(n, fmt(np.median(t), dd))
        macro(n + "Pnn", fmt(np.percentile(t, 99), dd))
    macro("AssocAllOptimalStatus", "yes" if all("Optimal" in r["status"] or r["status"] == "empty"
                                                  for r in rows) else "no")
    # per-demand table
    R = sorted({r["r_min"] for r in rows})
    lines = [r"\begin{tabular}{@{}lrrrrr@{}}", r"\toprule",
             r"$R_{\min}$ (Gb/s) & " + " & ".join(f"{r / 1e9:g}" for r in R) + r" \\", r"\midrule"]
    sel = [np.array([r["r_min"] == x for r in rows]) for x in R]
    cells = {
        "Greedy optimal (\\%)": [fmt(100 * np.mean(g[m] == e[m])) for m in sel],
        "PACE optimal (\\%)": [fmt(100 * np.mean(p[m] == e[m])) for m in sel],
        "PACE certified (\\%)": [fmt(100 * np.mean(cert[m])) for m in sel],
        "Users short, greedy": [str(int(np.sum(e[m] - g[m]))) for m in sel],
        "Users short, PACE": [str(int(np.sum(e[m] - p[m]))) for m in sel],
    }
    for name, vals in cells.items():
        lines.append(name + " & " + " & ".join(vals) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TAB / "assoc.tex").write_text("\n".join(lines) + "\n")
    macro("AssocPerDemand", str(int(sel[0].sum())))


# ----------------------------------------------------------------------- E6 sensing
def sensing():
    d = load("sensing")
    if d is None:
        return
    rows = d["rows"]
    sig = d["meta"]["sigma"]
    S = [mean_ci([100 * r["satisfaction"] for r in by(rows, sigma=s)]) for s in sig]
    fig, ax = plt.subplots(figsize=(COL_W, 1.6))
    ax.errorbar(sig, [s[0] for s in S], yerr=[s[1] for s in S], color=BLUE, marker="o", ms=3,
                capsize=1.5, elinewidth=0.6)
    ax.set_xlabel("Position error std. $\\sigma$ (m)")
    ax.set_ylabel("Satisfied users $S$ (%)")
    save(fig, "sensing")
    for s, (m, h) in zip(sig, S):
        macro("Sens" + {0.0: "Zero", 0.25: "Quarter", 0.5: "Half", 1.0: "One"}[s], fmt(m))


# ----------------------------------------------------------------------- params
def params_numbers():
    t = P.thz
    macro("NoiseThz", fmt(t.noise_dbm))
    macro("AbsCoeff", f"{t.absorption_coeff * 1e3:.2f}")
    macro("AbsDbKm", fmt(t.absorption_db_per_km, 2))
    macro("UePsi", fmt(ue_main_lobe_halfangle_deg(t.ue_gain_dbi, t.ue_side_lobe_dbi)))
    gains = {int(a): ap_main_gain_dbi(a, t.ap_side_lobe_dbi) for a in CANDIDATE_ALPHA}
    macro("GainThirty", fmt(gains[30]))
    macro("GainSixty", fmt(gains[60]))
    macro("GainOneTwenty", fmt(gains[120]))
    wn = -174 + 10 * math.log10(160e6) + 7
    macro("WifiMaxRate", fmt(P.wifi.mac_efficiency * P.wifi.phy_rate_mbps[-1] / 1e3, 2))
    macro("BudgetUnit", str(P.opt.swarm * P.opt.iters))
    macro("FlatBudget", str(4 * P.opt.swarm * P.opt.iters))
    eirp = t.p_max_dbm + gains[30]
    s_half = 10 ** ((eirp - 30) / 10) / (4 * math.pi * 0.5 ** 2)
    macro("MaxEirp", fmt(eirp))
    macro("ExposureHalfMeter", fmt(s_half, 2))
    _ = wn


def write_numbers():
    lines = ["% Auto-generated by plots/make_paper_assets.py -- do not edit."]
    for k, v in sorted(NUM.items()):
        lines.append(f"\\newcommand{{\\{k}}}{{{v}}}")
    (ROOT / "paper" / "numbers.tex").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    params_numbers()
    legacy_numbers()
    fig_layout()
    main_results()
    convergence()
    assoc()
    sensing()
    regime()
    temporal()
    write_numbers()
    print(f"{len(NUM)} macros written")
