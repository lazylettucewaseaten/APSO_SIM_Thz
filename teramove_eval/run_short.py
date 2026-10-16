"""Simulation results of the short TeraMove paper (TeraHertz-short/paper.tex).

Model: chsr_sim with the corrections of config.py (compass azimuths, ITU-R absorption,
beamwidth-coupled gain, saturating blockage, users at cell centres, ray height from the
user end).  Results go to teramove_eval/results_short/ (or $TM_RESULTS).

Arms compared on the same crowds:
  fixed     static layout, design-time association (each cell keeps its empty-floor AP)
  handover  static layout, every cell re-associates to its strongest AP
  ho_t2     handover + Tier 2 only (beam steering, no movement)
  teramove  full 4-tier cascade (Tier 4 swarm seeded with the greedy layout)
  greedy    crowd-aware greedy re-placement alone (chsr_sim.greedy_seed), no swarm
  pso, ga   flat baselines with the same fitness and the same worst-case budget

Crowds: every (seed, step) gets its own draw of the circular-cluster crowd model.

Usage:  PYTHONPATH=. python -m teramove_eval.run_short [--exp all|commission|tiers|temporal|density]
"""
import argparse
import json
import os
import time
from pathlib import Path

import numpy as np

import chsr_sim.optimizer as opt
from chsr_sim.baselines import nearest_neighbour_assign
from chsr_sim.greedy_seed import greedy_seed
from chsr_sim.config import CANDIDATE_ALPHA, CANDIDATE_PHI, CANDIDATE_Z, RAIL_SPEED, TARGET_COVERAGE
from chsr_sim.optimizer import apso_optimize, compute_total_movement, hungarian_reassign
from chsr_sim.physics import calculate_sinr
from teramove_eval.run import DENSITY_LEVELS, WALLS, density, flat_method, milp_routers, pmap, set_weights

ROOT = Path(__file__).resolve().parents[1]
RES = Path(os.environ.get("TM_RESULTS", ROOT / "teramove_eval" / "results_short"))
RES.mkdir(parents=True, exist_ok=True)
N_SEEDS = int(os.environ.get("TM_SEEDS", 30))
ARMS = ("fixed", "handover", "ho_t2", "teramove", "greedy", "pso", "ga")
EMPTY = np.zeros((32, 20))
# crowd-map seeds, kept apart per experiment
TIER_CROWD = 100
SEQ_CROWD = 200
DEN_CROWD = 300
# beamwidth of the MILP solution (Optimal-AP-Placement-for-THz/ED1: tbw = 120 deg)
MILP_ALPHA = 120.0


def save(name, obj):
    (RES / f"{name}.json").write_text(json.dumps(obj, indent=0, default=float))


def load(name):
    return json.loads((RES / f"{name}.json").read_text())


def coverage(routers, dens, serving=None):
    return float(calculate_sinr(routers, dens, WALLS, serving=serving)[1])


