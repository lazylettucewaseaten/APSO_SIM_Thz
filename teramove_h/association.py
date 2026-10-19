"""User association under per-AP airtime budgets.

Every AP time-shares its channel.  User u served by AP a at link capacity c_ua
needs airtime tau_ua = R_min / c_ua to receive R_min; an AP can grant at most a
total airtime of 1.  Maximising the number of satisfied users is a maximum
generalised assignment problem (GAP) with unit profits:

    max  sum_ua x_ua
    s.t. sum_a x_ua <= 1            for every user u
         sum_u tau_ua x_ua <= 1     for every AP a
         x_ua in {0, 1},  x_ua = 0 if c_ua < R_min.

Solvers
-------
* ``gap_greedy`` assigns pairs in increasing airtime order.
* ``gap_pace`` (proposed) -- Price-guided Association with Certified Ejection
  chains.  It starts from the greedy solution and combines:

  1. Slot cuts.  If AP a can hold at most K_a users (the K_a + 1 smallest
     airtimes already exceed 1), then sum_u x_ua <= K_a is a valid inequality.
     Adding it makes the LP relaxation much tighter.
  2. Lagrangian dual.  Dualising both AP constraints with an airtime price
     lam_a >= 0 and a slot price nu_a >= 0 gives, for every price vector,

         L(lam, nu) = sum_a (lam_a + K_a nu_a)
                      + sum_u max(0, max_a (1 - lam_a tau_ua - nu_a)),

     which upper-bounds the optimum (weak duality).  The prices are improved
     by projected subgradient steps (Polyak step towards the incumbent).
  3. Price-guided restarts.  Every few dual steps, users are re-assigned
     greedily in increasing order of priced cost lam_a tau_ua + nu_a, so that
     users avoid congested APs.
  4. Ejection chains.  An unserved user u enters AP a by pushing out a served
     user v, who moves to another AP b (and possibly pushes out w, who moves
     to c).  Every successful chain serves one more user and drops nobody.

  It keeps the best assignment found, so it never serves fewer users than the
  greedy.  It stops early when ub < served + 1.  Since the optimum is an
  integer, this proves that the assignment is optimal.
* ``gap_exact`` solves the ILP with HiGHS (scipy.optimize.milp) and is used
  only to measure the optimality gap of the heuristics on sampled instances.
"""
import numpy as np
from numba import njit
from scipy.optimize import Bounds, LinearConstraint, linprog, milp
from scipy.sparse import coo_matrix, vstack


@njit(cache=True)
def _greedy_scan(order_u, order_a, order_tau, k, m):
    assign = np.full(k, -1, dtype=np.int64)
    load = np.zeros(m)
    for i in range(order_u.shape[0]):
        u, a, tau = order_u[i], order_a[i], order_tau[i]
        if assign[u] >= 0:
            continue
        if load[a] + tau <= 1.0 + 1e-12:
            assign[u] = a
            load[a] += tau
    return assign, load


def airtime(cap, r_min):
    tau = np.full(cap.shape, np.inf)
    ok = cap >= r_min
    tau[ok] = r_min / cap[ok]
    return tau


def gap_greedy(cap, r_min):
    """Greedy GAP: returns (assignment (k,) with -1 = unserved, per-AP airtime load)."""
    k, m = cap.shape
    tau = airtime(cap, r_min)
    u, a = np.nonzero(np.isfinite(tau))
    t = tau[u, a]
    order = np.lexsort((a, u, t))           # primary key: airtime; ties broken by user, AP
    return _greedy_scan(u[order].astype(np.int64), a[order].astype(np.int64), t[order], k, m)


_EPS = 1e-12            # airtime tolerance, identical to the greedy feasibility test
_CERT = 1e-7            # margin of the integrality certificate ub < served + 1


@njit(cache=True)
def slot_limits(tau):
    """K_a: largest number of users AP a can serve (its smallest airtimes, summed)."""
    k, m = tau.shape
    lim = np.zeros(m)
    for a in range(m):
        t = np.sort(tau[:, a])
        s, c = 0.0, 0
        for i in range(k):
            if not np.isfinite(t[i]) or s + t[i] > 1.0 + _EPS:
                break
            s += t[i]
            c += 1
        lim[a] = c
    return lim


