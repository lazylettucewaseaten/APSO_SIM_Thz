"""Shared experiment utilities: commissioning, seeding, parallel execution, statistics."""
import json
import os
import zlib
from multiprocessing import get_context
from pathlib import Path

import numpy as np
from scipy import stats

from teramove_h.config import CANDIDATE_ALPHA, CANDIDATE_PHI, CANDIDATE_Z, DEFAULT, Params
from teramove_h.crowd import Crowd
from teramove_h.network import APConfig, Scenario, grid_coverage, milp_config
from teramove_h.optimizer import cluster_penalty, pso

ROOT = Path(__file__).resolve().parents[1]
RESULTS = Path(os.environ.get("TMH_RESULTS", ROOT / "results"))
RESULTS.mkdir(exist_ok=True, parents=True)
N_SEEDS = int(os.environ.get("TMH_SEEDS", 30))
WORKERS = max(1, min(22, (os.cpu_count() or 2) - 2))
COMMISSION_FILE = RESULTS / "commissioned_layout.json"


def rng_for(seed, tag):
    """Independent, reproducible stream per (seed, tag)."""
    return np.random.default_rng([seed, zlib.crc32(tag.encode())])


def empty_crowd():
    z = np.zeros
    return Crowd(z((0, 2)), z(0, bool), z(0), z(0, int), z((0, 2)), z((0, 2)))


def commission(params: Params = DEFAULT, swarm=60, iters=60):
    """Empty-room commissioning of the MILP layout (positions fixed).

    The MILP of the earlier work used a different antenna/channel model, so its
    azimuths and heights are re-tuned once for the empty building under the
    present model (tiers 2 and 3, maximising grid coverage).  Positions are the
    MILP positions.  The result is the starting deployment of every experiment.
    """
    if COMMISSION_FILE.exists():
        d = json.loads(COMMISSION_FILE.read_text())
        return APConfig(*(np.array(d[k]) for k in ("x", "y", "z", "phi", "alpha", "p", "room"))), d
    view = Scenario(params, empty_crowd(), wifi=False).true_view
    cfg = milp_config(params)
    _, cov0, _ = grid_coverage(params, cfg, view)
    opt = params.with_(opt={"swarm": swarm, "iters": iters}).opt

    def fit(c):
        _, cell, _ = grid_coverage(params, c, view)
        return cell - opt.gamma_cluster * cluster_penalty(c, opt.d_min_m)

    rng = np.random.default_rng(20261003)
    cur = cfg
    for tier in (2, 3):
        cur, _, _, _ = pso(cur, fit, tier, opt, rng)
    cur = polish(cur, fit)
    cur.p[:] = cfg.p
    _, cov1, _ = grid_coverage(params, cur, view)
    d = {k: getattr(cur, k).tolist() for k in ("x", "y", "z", "phi", "alpha", "p", "room")}
    d.update(milp_empty_coverage=cov0, commissioned_empty_coverage=cov1, swarm=swarm, iters=iters)
    COMMISSION_FILE.write_text(json.dumps(d, indent=1))
    return cur, d


def polish(cfg, fit):
    """Coordinate descent: for each AP try every (azimuth, width, height) candidate,
    keep strict improvements, repeat until a full sweep changes nothing."""
    cur, f_cur = cfg.copy(), fit(cfg)
    improved = True
    while improved:
        improved = False
        for i in range(cur.n):
            for z in CANDIDATE_Z:
                for phi in CANDIDATE_PHI:
                    for alpha in CANDIDATE_ALPHA:
                        cand = cur.copy()
                        cand.z[i], cand.phi[i], cand.alpha[i] = z, phi, alpha
                        f = fit(cand)
                        if f > f_cur + 1e-12:
                            cur, f_cur, improved = cand, f, True
    return cur


def pmap(fn, tasks, workers=WORKERS):
    if workers <= 1:
        return [fn(t) for t in tasks]
    with get_context("fork").Pool(workers) as pool:
        return pool.map(fn, tasks, chunksize=1)


def mean_ci(x, conf=0.95):
    """Mean and half-width of the Student-t confidence interval."""
    x = np.asarray(x, dtype=float)
    if len(x) < 2:
        return float(np.mean(x)), 0.0
    h = stats.t.ppf((1 + conf) / 2, len(x) - 1) * stats.sem(x)
    return float(np.mean(x)), float(h)


def wilcoxon_p(a, b):
    """Two-sided Wilcoxon signed-rank p-value for paired samples (1.0 if identical)."""
    a, b = np.asarray(a), np.asarray(b)
    if np.allclose(a, b):
        return 1.0
    return float(stats.wilcoxon(a, b).pvalue)


def strip(result):
    """Drop non-serialisable fields of a run_method result."""
    r = dict(result)
    r.pop("cfg", None)
    r.pop("assign", None)
    r["stages"] = [(int(t), float(s)) for t, s in r["stages"]]
    r["curves"] = {str(k): [float(v) for v in c] for k, c in r["curves"].items()}
    return r