def per_ap_disp(prev, new):
    return [float(np.sqrt((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2 + (a["z"] - b["z"]) ** 2))
            for a, b in zip(prev, new)]


# --------------------------------------------------------------------------- commissioning
def exp_commission():
    """Positions from the MILP layout stay fixed.  Heights and beams are re-tuned once for
    the empty floor under the simulator's model by per-AP coordinate descent.  The best
    server of each cell on the empty floor is the design-time association."""
    cur = [dict(r, alpha=MILP_ALPHA) for r in milp_routers()]
    f0 = coverage(cur, EMPTY)
    best, improved = f0, True
    while improved:
        improved = False
        for i in range(len(cur)):
            for z in CANDIDATE_Z:
                for phi in CANDIDATE_PHI:
                    for a in CANDIDATE_ALPHA:
                        cand = [dict(r) for r in cur]
                        cand[i].update(z=float(z), phi=float(phi), alpha=float(a))
                        c = coverage(cand, EMPTY)
                        if c > best + 1e-12:
                            cur, best, improved = cand, c, True
    _, _, serving = calculate_sinr(cur, EMPTY, WALLS, return_serving=True)
    save("commission", {"milp_empty_coverage": f0, "commissioned_empty_coverage": best,
                        "routers": cur, "serving": serving.tolist()})


def commissioned():
    c = load("commission")
    return [dict(r) for r in c["routers"]], np.array(c["serving"], dtype=np.int64)


# --------------------------------------------------------------------------- cascade
def cascade(routers, dens, max_tier=4, force_all=False):
    """TeraMove cascade.  Tier 1 keeps the layout if coverage meets the target; Tiers 2-4
    unlock beams, height, then (x, y).  Hungarian matching after each tier."""
    prev = [dict(r) for r in routers]
    log = [{"tier": 1, "coverage": coverage(routers, dens), "disp": 0.0, "max_ap_disp": 0.0,
            "wall_s": 0.0}]
    if log[0]["coverage"] >= TARGET_COVERAGE and not force_all:
        return routers, log
    cur, placed = routers, routers
    for tier in range(2, max_tier + 1):
        t0 = time.perf_counter()
        seed = greedy_seed(cur, dens, WALLS) if tier == 4 else None
        cur = apso_optimize(cur, dens, WALLS, tier=tier, prev_routers=prev, verbose=False,
                            seed_routers=seed)
        placed = hungarian_reassign(prev, cur)
        wall = time.perf_counter() - t0
        d = per_ap_disp(prev, placed)
        entry = {"tier": tier, "coverage": coverage(placed, dens), "disp": float(sum(d)),
                 "max_ap_disp": float(max(d)), "wall_s": wall}
        if tier == 4:
            entry["disp_nn"] = compute_total_movement(prev, nearest_neighbour_assign(prev, cur))
        log.append(entry)
        if entry["coverage"] >= TARGET_COVERAGE and not force_all:
            return placed, log
    return placed, log


def step_arm(arm, routers, dens, serving):
    """One adaptation step of one arm.  Returns (new routers, coverage after, log)."""
    if arm == "fixed":
        return routers, coverage(routers, dens, serving), None
    if arm == "handover":
        return routers, coverage(routers, dens), None
    if arm in ("ho_t2", "teramove"):
        new, log = cascade(routers, dens, max_tier=2 if arm == "ho_t2" else 4)
        return new, coverage(new, dens), log
    if arm == "greedy":
        if coverage(routers, dens) >= TARGET_COVERAGE:
            return routers, coverage(routers, dens), None
        new = greedy_seed(routers, dens, WALLS)
        return new, coverage(new, dens), None
    new, cov, _ = flat_method(arm, routers, dens)
    return new, cov, None


# --------------------------------------------------------------------------- experiments
def _tiers_task(seed):
    set_weights("D")
    np.random.seed(seed)
    routers, _ = commissioned()
    _, log = cascade(routers, density(TIER_CROWD + seed), force_all=True)
    return {"seed": seed, "log": log}


def exp_tiers():
    save("tiers", pmap(_tiers_task, list(range(N_SEEDS))))


def _temporal_task(args):
    arm, seed = args
    set_weights("D")
    np.random.seed(seed)
    routers, serving = commissioned()
    steps = []
    for t in range(3):
        dens = density(SEQ_CROWD + 3 * seed + t)
        before = [dict(r) for r in routers]
        c0 = coverage(routers, dens, serving if arm == "fixed" else None)
        routers, c1, log = step_arm(arm, routers, dens, serving)
        d = per_ap_disp(before, routers)
        step = {"t": t, "cov_before": c0, "cov_after": c1, "disp": float(sum(d)),
                "max_ap_disp": float(max(d)), "tier": log[-1]["tier"] if log else None}
        if seed == 0:
            step["routers_before"], step["routers_after"] = before, routers
        steps.append(step)
    return {"arm": arm, "seed": seed, "steps": steps}


def exp_temporal():
    save("temporal", pmap(_temporal_task, [(a, s) for a in ARMS for s in range(N_SEEDS)]))


def _density_task(args):
    level, arm, seed = args
    set_weights("D")
    np.random.seed(seed)
    routers, serving = commissioned()
    dens = density(DEN_CROWD + seed, DENSITY_LEVELS[level])
    c0 = coverage(routers, dens)
    new, c1, log = step_arm(arm, routers, dens, serving)
    return {"level": level, "arm": arm, "seed": seed, "cov_before": c0, "coverage": c1,
            "disp": compute_total_movement(routers, new), "tier": log[-1]["tier"] if log else None}


def exp_density():
    save("density", pmap(_density_task, [(lv, a, s) for lv in DENSITY_LEVELS for a in ARMS
                                         for s in range(N_SEEDS)]))


EXPS = {"commission": exp_commission, "tiers": exp_tiers, "temporal": exp_temporal,
        "density": exp_density}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", nargs="+", default=["all"], choices=list(EXPS) + ["all"])
    a = ap.parse_args()
    names = list(EXPS) if "all" in a.exp else a.exp
    coverage(milp_routers(), EMPTY)     # JIT-compile before forking workers
    meta = {"seeds": N_SEEDS, "rail_speed": RAIL_SPEED, "beta": opt.MOVEMENT_BETA}
    for n in names:
        t = time.time()
        EXPS[n]()
        print(f"[{n}] {time.time() - t:.0f} s", flush=True)
    save("meta", meta)


if __name__ == "__main__":
    main()