@njit(cache=True)
def _dual_value(tau, lim, lam, nu, choice):
    """Lagrangian dual function; ``choice`` receives each user's priced-best AP (-1 = none)."""
    k, m = tau.shape
    val = 0.0
    for a in range(m):
        val += lam[a] + lim[a] * nu[a]
    for u in range(k):
        best = 0.0
        choice[u] = -1
        for a in range(m):
            if np.isfinite(tau[u, a]):
                r = 1.0 - lam[a] * tau[u, a] - nu[a]
                if r > best:
                    best = r
                    choice[u] = a
        val += best
    return val


@njit(cache=True)
def _count(assign):
    c = 0
    for u in range(assign.shape[0]):
        if assign[u] >= 0:
            c += 1
    return c


@njit(cache=True)
def _try_insert(tau, assign, load, u, depth):
    """Serve unserved user u with an ejection chain of at most ``depth`` moves.

    depth 0: u joins an AP with enough free airtime.
    depth 1: u replaces v at AP a; v joins another AP b with free airtime.
    depth 2: as depth 1, but v replaces w at b and w joins a third AP c.
    The state is unchanged when no chain exists.
    """
    k, m = tau.shape
    for a in range(m):
        if np.isfinite(tau[u, a]) and load[a] + tau[u, a] <= 1.0 + _EPS:
            assign[u] = a
            load[a] += tau[u, a]
            return True
    if depth == 0:
        return False
    for a in range(m):
        tua = tau[u, a]
        if not np.isfinite(tua):
            continue
        for v in range(k):
            if assign[v] != a or v == u or load[a] - tau[v, a] + tua > 1.0 + _EPS:
                continue
            load[a] += tua - tau[v, a]
            assign[u] = a
            assign[v] = -1
            for b in range(m):
                if b != a and np.isfinite(tau[v, b]) and load[b] + tau[v, b] <= 1.0 + _EPS:
                    assign[v] = b
                    load[b] += tau[v, b]
                    return True
            if depth >= 2:
                for b in range(m):
                    tvb = tau[v, b]
                    if b == a or not np.isfinite(tvb):
                        continue
                    for w in range(k):
                        if assign[w] != b or w == u or load[b] - tau[w, b] + tvb > 1.0 + _EPS:
                            continue
                        load[b] += tvb - tau[w, b]
                        assign[v] = b
                        assign[w] = -1
                        for c in range(m):
                            if c != b and np.isfinite(tau[w, c]) and load[c] + tau[w, c] <= 1.0 + _EPS:
                                assign[w] = c
                                load[c] += tau[w, c]
                                return True
                        load[b] -= tvb - tau[w, b]
                        assign[v] = -1
                        assign[w] = b
            load[a] -= tua - tau[v, a]
            assign[u] = -1
            assign[v] = a
    return False


@njit(cache=True)
def _augment(tau, assign, load, depth):
    """Apply ejection chains of length <= depth until no unserved user can be added."""
    if depth == 1:
        _augment1(tau, assign, load)
        return
    improved = True
    while improved:
        improved = False
        for u in range(tau.shape[0]):
            if assign[u] < 0 and _try_insert(tau, assign, load, u, depth):
                improved = True


@njit(cache=True)
def _relocation_targets(tau, assign, load, alt):
    """alt[v]: AP with free airtime (smallest tau) that served user v could move to, -1 if none."""
    k, m = tau.shape
    for v in range(k):
        alt[v] = -1
        a = assign[v]
        if a < 0:
            continue
        bt = np.inf
        for b in range(m):
            if b != a and tau[v, b] < bt and load[b] + tau[v, b] <= 1.0 + _EPS:
                alt[v] = b
                bt = tau[v, b]


@njit(cache=True)
def _augment1(tau, assign, load):
    """Depth-1 ejection chains (u joins a, v leaves a for its relocation target).
    Same moves as _try_insert(depth=1); relocation targets are precomputed so a
    scan costs O(k m) per unserved user instead of O(k m^2)."""
    k, m = tau.shape
    alt = np.empty(k, dtype=np.int64)
    _relocation_targets(tau, assign, load, alt)
    improved = True
    while improved:
        improved = False
        for u in range(k):
            if assign[u] >= 0:
                continue
            done = False
            for a in range(m):
                if np.isfinite(tau[u, a]) and load[a] + tau[u, a] <= 1.0 + _EPS:
                    assign[u] = a
                    load[a] += tau[u, a]
                    done = True
                    break
            if not done:
                for a in range(m):
                    tua = tau[u, a]
                    if not np.isfinite(tua):
                        continue
                    for v in range(k):
                        if assign[v] == a and alt[v] >= 0 and load[a] - tau[v, a] + tua <= 1.0 + _EPS:
                            b = alt[v]
                            load[a] += tua - tau[v, a]
                            assign[u] = a
                            assign[v] = b
                            load[b] += tau[v, b]
                            done = True
                            break
                    if done:
                        break
            if done:
                improved = True
                _relocation_targets(tau, assign, load, alt)


