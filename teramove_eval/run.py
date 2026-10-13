"""Re-run every simulation result of the TeraMove paper with the corrected simulator.

Corrections relative to the original runs (see teramove_paper/CHANGES.md):
  * azimuths are compass bearings, as produced by the MILP (chsr_sim.config.AZIMUTH_COMPASS);
  * molecular absorption from ITU-R P.676 (chsr_sim.config.K_F);
  * PSO and GA baselines are real implementations with the same fitness (chsr_sim.baselines);
  * every statistic is a mean over 30 seeds.

Usage:  PYTHONPATH=. python -m teramove_eval.run [--exp all|commission|tiers|temporal|density|sensitivity]
"""
import argparse
import json
import os
import time
from multiprocessing import get_context
from pathlib import Path

import numpy as np

import chsr_sim.environment as env
import chsr_sim.optimizer as opt
from chsr_sim.baselines import ga_optimize, nearest_neighbour_assign, standard_pso_optimize
from chsr_sim.config import CANDIDATE_ALPHA, CANDIDATE_PHI, CANDIDATE_Z, TARGET_COVERAGE
from chsr_sim.environment import gen_walls, generate_human_density
from chsr_sim.optimizer import apso_optimize, compute_total_movement, hungarian_reassign
from chsr_sim.physics import calculate_sinr

ROOT = Path(__file__).resolve().parents[1]
RES = Path(os.environ.get("TM_RESULTS", ROOT / "teramove_eval" / "results"))
RES.mkdir(parents=True, exist_ok=True)
N_SEEDS = int(os.environ.get("TM_SEEDS", 30))
WORKERS = max(1, min(22, (os.cpu_count() or 2) - 2))
WALLS = gen_walls()
DENSITY_LEVELS = {"Low": 3, "Medium": 6, "High": 9, "Ultra-dense": 12}   # number of crowd clusters
DEFAULT_CLUSTERS = 9                                                     # chsr_sim.config.COUNT_CIRCLE
CONFIGS = {  # Table IV: (w_c, w_d, beta, gamma)
    "A": (0.4, 0.6, 0.15, 0.3), "B": (0.3, 0.7, 0.15, 0.3),
    "C": (0.4, 0.6, 0.15, 0.1), "D": (0.4, 0.6, 0.25, 0.3),
}
BUDGET_TIERS = 3   # worst-case cascade budget = 3 tiers x S x T evaluations

# MILP.pdf Fig. 1 layout (x, y, z, compass azimuth); TeraMove used 60 deg beams.
MILP = [(0.5, 19.5, 2.4, 135), (0.5, 15.5, 2.2, 135), (17.5, 18.5, 2.6, 270),
        (28.5, 16.5, 2.2, 45), (28.5, 12.5, 2.8, 45), (0.5, 10.5, 3.0, 45),
        (0.5, 9.5, 2.8, 135), (14.5, 12.5, 3.0, 45), (16.5, 11.5, 2.4, 135),
        (29.5, 9.5, 2.6, 135), (0.5, 4.5, 2.8, 135), (3.5, 0.5, 2.2, 45),
        (16.5, 0.5, 2.4, 45), (29.5, 4.5, 3.0, 135)]


def milp_routers():
    return [{"x": x, "y": y, "z": z, "phi": float(b), "alpha": 60.0, "power": 1.0} for x, y, z, b in MILP]


def set_weights(cfg="D"):
    wc, wd, beta, gamma = CONFIGS[cfg]
    opt.CELL_WEIGHT, opt.DENSITY_WEIGHT, opt.MOVEMENT_BETA, opt.CLUSTER_GAMMA = wc, wd, beta, gamma


def density(seed, clusters=DEFAULT_CLUSTERS):
    env.COUNT_CIRCLE = clusters
    d = generate_human_density(seed)
    env.COUNT_CIRCLE = DEFAULT_CLUSTERS
    return d


def coverage(routers, dens):
    return float(calculate_sinr(routers, dens, WALLS)[1])


def save(name, obj):
    (RES / f"{name}.json").write_text(json.dumps(obj, indent=0, default=float))


def load(name):
    return json.loads((RES / f"{name}.json").read_text())


def pmap(fn, tasks):
    with get_context("fork").Pool(WORKERS) as pool:
        return pool.map(fn, tasks, chunksize=1)


# --------------------------------------------------------------------------- commissioning
def exp_commission():
    """The MILP solved its own channel model; under the simulator's model its beams and
    heights are re-tuned once for the empty floor (positions unchanged) by exhaustive
    per-AP coordinate descent over (height, azimuth, beamwidth)."""
    empty = np.zeros((32, 20))
    cur = milp_routers()
    f0 = coverage(cur, empty)
    best, improved = f0, True
    while improved:
        improved = False
        for i in range(len(cur)):
            for z in CANDIDATE_Z:
                for phi in CANDIDATE_PHI:
                    for a in CANDIDATE_ALPHA:
                        cand = [dict(r) for r in cur]
                        cand[i].update(z=float(z), phi=float(phi), alpha=float(a))
                        c = coverage(cand, empty)
                        if c > best + 1e-12:
                            cur, best, improved = cand, c, True
    save("commission", {"milp_empty_coverage": f0, "commissioned_empty_coverage": best, "routers": cur})


def commissioned():
    return load("commission")["routers"]


