"""Swarm optimisers over THz AP geometry and beams.

* ``hpso_tier``: one tier of the hierarchical PSO (TeraMove). Tier 2 frees the
  azimuth and sector width, tier 3 also the height, tier 4 also (x, y).
  Locked dimensions keep zero velocity (legacy ``apso_optimize``).
* ``flat_pso``: all dimensions free from the first iteration (baseline B5).
* ``genetic``: real-coded GA (baseline B6).

All three include the current configuration as one initial particle, so the
returned configuration is never worse (in fitness) than the starting one.
Positions are confined to the AP's room (ceiling rail) and snapped to the rail
grid (fixes legacy defects D9, D10).
"""
import numpy as np
from scipy.optimize import linear_sum_assignment

from .config import CANDIDATE_ALPHA, CANDIDATE_PHI, CANDIDATE_Z
from .geometry import ROOMS

DIMS = 5  # x, y, z, phi, alpha
WALL_MARGIN = 0.25
VMAX = np.array([3.2, 2.0, 0.4, 45.0, 30.0])  # legacy per-dimension velocity limits


def room_bounds(cfg):
    r = ROOMS[cfg.room]
    return r[:, 0] + WALL_MARGIN, r[:, 1] - WALL_MARGIN, r[:, 2] + WALL_MARGIN, r[:, 3] - WALL_MARGIN


def encode(cfg):
    return np.column_stack([cfg.x, cfg.y, cfg.z, cfg.phi, cfg.alpha]).ravel()


def _snap_circular(v, cands):
    v = v % 360.0
    d = np.abs((cands[None, :] - v[:, None] + 180.0) % 360.0 - 180.0)
    return cands[np.argmin(d, axis=1)]


def _snap(v, cands):
    return cands[np.argmin(np.abs(cands[None, :] - v[:, None]), axis=1)]


def decode(vec, template, rail_step):
    v = vec.reshape(-1, DIMS)
    x0, x1, y0, y1 = room_bounds(template)
    out = template.copy()
    out.x = np.clip(np.round(np.clip(v[:, 0], x0, x1) / rail_step) * rail_step, x0, x1)
    out.y = np.clip(np.round(np.clip(v[:, 1], y0, y1) / rail_step) * rail_step, y0, y1)
    out.z = _snap(v[:, 2], CANDIDATE_Z)
    out.phi = _snap_circular(v[:, 3], CANDIDATE_PHI)
    out.alpha = _snap(v[:, 4], CANDIDATE_ALPHA)
    return out


def movement(prev, new):
    return np.sqrt((new.x - prev.x) ** 2 + (new.y - prev.y) ** 2 + (new.z - prev.z) ** 2)


def movement_penalty(prev, new, params):
    diag = np.sqrt(params.length_m ** 2 + params.breadth_m ** 2 + params.height_m ** 2)
    return movement(prev, new).sum() / (prev.n * diag)


def cluster_penalty(cfg, d_min):
    """Legacy anti-clustering penalty: mean over AP pairs of max(0, 1 - d_ij / d_min)."""
    n = cfg.n
    d = np.hypot(cfg.x[:, None] - cfg.x[None, :], cfg.y[:, None] - cfg.y[None, :])
    iu = np.triu_indices(n, 1)
    return float(np.sum(np.maximum(0.0, 1.0 - d[iu] / d_min)) / max(len(iu[0]), 1))


def hungarian_by_room(prev, new):
    """Re-assign the new AP states to physical APs inside each room so that the
    total 3-D displacement is minimal (Kuhn 1955).  APs never change rooms."""
    out = new.copy()
    for r in np.unique(prev.room):
        idx = np.flatnonzero(prev.room == r)
        if len(idx) < 2:
            continue
        cost = np.sqrt((prev.x[idx, None] - new.x[None, idx]) ** 2
                       + (prev.y[idx, None] - new.y[None, idx]) ** 2
                       + (prev.z[idx, None] - new.z[None, idx]) ** 2)
        rows, cols = linear_sum_assignment(cost)
        src = idx[cols]
        for arr_out, arr_new in ((out.x, new.x), (out.y, new.y), (out.z, new.z),
                                 (out.phi, new.phi), (out.alpha, new.alpha)):
            arr_out[idx[rows]] = arr_new[src]
    return out