@njit(cache=True)
def _relocate(tau, assign, load):
    """Move served users to an AP with a smaller airtime while it fits (count unchanged)."""
    k, m = tau.shape
    improved = True
    while improved:
        improved = False
        for u in range(k):
            a = assign[u]
            if a < 0:
                continue
            nb, nt = -1, tau[u, a]
            for b in range(m):
                if b != a and tau[u, b] < nt and load[b] + tau[u, b] <= 1.0 + _EPS:
                    nb, nt = b, tau[u, b]
            if nb >= 0:
                load[a] -= tau[u, a]
                load[nb] += nt
                assign[u] = nb
                improved = True


@njit(cache=True)
def _priced_greedy(tau, pu, pa, pt, lam, nu, depth):
    """Greedy over the feasible pairs (pu, pa, pt) sorted by priced cost lam_a tau + nu_a,
    ties by airtime, user, AP; followed by ejection chains."""
    k, m = tau.shape
    key = lam[pa] * pt + nu[pa]
    o1 = np.argsort(pt, kind="mergesort")
    order = o1[np.argsort(key[o1], kind="mergesort")]
    assign = np.full(k, -1, dtype=np.int64)
    load = np.zeros(m)
    for j in order:
        u, a = pu[j], pa[j]
        if assign[u] < 0 and load[a] + pt[j] <= 1.0 + _EPS:
            assign[u] = a
            load[a] += pt[j]
    _augment(tau, assign, load, depth)
    return assign, load


@njit(cache=True)
def _pace(tau, pu, pa, pt, assign0, load0, iters, every):
    k, m = tau.shape
    lim = slot_limits(tau)
    best_a, best_l = assign0.copy(), load0.copy()
    _augment(tau, best_a, best_l, 1)
    lb = _count(best_a)
    lam, nu = np.zeros(m), np.zeros(m)
    choice = np.empty(k, dtype=np.int64)
    g1, g2 = np.empty(m), np.empty(m)
    ub, theta, stall = np.inf, 1.0, 0
    for it in range(iters):
        val = _dual_value(tau, lim, lam, nu, choice)
        if val < ub - 1e-9:
            ub, stall = val, 0
        else:
            stall += 1
            if stall >= 20:
                theta, stall = 0.5 * theta, 0
        if ub < lb + 1 - _CERT:
            break
        if it > 0 and it % every == 0:
            a2, l2 = _priced_greedy(tau, pu, pa, pt, lam, nu, 1)
            c = _count(a2)
            if c > lb:
                lb, best_a, best_l = c, a2, l2
                if ub < lb + 1 - _CERT:
                    break
        # subgradient of L at (lam, nu), projected onto lam, nu >= 0
        for a in range(m):
            g1[a] = 1.0
            g2[a] = lim[a]
        for u in range(k):
            a = choice[u]
            if a >= 0:
                g1[a] -= tau[u, a]
                g2[a] -= 1.0
        nrm = 0.0
        for a in range(m):
            if lam[a] <= 0.0 and g1[a] > 0.0:
                g1[a] = 0.0
            if nu[a] <= 0.0 and g2[a] > 0.0:
                g2[a] = 0.0
            nrm += g1[a] * g1[a] + g2[a] * g2[a]
        if nrm < 1e-18:      # zero subgradient: (lam, nu) minimises L
            break
        step = theta * (val - (lb + 0.5)) / nrm
        for a in range(m):
            lam[a] = max(0.0, lam[a] - step * g1[a])
            nu[a] = max(0.0, nu[a] - step * g2[a])
    if not ub < lb + 1 - _CERT:
        _augment(tau, best_a, best_l, 2)
        lb = _count(best_a)
    _relocate(tau, best_a, best_l)
    return best_a, best_l, ub


