"""Run every experiment of the paper and store raw results in results/*.json.

Usage:  python -m experiments.run_experiments --exp all
        python -m experiments.run_experiments --exp main regime
"""
import argparse
import json
import time

import numpy as np

from teramove_h.association import gap_exact, gap_greedy
from teramove_h.cascade import run_method
from teramove_h.config import DEFAULT
from teramove_h.crowd import drift_crowd, generate_crowd, perturb_crowd
from teramove_h.network import Scenario, THzTerms, grid_coverage, milp_config, thz_capacity
from teramove_h.optimizer import decode, encode

from .common import N_SEEDS, RESULTS, commission, empty_crowd, pmap, rng_for, strip

MAIN_METHODS = ["static", "wifi_only", "teramove", "thz_only", "naive", "flat_pso", "ga",
                "proposed", "proposed_nopc", "proposed_nomove", "proposed_hpso"]
REGIME_RMIN = [0.1e9, 0.25e9, 0.5e9, 1e9, 2e9]
REGIME_NP = [60, 120, 180, 240]
REGIME_METHODS = ["proposed", "ga", "thz_only", "naive"]
TEMPORAL_METHODS = ["static", "teramove", "ga", "proposed"]
N_EPOCHS = 6
SENSING_SIGMA = [0.0, 0.25, 0.5, 1.0]


def _params(r_min=1e9, n_people=120):
    return DEFAULT.with_(opt={"r_min_bps": r_min}, crowd={"n_people": n_people})


def _save(name, rows, meta):
    (RESULTS / f"{name}.json").write_text(json.dumps({"meta": meta, "rows": rows}, indent=0,
                                                     default=float))


# ---------------------------------------------------------------- E1 legacy check
def exp_legacy():
    """Fig. 1 layout under (i) the legacy simulator with both azimuth conventions,
    (ii) the corrected model before and after commissioning."""
    import chsr_sim.physics as lp
    from chsr_sim.environment import gen_walls
    from teramove_h.geometry import MILP_LAYOUT
    walls = gen_walls()
    empty = np.zeros((32, 20))
    rows = []
    # The original simulator: absorption 0.05 1/m; azimuth read as a math angle
    # ("legacy_math") or, correctly, as a compass bearing ("compass").
    k_f, compass = lp.K_F, lp.AZIMUTH_COMPASS
    lp.K_F = lp.K_F_LEGACY
    for conv in ("legacy_math", "compass"):
        lp.AZIMUTH_COMPASS = conv == "compass"
        routers = [{"x": x, "y": y, "z": z, "alpha": 60.0, "power": 1.0, "phi": b}
                   for x, y, z, b in MILP_LAYOUT]
        lp._ROUTER_STATIC_CACHE.clear()
        sinr, _ = lp.calculate_sinr(routers, empty, walls)
        rows.append({"model": "legacy", "convention": conv, "coverage": float(np.mean(sinr >= 5))})
    lp.K_F, lp.AZIMUTH_COMPASS = k_f, compass
    lp._ROUTER_STATIC_CACHE.clear()
    cfg, info = commission()
    view = Scenario(DEFAULT, empty_crowd(), wifi=False).true_view
    for name, c in (("milp", milp_config(DEFAULT)), ("commissioned", cfg)):
        _, cov, _ = grid_coverage(DEFAULT, c, view)
        rows.append({"model": "corrected", "convention": "compass", "layout": name, "coverage": cov})
    _save("legacy", rows, {"commission": {k: v for k, v in info.items()
                                          if k not in ("x", "y", "p", "room")}})


# ---------------------------------------------------------------- E2 main comparison
def _main_task(args):
    seed, method = args
    p = _params()
    cfg0, _ = commission()
    sc = Scenario(p, generate_crowd(rng_for(seed, "crowd"), p.crowd))
    r = strip(run_method(p, sc, cfg0, method, rng_for(seed, "opt")))
    r["seed"] = seed
    return r


def exp_main():
    tasks = [(s, m) for s in range(N_SEEDS) for m in MAIN_METHODS]
    _save("main", pmap(_main_task, tasks), {"r_min": 1e9, "n_people": 120, "seeds": N_SEEDS})


# ---------------------------------------------------------------- E3 regime map
def _regime_task(args):
    seed, method, r_min, n_people = args
    p = _params(r_min, n_people)
    cfg0, _ = commission()
    sc = Scenario(p, generate_crowd(rng_for(seed, f"crowd-{n_people}"), p.crowd))
    r = strip(run_method(p, sc, cfg0, method, rng_for(seed, "opt")))
    r.pop("curves")
    r.update(seed=seed, r_min=r_min, n_people=n_people)
    return r


def exp_regime():
    tasks = [(s, m, r, n) for r in REGIME_RMIN for n in REGIME_NP for m in REGIME_METHODS
             for s in range(N_SEEDS)]
    _save("regime", pmap(_regime_task, tasks),
          {"r_min": REGIME_RMIN, "n_people": REGIME_NP, "seeds": N_SEEDS})