def _init_swarm(cfg, tier, n_particles, rng, opt, flat=False):
    n = cfg.n
    x0, x1, y0, y1 = room_bounds(cfg)
    base = encode(cfg).reshape(n, DIMS)
    swarm = np.repeat(base[None], n_particles, axis=0)
    for i in range(1, n_particles):
        if tier >= 2 or flat:
            swarm[i, :, 3] = rng.choice(CANDIDATE_PHI, n)
            swarm[i, :, 4] = rng.choice(CANDIDATE_ALPHA, n)
        if tier >= 3 or flat:
            swarm[i, :, 2] = rng.choice(CANDIDATE_Z, n)
        if tier >= 4 or flat:
            near = (not flat) and i <= int(round(opt.seed_near_fraction * n_particles))
            if near:
                r = opt.seed_near_radius_m
                swarm[i, :, 0] = np.clip(base[:, 0] + rng.uniform(-r, r, n), x0, x1)
                swarm[i, :, 1] = np.clip(base[:, 1] + rng.uniform(-r, r, n), y0, y1)
            else:
                swarm[i, :, 0] = rng.uniform(x0, x1)
                swarm[i, :, 1] = rng.uniform(y0, y1)
    return swarm.reshape(n_particles, n * DIMS)


def _free_mask(n, tier, flat=False):
    m = np.zeros(DIMS, dtype=bool)
    m[3:5] = True
    if tier >= 3 or flat:
        m[2] = True
    if tier >= 4 or flat:
        m[0:2] = True
    return np.tile(m, n)


def pso(cfg, fitness, tier, opt, rng, iters=None, flat=False):
    """Returns (best configuration, best fitness, curve of best fitness, evaluations)."""
    n = cfg.n
    S = opt.swarm
    T = iters if iters is not None else opt.iters
    vmax = np.tile(VMAX, n)
    free = _free_mask(n, tier, flat)
    pos = _init_swarm(cfg, tier, S, rng, opt, flat)
    vel = rng.uniform(-0.1, 0.1, pos.shape) * vmax * free
    pbest, pbest_f = pos.copy(), np.full(S, -np.inf)
    gbest, gbest_f = pos[0].copy(), -np.inf
    curve, evals = [], 0
    for it in range(T):
        for i in range(S):
            f = fitness(decode(pos[i], cfg, opt.rail_step_m))
            evals += 1
            if f > pbest_f[i]:
                pbest_f[i], pbest[i] = f, pos[i].copy()
            if f > gbest_f:
                gbest_f, gbest = f, pos[i].copy()
        curve.append(gbest_f)
        w = opt.w_start - (opt.w_start - opt.w_end) * it / T
        r1, r2 = rng.random(pos.shape), rng.random(pos.shape)
        vel = w * vel + opt.c1 * r1 * (pbest - pos) + opt.c2 * r2 * (gbest[None] - pos)
        vel = np.clip(vel * free, -vmax, vmax)
        pos = pos + vel
    return decode(gbest, cfg, opt.rail_step_m), gbest_f, curve, evals


def genetic(cfg, fitness, opt, rng, generations, tier=4, flat=True):
    """Real-coded GA: binary tournament, BLX-alpha crossover, Gaussian mutation, elitism.

    With flat=False only the dimensions of ``tier`` are searched (locked
    dimensions have lo = hi = current value), i.e. one tier of a hierarchical GA.
    """
    n = cfg.n
    S = opt.swarm
    x0, x1, y0, y1 = room_bounds(cfg)
    lo = np.column_stack([x0, y0, np.full(n, CANDIDATE_Z[0]), np.zeros(n),
                          np.full(n, CANDIDATE_ALPHA[0])]).ravel()
    hi = np.column_stack([x1, y1, np.full(n, CANDIDATE_Z[-1]), np.full(n, 360.0),
                          np.full(n, CANDIDATE_ALPHA[-1])]).ravel()
    free = _free_mask(n, tier, flat)
    cur = encode(cfg)
    lo, hi = np.where(free, lo, cur), np.where(free, hi, cur)
    span = hi - lo
    pop = _init_swarm(cfg, tier, S, rng, opt, flat=flat)
    fit = np.array([fitness(decode(ind, cfg, opt.rail_step_m)) for ind in pop])
    evals = S
    curve = [fit.max()]
    dim = pop.shape[1]
    for _ in range(generations - 1):
        elite = pop[np.argmax(fit)].copy()
        children = [elite]
        while len(children) < S:
            a, b = rng.integers(0, S, 2), rng.integers(0, S, 2)
            p1 = pop[a[np.argmax(fit[a])]]
            p2 = pop[b[np.argmax(fit[b])]]
            if rng.random() < opt.ga_crossover_prob:
                cmin, cmax = np.minimum(p1, p2), np.maximum(p1, p2)
                ext = opt.ga_blx_alpha * (cmax - cmin)
                child = rng.uniform(cmin - ext, cmax + ext)
            else:
                child = p1.copy()
            mut = rng.random(dim) < 1.0 / max(int(free.sum()), 1)
            child = child + mut * rng.normal(0, opt.ga_mutation_sigma, dim) * span
            child = np.clip(child, lo, hi)
            children.append(child)
        pop = np.array(children)
        fit = np.array([fitness(decode(ind, cfg, opt.rail_step_m)) for ind in pop])
        evals += S
        curve.append(max(curve[-1], fit.max()))
    best = pop[np.argmax(fit)]
    return decode(best, cfg, opt.rail_step_m), fit.max(), curve, evals