def gap_pace(cap, r_min, iters=200, every=5, info=False):
    """PACE association (see module docstring).

    Returns (assignment (k,) with -1 = unserved, per-AP airtime load); with
    info=True also a dict with the dual upper bound ``ub`` on the number of
    servable users and ``certified`` (True when the assignment is provably optimal).
    """
    k, m = cap.shape
    tau = airtime(cap, r_min)
    u, a = np.nonzero(np.isfinite(tau))
    t = tau[u, a]
    order = np.lexsort((a, u, t))
    pu, pa, pt = u[order].astype(np.int64), a[order].astype(np.int64), t[order]
    a0, l0 = _greedy_scan(pu, pa, pt, k, m)
    if len(pu) == 0:
        assign, load, ub = a0, l0, 0.0
    else:
        assign, load, ub = _pace(tau, pu, pa, pt, a0, l0, iters, every)
    if not info:
        return assign, load
    served = int(np.sum(assign >= 0))
    return assign, load, {"ub": float(ub), "certified": bool(ub < served + 1 - _CERT)}


def gap_exact(cap, r_min, time_limit=60.0):
    """Exact GAP via HiGHS. Returns (assignment, load, status)."""
    k, m = cap.shape
    tau = airtime(cap, r_min)
    u, a = np.nonzero(np.isfinite(tau))
    nv = len(u)
    if nv == 0:
        return np.full(k, -1), np.zeros(m), "empty"
    rows_u = coo_matrix((np.ones(nv), (u, np.arange(nv))), shape=(k, nv))
    rows_a = coo_matrix((tau[u, a], (a, np.arange(nv))), shape=(m, nv))
    cons = [LinearConstraint(rows_u, -np.inf, 1.0), LinearConstraint(rows_a, -np.inf, 1.0)]
    res = milp(c=-np.ones(nv), constraints=cons, integrality=np.ones(nv),
               bounds=Bounds(0, 1), options={"time_limit": time_limit, "mip_rel_gap": 0.0})
    assign = np.full(k, -1)
    load = np.zeros(m)
    if res.x is not None:
        chosen = res.x > 0.5
        assign[u[chosen]] = a[chosen]
        np.add.at(load, a[chosen], tau[u[chosen], a[chosen]])
    return assign, load, res.message


def gap_lp_bound(cap, r_min, slot_cuts=True):
    """Value of the LP relaxation (optionally with the slot cuts), via HiGHS.
    Analysis only: min L(lam, nu) of PACE's dual equals the value with slot cuts."""
    k, m = cap.shape
    tau = airtime(cap, r_min)
    u, a = np.nonzero(np.isfinite(tau))
    nv = len(u)
    if nv == 0:
        return 0.0
    rows = [coo_matrix((np.ones(nv), (u, np.arange(nv))), shape=(k, nv)),
            coo_matrix((tau[u, a], (a, np.arange(nv))), shape=(m, nv))]
    rhs = [np.ones(k), np.ones(m)]
    if slot_cuts:
        rows.append(coo_matrix((np.ones(nv), (a, np.arange(nv))), shape=(m, nv)))
        rhs.append(slot_limits(tau))
    res = linprog(-np.ones(nv), A_ub=vstack(rows), b_ub=np.concatenate(rhs), bounds=(0, 1),
                  method="highs")
    if res.status != 0:
        raise RuntimeError(res.message)
    return -res.fun


def admit(pref, cap, r_min):
    """Fixed preference (one AP per user, -1 = none); each AP admits its users in
    increasing airtime order until the budget is used.  Used by the max-SINR and
    naive-offload baselines."""
    k, m = cap.shape
    big = np.zeros_like(cap)
    rows = np.flatnonzero(pref >= 0)
    big[rows, pref[rows]] = cap[rows, pref[rows]]
    return gap_greedy(big, r_min)


def max_sinr_pref(sinr_thz):
    """Each user prefers the THz AP with the highest SINR."""
    return np.argmax(sinr_thz, axis=1) if sinr_thz.shape[1] else np.full(sinr_thz.shape[0], -1)


def naive_offload_pref(sinr_thz, cap_thz, cap_wifi, sinr_th_lin):
    """Strongest THz AP if its SINR meets the threshold, else the best Wi-Fi AP."""
    k, n = cap_thz.shape
    pref = np.full(k, -1)
    best = np.argmax(sinr_thz, axis=1)
    ok = sinr_thz[np.arange(k), best] >= sinr_th_lin
    pref[ok] = best[ok]
    if cap_wifi.shape[1]:
        bw = np.argmax(cap_wifi, axis=1)
        has = cap_wifi[np.arange(k), bw] > 0
        sel = (~ok) & has
        pref[sel] = n + bw[sel]
    return pref
