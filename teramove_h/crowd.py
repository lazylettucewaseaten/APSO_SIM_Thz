"""Crowd model: people are both the users and the blockers.

People are drawn from a clustered point process: a fraction lives in Gaussian
clusters around uniformly placed centres (Thomas-type clusters), the rest is
uniform background.  Positions are hard-core (no two bodies overlap) and keep a
clearance from walls and cubicles.  Each person is an active user with
probability ``active_prob``; users face a uniformly random direction.
"""
from dataclasses import dataclass

import numpy as np

from .config import CrowdParams
from .geometry import WALLS, segment_distance


@dataclass
class Crowd:
    xy: np.ndarray          # (P, 2) body centres
    active: np.ndarray      # (P,) bool, person holds an active device
    facing: np.ndarray      # (P,) device orientation, math angle deg (uniform)
    cluster: np.ndarray     # (P,) cluster index, -1 for background
    offset: np.ndarray      # (P, 2) offset from cluster centre (identity across epochs)
    centres: np.ndarray     # (C, 2) cluster centres

    @property
    def n_people(self):
        return len(self.xy)

    @property
    def user_idx(self):
        return np.flatnonzero(self.active)


def _valid(p, placed, cp: CrowdParams, length, breadth):
    x, y = p
    m = cp.body_radius_m
    if not (m <= x <= length - m and m <= y <= breadth - m):
        return False
    for w in WALLS:
        if segment_distance(x, y, w) < cp.wall_clearance_m:
            return False
    if placed:
        d = np.hypot(*(np.asarray(placed) - p).T)
        if np.any(d < cp.min_separation_m):
            return False
    return True


def _place(rng, proposal, placed, cp, length, breadth, tries=200):
    for _ in range(tries):
        p = proposal()
        if _valid(p, placed, cp, length, breadth):
            return p
    # Crowded cluster: fall back to a uniform valid position.
    while True:
        p = rng.uniform([0, 0], [length, breadth])
        if _valid(p, placed, cp, length, breadth):
            return p


def generate_crowd(rng: np.random.Generator, cp: CrowdParams, length=32.0, breadth=20.0) -> Crowd:
    n = cp.n_people
    centres = rng.uniform([1.0, 1.0], [length - 1.0, breadth - 1.0], size=(cp.n_clusters, 2))
    n_bg = int(round(cp.background_fraction * n))
    cluster = np.full(n, -1)
    cluster[: n - n_bg] = rng.integers(0, cp.n_clusters, size=n - n_bg)
    placed, offsets = [], []
    for i in range(n):
        if cluster[i] >= 0:
            c = centres[cluster[i]]
            p = _place(rng, lambda: c + rng.normal(0, cp.cluster_sigma_m, 2),
                       placed, cp, length, breadth)
            offsets.append(p - c)
        else:
            p = _place(rng, lambda: rng.uniform([0, 0], [length, breadth]),
                       placed, cp, length, breadth)
            offsets.append(np.zeros(2))
        placed.append(p)
    active = rng.random(n) < cp.active_prob
    facing = rng.uniform(0, 360, n)
    return Crowd(np.array(placed), active, facing, cluster, np.array(offsets), centres)


def drift_crowd(crowd: Crowd, rng: np.random.Generator, cp: CrowdParams,
                length=32.0, breadth=20.0) -> Crowd:
    """Next epoch: clusters drift, people keep identity, offset and activity."""
    ang = rng.uniform(0, 2 * np.pi, len(crowd.centres))
    centres = crowd.centres + cp.drift_m * np.column_stack([np.cos(ang), np.sin(ang)])
    # Reflect at the boundary [1, L-1] x [1, B-1].
    lo, hi = np.array([1.0, 1.0]), np.array([length - 1.0, breadth - 1.0])
    centres = np.where(centres < lo, 2 * lo - centres, centres)
    centres = np.where(centres > hi, 2 * hi - centres, centres)
    placed, offsets = [], []
    for i in range(crowd.n_people):
        if crowd.cluster[i] >= 0:
            base = centres[crowd.cluster[i]] + crowd.offset[i]
        else:
            base = crowd.xy[i]
        p = _place(rng, lambda: base + rng.normal(0, cp.jitter_m, 2), placed, cp, length, breadth)
        placed.append(p)
        offsets.append(p - centres[crowd.cluster[i]] if crowd.cluster[i] >= 0 else np.zeros(2))
    facing = (crowd.facing + rng.normal(0, cp.facing_jitter_deg, crowd.n_people)) % 360
    return Crowd(np.array(placed), crowd.active.copy(), facing, crowd.cluster.copy(),
                 np.array(offsets), centres)


def density_map(crowd: Crowd, cp: CrowdParams, length=32, breadth=20) -> np.ndarray:
    """Eq. (12): D(c) = min(1, n(c) / n_max) on the 1 m grid, shape (length, breadth)."""
    counts = np.zeros((length, breadth))
    ix = np.clip(crowd.xy[:, 0].astype(int), 0, length - 1)
    iy = np.clip(crowd.xy[:, 1].astype(int), 0, breadth - 1)
    np.add.at(counts, (ix, iy), 1.0)
    return np.minimum(1.0, counts / cp.n_max_per_cell)


def perturb_crowd(crowd: Crowd, rng: np.random.Generator, sigma_m: float,
                  length=32.0, breadth=20.0) -> Crowd:
    """Sensing error: Gaussian position noise (used as the optimiser's context only)."""
    xy = crowd.xy + rng.normal(0, sigma_m, crowd.xy.shape)
    xy[:, 0] = np.clip(xy[:, 0], 0.01, length - 0.01)
    xy[:, 1] = np.clip(xy[:, 1], 0.01, breadth - 0.01)
    return Crowd(xy, crowd.active.copy(), crowd.facing.copy(), crowd.cluster.copy(),
                 crowd.offset.copy(), crowd.centres.copy())