# ---------------------------------------------------------------- E4 temporal
def _handovers(prev_assign, assign, n_thz):
    both = (prev_assign >= 0) & (assign >= 0)
    changed = both & (prev_assign != assign)
    thz_prev, thz_now = prev_assign < n_thz, assign < n_thz
    return {"ho_total": int(changed.sum()),
            "ho_thz_thz": int(np.sum(changed & thz_prev & thz_now)),
            "ho_vertical": int(np.sum(changed & (thz_prev != thz_now))),
            "served_both": int(both.sum())}


def _temporal_task(args):
    seed, method = args
    p = _params()
    cfg, _ = commission()
    rng_c = rng_for(seed, "temporal-crowd")
    crowd = generate_crowd(rng_c, p.crowd)
    rng = rng_for(seed, "temporal-opt")
    rows, prev = [], None
    for epoch in range(N_EPOCHS):
        sc = Scenario(p, crowd)
        r = run_method(p, sc, cfg, method, rng)
        row = strip(r)
        row.pop("curves")
        row.update(seed=seed, epoch=epoch)
        if prev is not None:
            row.update(_handovers(prev, r["assign"], cfg.n))
        rows.append(row)
        prev, cfg = r["assign"], r["cfg"]
        crowd = drift_crowd(crowd, rng_c, p.crowd)
    return rows


def exp_temporal():
    out = pmap(_temporal_task, [(s, m) for s in range(N_SEEDS) for m in TEMPORAL_METHODS])
    _save("temporal", [r for rows in out for r in rows], {"epochs": N_EPOCHS, "seeds": N_SEEDS})


# ---------------------------------------------------------------- E5 association gap
def _assoc_task(seed):
    rows = []
    cfg0, _ = commission()
    for r_min in REGIME_RMIN:
        p = _params(r_min, 120)
        sc = Scenario(p, generate_crowd(rng_for(seed, "crowd"), p.crowd))
        rng = rng_for(seed, f"assoc-{r_min}")
        for trial in range(3):   # commissioned layout + two random re-configurations
            noise = (rng.normal(0, 1, (cfg0.n, 5)) * [2.0, 2.0, 0.4, 90.0, 30.0]).ravel()
            cfg = cfg0 if trial == 0 else decode(encode(cfg0) + noise, cfg0, 0.25)
            terms = THzTerms(p, cfg, sc.true_view.users)
            cap = np.hstack([thz_capacity(p, terms.sinr(cfg.p)), sc.true_view.wifi_rate])
            t = time.perf_counter()
            a_g, _ = gap_greedy(cap, r_min)
            t_g = time.perf_counter() - t
            t = time.perf_counter()
            a_e, _, status = gap_exact(cap, r_min)
            t_e = time.perf_counter() - t
            rows.append({"seed": seed, "r_min": r_min, "trial": trial, "k": cap.shape[0],
                         "greedy": int(np.sum(a_g >= 0)), "exact": int(np.sum(a_e >= 0)),
                         "t_greedy": t_g, "t_exact": t_e, "status": str(status)})
    return rows


def exp_assoc():
    gap_greedy(np.ones((2, 2)) * 2e9, 1e9)   # compile before timing
    out = pmap(_assoc_task, list(range(N_SEEDS)))
    _save("assoc", [r for rows in out for r in rows], {"seeds": N_SEEDS})


# ---------------------------------------------------------------- E6 sensing error
def _sensing_task(args):
    seed, sigma = args
    p = _params()
    cfg0, _ = commission()
    truth = generate_crowd(rng_for(seed, "crowd"), p.crowd)
    ctx = perturb_crowd(truth, rng_for(seed, f"noise-{sigma}"), sigma) if sigma > 0 else None
    sc = Scenario(p, truth, ctx)
    r = strip(run_method(p, sc, cfg0, "proposed", rng_for(seed, "opt")))
    r.pop("curves")
    r.update(seed=seed, sigma=sigma)
    return r


def exp_sensing():
    tasks = [(s, sg) for sg in SENSING_SIGMA for s in range(N_SEEDS)]
    _save("sensing", pmap(_sensing_task, tasks), {"sigma": SENSING_SIGMA, "seeds": N_SEEDS})


EXPERIMENTS = {"legacy": exp_legacy, "main": exp_main, "regime": exp_regime,
               "temporal": exp_temporal, "assoc": exp_assoc, "sensing": exp_sensing}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", nargs="+", default=["all"], choices=list(EXPERIMENTS) + ["all"])
    names = list(EXPERIMENTS) if "all" in ap.parse_args().exp else ap.parse_args().exp
    commission()                       # deterministic, cached in results/
    for name in names:
        t = time.time()
        EXPERIMENTS[name]()
        print(f"[{name}] done in {time.time() - t:.0f} s", flush=True)


if __name__ == "__main__":
    main()
