"""Minimum-power THz control for a fixed association (Yates' framework).

For AP a with served users U_a and airtime load L_a = sum_u R_min / c_ua
(evaluated at the current powers), every served user can keep R_min while the
AP stretches the airtime to the full frame: user u then needs capacity
c*_u = c_ua * L_a, i.e. SINR target gamma_u = max(gamma_th, 2^(c*_u / B) - 1).

The map  I_a(p) = max_{u in U_a} gamma_u (N0 + sum_{b != a} G^r_{u,a,b} p_b G^t_{b,u} L_{b,u})
                                     / (g_ue G^t_{a,u} L_{a,u})
is a *standard interference function* (positive, monotone, scalable), so the
iteration p <- min(I(p), P_max) converges to the unique minimal fixed point
(Yates, IEEE JSAC 1995).  The current powers satisfy all targets (L_a <= 1), so
starting from them the iteration decreases monotonically and every served user
remains served: satisfaction never drops.
"""
import numpy as np


def sinr_targets(params, cap, assign, r_min, n_thz):
    """Per-user SINR target (linear), NaN for users not served by a THz AP."""
    t = params.thz
    k = cap.shape[0]
    gamma = np.full(k, np.nan)
    for a in range(n_thz):
        users = np.flatnonzero(assign == a)
        if len(users) == 0:
            continue
        c = cap[users, a]
        load = np.sum(r_min / c)
        c_star = c * load
        gamma[users] = np.maximum(t.sinr_th_lin, 2.0 ** (c_star / t.bandwidth_hz) - 1.0)
    # 1e-6 relative margin so that the converged fixed point (which meets the
    # target with equality up to the iteration tolerance) is not rejected by the
    # SINR >= gamma_th test because of floating-point rounding.
    return gamma * (1.0 + 1e-6)


def yates_min_power(terms, p_start, assign, gamma, p_max, tol=1e-9, max_iter=500):
    """Returns (powers, iterations, converged).  APs without THz users are switched off."""
    n = len(p_start)
    served = [np.flatnonzero(assign == a) for a in range(n)]
    p = np.where([len(s) > 0 for s in served], np.minimum(p_start, p_max), 0.0)
    g_ue = terms.g_ue
    for it in range(1, max_iter + 1):
        h = (p[:, None] * terms.Gt * terms.L).T                # (k, n)
        p_new = np.zeros(n)
        for a in range(n):
            users = served[a]
            if len(users) == 0:
                continue
            interf = (terms.Gr[users, a, :] * h[users, :]).sum(axis=1) - g_ue * h[users, a]
            need = gamma[users] * (terms.noise_w + np.maximum(interf, 0.0)) / (
                g_ue * terms.Gt[a, users] * terms.L[a, users])
            p_new[a] = min(p_max, need.max())
        delta = np.max(np.abs(p_new - p) / np.maximum(p, 1e-30))
        p = p_new
        if delta < tol:
            return p, it, True
    return p, max_iter, False
