"""Crowd-aware greedy AP layout, used to seed the Tier-4 swarm.

APs are added one at a time.  Each step picks, from a candidate set (every cell centre,
a few heights, all azimuths, a few beamwidths), the AP that adds the most
density-weighted coverage, with full SINR (interference from the APs already placed).
The resulting layout is matched to the current APs with the Hungarian algorithm, so a
particle that starts from it has the smallest possible displacement for that layout.
"""
import numpy as np

from . import physics as lp
from .config import (AZIMUTH_COMPASS, BLOCKAGE_SATURATING, BREADTH, C, CANDIDATE_PHI,
                     CELL_CENTRES, F_HZ, H_HUMAN, HUMAN_PENALTY_DB, K_F, LENGTH, NOISE_DBM, PTX_DBM,
                     RAY_FROM_USER, SINR_TH, Z_U)
from .optimizer import hungarian_reassign

SEED_Z = (2.0, 2.6, 3.0)
SEED_ALPHA = (60.0, 90.0, 120.0)
_CHUNK = 4096


def walls_to_array(walls):
    arr = np.zeros((len(walls), 6))
    for i, w in enumerate(walls):
        arr[i] = (0.0 if w['o'] == 'h' else 1.0,
                  30.0 if w['m'] == 'solid' else (20.0 if w['m'] == 'wood' else 15.0),
                  float(w['p']), float(w['s']), float(w['e']), float(w['h']))
    return arr


def _candidates(human_density, walls):
    """Received power (mW, float32) of every candidate AP at every cell, and its settings."""
    wa = walls_to_array(walls)
    off = 0.5 if CELL_CENTRES else 0.0
    rows, meta = [], []
    g = np.empty((LENGTH, BREADTH))
    for x in range(LENGTH):
        for y in range(BREADTH):
            for z in SEED_Z:
                bp, ang = lp._compute_single_router_static_data(
                    x + off, y + off, z, human_density, wa, LENGTH, BREADTH, float(Z_U), float(F_HZ),
                    float(C), float(K_F), float(H_HUMAN), float(HUMAN_PENALTY_DB), float(PTX_DBM),
                    bool(AZIMUTH_COMPASS), bool(BLOCKAGE_SATURATING), bool(CELL_CENTRES), bool(RAY_FROM_USER))
                for phi in CANDIDATE_PHI:
                    for a in SEED_ALPHA:
                        lp._apply_router_gain_jit(g, bp, ang, float(phi), a, 1.0,
                                                  float(lp.main_lobe_gain(a) + lp.G_RX))
                        rows.append(g.ravel().astype(np.float32))
                        meta.append((x + off, y + off, z, float(phi), a))
    return np.array(rows), meta


def greedy_layout(n_aps, human_density, walls):
    """n_aps AP dicts placed greedily for density-weighted coverage."""
    P, meta = _candidates(human_density, walls)
    w = np.ascontiguousarray(human_density, dtype=np.float32).ravel()
    if w.sum() <= 0:
        w = np.ones_like(w)
    noise = np.float32(10 ** (NOISE_DBM / 10))
    th = np.float32(10 ** (SINR_TH / 10))
    tot = np.zeros(P.shape[1], np.float32)
    best = np.zeros(P.shape[1], np.float32)
    sel = []
    for _ in range(n_aps):
        gains = np.empty(P.shape[0], np.float32)
        for k in range(0, P.shape[0], _CHUNK):
            blk = P[k:k + _CHUNK]
            nb = np.maximum(best, blk)
            ok = nb >= th * (noise + tot + blk - nb)
            gains[k:k + _CHUNK] = ok @ w
        gains[sel] = -1.0
        i = int(np.argmax(gains))
        sel.append(i)
        tot += P[i]
        best = np.maximum(best, P[i])
    return [{'x': m[0], 'y': m[1], 'z': m[2], 'phi': m[3], 'alpha': m[4]} for m in (meta[i] for i in sel)]


def greedy_seed(current_routers, human_density, walls):
    """Greedy layout with the same AP count, matched to the current APs (Hungarian)."""
    layout = greedy_layout(len(current_routers), human_density, walls)
    return hungarian_reassign(current_routers, layout)

