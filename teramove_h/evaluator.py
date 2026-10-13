"""Inner (electronic) problem: association + power for a fixed AP geometry.

Association rules
-----------------
* ``gap``      proposed: greedy GAP over THz and Wi-Fi APs.
* ``maxsinr``  legacy: each user to its strongest-SINR THz AP (THz only).
* ``naive``    strongest THz AP, else best Wi-Fi AP (threshold offload).
* ``wifi``     Wi-Fi only.
"""
from dataclasses import dataclass

import numpy as np

from .association import admit, gap_greedy, max_sinr_pref, naive_offload_pref
from .network import THzTerms, thz_capacity
from .power import sinr_targets, yates_min_power


@dataclass
class Outcome:
    satisfaction: float          # fraction of active users with >= R_min
    quality: float               # mean_u min(1, best capacity / R_min)
    assign: np.ndarray           # (k,) AP index (THz 0..n-1, Wi-Fi n..), -1 unserved
    p: np.ndarray                # THz powers (W)
    load: np.ndarray             # airtime load per AP
    n_thz_served: int
    n_wifi_served: int
    yates_iters: int = 0


def _caps(params, terms, p, view, use_thz, use_wifi):
    k = view.k
    n = terms.L.shape[0]
    if use_thz:
        sinr = terms.sinr(p)
        cap_t = thz_capacity(params, sinr)
    else:
        sinr = np.zeros((k, n))
        cap_t = np.zeros((k, n))
    cap_w = view.wifi_rate if use_wifi else np.zeros((k, view.wifi_rate.shape[1]))
    return sinr, cap_t, cap_w


def _associate(rule, params, sinr, cap_t, cap_w, r_min):
    cap = np.hstack([cap_t, cap_w])
    if rule in ("gap", "wifi"):
        return gap_greedy(cap, r_min)
    if rule == "maxsinr":
        pref = max_sinr_pref(sinr)
        pref = np.where(cap_t[np.arange(len(pref)), pref] > 0, pref, -1) if cap_t.shape[1] else pref
        return admit(pref, cap, r_min)
    if rule == "naive":
        return admit(naive_offload_pref(sinr, cap_t, cap_w, params.thz.sinr_th_lin), cap, r_min)
    raise ValueError(rule)


def _outcome(assign, load, cap, p, n, k, r_min, yates_iters=0):
    served = assign >= 0
    best = cap.max(axis=1) if cap.shape[1] else np.zeros(k)
    q = float(np.mean(np.minimum(1.0, best / r_min))) if k else 1.0
    return Outcome(float(served.mean()) if k else 1.0, q, assign, p, load,
                   int(np.sum(served & (assign < n))), int(np.sum(assign >= n)), yates_iters)


def evaluate(params, cfg, view, rule="gap", use_wifi=True, power_control=False, fast=False):
    """Solve association (and optionally sleep + Yates power) for configuration ``cfg``.

    fast=True: association at the configured powers only (used inside the swarm).
    Otherwise: (i) associate at P_max with every AP awake, (ii) switch off THz
    APs without users and re-associate, keeping the best assignment, and
    (iii) if power_control, run Yates' minimum-power iteration.
    """
    o = params.opt
    r_min = o.r_min_bps
    use_thz = rule != "wifi"
    terms = THzTerms(params, cfg, view.users)
    n, k = cfg.n, view.k
    p_max = 10 ** (params.thz.p_max_dbm / 10) / 1000.0
    p = np.full(n, p_max) if use_thz else np.zeros(n)
    if not fast:
        cfg = cfg.copy()
    sinr, cap_t, cap_w = _caps(params, terms, p, view, use_thz, use_wifi)
    assign, load = _associate(rule, params, sinr, cap_t, cap_w, r_min)
    if fast:
        return _outcome(assign, load, np.hstack([cap_t, cap_w]), p, n, k, r_min), terms
    best = (assign, load, p.copy(), np.hstack([cap_t, cap_w]))
    if power_control and use_thz:
        for _ in range(o.assoc_rounds):
            awake = np.array([np.any(best[0] == a) for a in range(n)])
            p_try = np.where(awake, p_max, 0.0)
            if np.array_equal(p_try, best[2]):
                break
            sinr, cap_t, cap_w = _caps(params, terms, p_try, view, use_thz, use_wifi)
            cap_t[:, ~awake] = 0.0
            a2, l2 = _associate(rule, params, sinr, cap_t, cap_w, r_min)
            if np.sum(a2 >= 0) >= np.sum(best[0] >= 0):
                best = (a2, l2, p_try, np.hstack([cap_t, cap_w]))
            else:
                break
        assign, load, p_awake, cap = best
        gamma = sinr_targets(params, cap, assign, r_min, n)
        p_fin, iters, conv = yates_min_power(terms, p_awake, assign, gamma, p_max,
                                             o.yates_tol, o.yates_max_iter)
        if not conv:
            raise RuntimeError("Yates iteration did not converge")
        # Recompute capacities at the final powers; served users must stay served.
        sinr_f, cap_tf, cap_wf = _caps(params, terms, p_fin, view, use_thz, use_wifi)
        cap_f = np.hstack([cap_tf, cap_wf])
        load_f = np.zeros(cap_f.shape[1])
        for u in np.flatnonzero(assign >= 0):
            a = assign[u]
            if cap_f[u, a] < r_min * (1 - 1e-6):
                raise RuntimeError("power control dropped a served user")
            load_f[a] += r_min / cap_f[u, a]
        if np.any(load_f > 1 + 1e-6):
            raise RuntimeError("power control violated an airtime budget")
        out = _outcome(assign, load_f, best[3], p_fin, n, k, r_min, iters)
        return out, terms
    assign, load, p_b, cap = best
    return _outcome(assign, load, cap, p_b, n, k, r_min), terms
