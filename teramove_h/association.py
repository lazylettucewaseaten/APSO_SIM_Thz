"""User association under per-AP airtime budgets.

Every AP time-shares its channel.  User u served by AP a at link capacity c_ua
needs airtime tau_ua = R_min / c_ua to receive R_min; an AP can grant at most a
total airtime of 1.  Maximising the number of satisfied users is a maximum
generalised assignment problem (GAP) with unit profits:

    max  sum_ua x_ua
    s.t. sum_a x_ua <= 1            for every user u
         sum_u tau_ua x_ua <= 1     for every AP a
         x_ua in {0, 1},  x_ua = 0 if c_ua < R_min.

``gap_greedy`` assigns pairs in increasing airtime order.  ``gap_exact`` solves
the ILP with HiGHS (scipy.optimize.milp) and is used only to measure the
greedy's optimality gap on sampled instances.
"""
import numpy as np
from numba import njit
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix


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
