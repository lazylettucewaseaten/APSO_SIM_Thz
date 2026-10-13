"""Baselines for the TeraMove evaluation (same fitness and decoding as the HPSO).

* standard PSO: every dimension free from the first iteration, uniform initialisation
  (``apso_optimize(..., tier=4, seed_near=False)``);
* real-coded genetic algorithm (``ga_optimize``);
* nearest-neighbour assignment, the naive alternative to the Hungarian matching.
"""
import numpy as np

from .config import CANDIDATE_ALPHA, CANDIDATE_Z, NUM_PARTICLES
from .optimizer import X_HI, X_LO, Y_HI, Y_LO, apso_optimize, compute_fitness, decode_routers


def standard_pso_optimize(routers, human_density, walls, prev_routers, iters, history=None):
    return apso_optimize(routers, human_density, walls, tier=4, prev_routers=prev_routers,
                         iters=iters, seed_near=False, history=history, verbose=False)


def ga_optimize(routers, human_density, walls, prev_routers, generations, history=None,
                pop_size=None, crossover_prob=0.9, blx_alpha=0.5, mutation_sigma=0.1):
    """Binary tournament, BLX-alpha crossover, Gaussian mutation (rate 1/dim), elitism.
    Genes use the same encoding and decoding as the PSO particles."""
    n = len(routers)
    pop_size = NUM_PARTICLES if pop_size is None else pop_size
    lo = np.tile([X_LO, Y_LO, CANDIDATE_Z[0], 0.0, CANDIDATE_ALPHA[0]], n)
    hi = np.tile([X_HI, Y_HI, CANDIDATE_Z[-1], 360.0, CANDIDATE_ALPHA[-1]], n)
    span = hi - lo
    dim = 5 * n
    pop = np.random.uniform(lo, hi, size=(pop_size, dim))
    pop[0] = [v for r in routers for v in (r['x'], r['y'], r['z'], r['phi'], r['alpha'])]   # incumbent

    def fit(ind):
        return compute_fitness(decode_routers(ind, n, routers), human_density, walls, prev_routers)

    f = np.array([fit(ind) for ind in pop])
    best_f = f.max()
    if history is not None:
        history.append(best_f)
    for _ in range(generations - 1):
        children = [pop[np.argmax(f)].copy()]                      # elitism
        while len(children) < pop_size:
            a, b = np.random.randint(0, pop_size, 2), np.random.randint(0, pop_size, 2)
            p1, p2 = pop[a[np.argmax(f[a])]], pop[b[np.argmax(f[b])]]
            if np.random.rand() < crossover_prob:
                cmin, cmax = np.minimum(p1, p2), np.maximum(p1, p2)
                ext = blx_alpha * (cmax - cmin)
                child = np.random.uniform(cmin - ext, cmax + ext)
            else:
                child = p1.copy()
            mut = np.random.rand(dim) < 1.0 / dim
            child = np.clip(child + mut * np.random.normal(0, mutation_sigma, dim) * span, lo, hi)
            children.append(child)
        pop = np.array(children)
        f = np.array([fit(ind) for ind in pop])
        best_f = max(best_f, f.max())
        if history is not None:
            history.append(best_f)
    return decode_routers(pop[np.argmax(f)], n, routers)


def nearest_neighbour_assign(prev_routers, new_routers):
    """Each existing AP, in index order, takes the nearest still-free new state."""
    free = list(range(len(new_routers)))
    out = []
    for r in prev_routers:
        d = [np.sqrt((r['x'] - new_routers[j]['x']) ** 2 + (r['y'] - new_routers[j]['y']) ** 2
                     + (r['z'] - new_routers[j]['z']) ** 2) for j in free]
        j = free.pop(int(np.argmin(d)))
        nr = dict(new_routers[j])
        if 'power' in r:
            nr['power'] = r['power']
        out.append(nr)
    return out