# --------------------------------------------------------------------------- cascade
def cascade(routers, dens, prev=None, force_all=False, histories=None):
    """TeraMove 4-tier cascade (as published). Returns final routers and a per-tier log."""
    prev = [dict(r) for r in routers] if prev is None else prev
    log = [{"tier": 1, "coverage": coverage(routers, dens), "disp": 0.0}]
    if log[0]["coverage"] >= TARGET_COVERAGE and not force_all:
        return routers, log
    cur = routers
    for tier in (2, 3, 4):
        h = [] if histories is not None else None
        cur = apso_optimize(cur, dens, WALLS, tier=tier, prev_routers=prev, history=h, verbose=False)
        if histories is not None:
            histories.extend(h)
        placed = hungarian_reassign(prev, cur)
        entry = {"tier": tier, "coverage": coverage(placed, dens),
                 "disp": compute_total_movement(prev, placed)}
        if tier == 4:
            nn = nearest_neighbour_assign(prev, cur)
            entry["disp_nn"] = compute_total_movement(prev, nn)
        log.append(entry)
        if entry["coverage"] >= TARGET_COVERAGE and not force_all:
            return placed, log
    return placed, log


def flat_method(method, routers, dens, histories=None, force=False):
    prev = [dict(r) for r in routers]
    c0 = coverage(routers, dens)
    if c0 >= TARGET_COVERAGE and not force:
        return routers, c0, 0.0
    iters = BUDGET_TIERS * opt.APSO_ITERS
    if method == "pso":
        new = standard_pso_optimize(routers, dens, WALLS, prev, iters, history=histories)
    else:
        new = ga_optimize(routers, dens, WALLS, prev, iters, history=histories)
    placed = hungarian_reassign(prev, new)
    return placed, coverage(placed, dens), compute_total_movement(prev, placed)


# --------------------------------------------------------------------------- experiments
def _tiers_task(seed):
    set_weights("D")
    np.random.seed(seed)
    dens = density(seed)
    hist = []
    _, log = cascade(commissioned(), dens, force_all=True, histories=hist)
    return {"seed": seed, "log": log, "history": hist}


def exp_tiers():
    save("tiers", pmap(_tiers_task, list(range(N_SEEDS))))


def _sequence(method, seed, cfg="D", keep_routers=False):
    """Time steps t0, t1, t2 use the crowd maps generate_human_density(0, 1, 2)."""
    set_weights(cfg)
    np.random.seed(seed)
    routers = commissioned()
    steps = []
    for t in range(3):
        dens = density(t)
        before = [dict(r) for r in routers]
        c0 = coverage(routers, dens)
        if method == "hpso":
            routers, log = cascade(routers, dens)
            tier = log[-1]["tier"]
        else:
            routers, _, _ = flat_method(method, routers, dens)
            tier = None
        step = {"t": t, "cov_before": c0, "cov_after": coverage(routers, dens),
                "disp": compute_total_movement(before, routers), "tier": tier}
        if keep_routers:
            step["routers_before"], step["routers_after"] = before, routers
        steps.append(step)
    return steps


def _temporal_task(args):
    method, seed = args
    return {"method": method, "seed": seed, "steps": _sequence(method, seed, keep_routers=(seed == 0))}


def exp_temporal():
    tasks = [(m, s) for m in ("hpso", "pso", "ga") for s in range(N_SEEDS)]
    save("temporal", pmap(_temporal_task, tasks))


def _density_task(args):
    level, method, seed = args
    set_weights("D")
    np.random.seed(seed)
    dens = density(seed, DENSITY_LEVELS[level])
    routers = commissioned()
    hist = []
    if method == "hpso":
        placed, log = cascade(routers, dens, histories=hist)
        cov, disp = log[-1]["coverage"], log[-1]["disp"]
    else:
        placed, cov, disp = flat_method(method, routers, dens, histories=hist)
    return {"level": level, "method": method, "seed": seed, "cov_before": coverage(routers, dens),
            "coverage": cov, "disp": disp, "history": hist}


def exp_density():
    tasks = [(lv, m, s) for lv in DENSITY_LEVELS for m in ("hpso", "pso", "ga") for s in range(N_SEEDS)]
    save("density", pmap(_density_task, tasks))


def _sens_task(args):
    cfg, seed = args
    steps = _sequence("hpso", seed, cfg)
    return {"cfg": cfg, "seed": seed, "avg_cov": float(np.mean([s["cov_after"] for s in steps])),
            "total_disp": float(np.sum([s["disp"] for s in steps]))}


def exp_sensitivity():
    save("sensitivity", pmap(_sens_task, [(c, s) for c in CONFIGS for s in range(N_SEEDS)]))


def _conv_task(args):
    method, seed = args
    set_weights("D")
    np.random.seed(seed)
    hist = []
    flat_method(method, commissioned(), density(seed), histories=hist, force=True)
    return {"method": method, "seed": seed, "history": hist}


def exp_convergence():
    """Standard PSO and GA run on the same 30 crowds as the forced HPSO tiers (exp_tiers)."""
    save("convergence", pmap(_conv_task, [(m, s) for m in ("pso", "ga") for s in range(N_SEEDS)]))


EXPS = {"commission": exp_commission, "tiers": exp_tiers, "temporal": exp_temporal,
        "density": exp_density, "sensitivity": exp_sensitivity, "convergence": exp_convergence}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", nargs="+", default=["all"], choices=list(EXPS) + ["all"])
    names = list(EXPS) if "all" in ap.parse_args().exp else ap.parse_args().exp
    coverage(milp_routers(), np.zeros((32, 20)))     # JIT-compile before forking workers
    for n in names:
        t = time.time()
        EXPS[n]()
        print(f"[{n}] {time.time() - t:.0f} s", flush=True)


if __name__ == "__main__":
    main()
