"""Association, power control, optimiser and cascade tests."""
import itertools

import numpy as np
import pytest

from teramove_h.association import airtime, gap_exact, gap_greedy, gap_pace, slot_limits
from teramove_h.cascade import run_method
from teramove_h.config import DEFAULT as P
from teramove_h.crowd import density_map, drift_crowd, generate_crowd
from teramove_h.evaluator import evaluate
from teramove_h.geometry import ROOMS, WALLS, segment_distance
from teramove_h.network import Scenario, THzTerms, milp_config, thz_capacity
from teramove_h.optimizer import (cluster_penalty, decode, encode, hungarian_by_room, movement,
                                  pso)
from teramove_h.power import sinr_targets, yates_min_power

FAST = P.with_(opt={"swarm": 8, "iters": 4}, crowd={"n_people": 60})


def _feasible(assign, cap, r_min):
    load = np.zeros(cap.shape[1])
    for u, a in enumerate(assign):
        if a >= 0:
            assert cap[u, a] >= r_min
            load[a] += r_min / cap[u, a]
    return np.all(load <= 1 + 1e-9)


def _brute(cap, r_min):
    k, m = cap.shape
    best = 0
    for choice in itertools.product(range(-1, m), repeat=k):
        a = np.array(choice)
        ok = all(a[u] < 0 or cap[u, a[u]] >= r_min for u in range(k))
        if ok and _feasible(a, cap, r_min):
            best = max(best, int(np.sum(a >= 0)))
    return best


def test_gap_greedy_feasible_and_exact_optimal():
    rng = np.random.default_rng(3)
    for _ in range(40):
        k, m = rng.integers(2, 6), rng.integers(1, 3)
        cap = rng.choice([0.0, 1.2, 2.0, 3.5, 6.0], size=(k, m))
        a_g, _ = gap_greedy(cap, 1.0)
        a_e, _, _ = gap_exact(cap, 1.0)
        assert _feasible(a_g, cap, 1.0) and _feasible(a_e, cap, 1.0)
        opt = _brute(cap, 1.0)
        assert np.sum(a_e >= 0) == opt
        assert np.sum(a_g >= 0) <= opt


def test_slot_limits_match_brute_force():
    rng = np.random.default_rng(11)
    for _ in range(30):
        k, m = rng.integers(2, 7), rng.integers(1, 3)
        cap = rng.choice([0.0, 1.2, 2.0, 3.5, 6.0], size=(k, m))
        tau = airtime(cap, 1.0)
        lim = slot_limits(tau)
        for a in range(m):
            best = 0
            for sub in itertools.product([0, 1], repeat=k):
                idx = np.flatnonzero(sub)
                if np.all(np.isfinite(tau[idx, a])) and tau[idx, a].sum() <= 1 + 1e-12:
                    best = max(best, len(idx))
            assert lim[a] == best


def test_pace_is_feasible_certified_and_never_worse_than_greedy():
    rng = np.random.default_rng(7)
    wins = 0
    for _ in range(60):
        k, m = rng.integers(3, 7), rng.integers(2, 4)
        cap = rng.choice([0.0, 1.1, 1.6, 2.2, 3.1, 4.5], size=(k, m))
        a_p, load, info = gap_pace(cap, 1.0, info=True)
        assert _feasible(a_p, cap, 1.0)
        tau = airtime(cap, 1.0)
        rows = np.flatnonzero(a_p >= 0)
        assert np.allclose(load, np.bincount(a_p[rows], tau[rows, a_p[rows]], minlength=m))
        opt = _brute(cap, 1.0)
        n_p, n_g = np.sum(a_p >= 0), np.sum(gap_greedy(cap, 1.0)[0] >= 0)
        assert n_g <= n_p <= opt
        assert info["ub"] >= opt - 1e-9                 # weak duality
        if info["certified"]:
            assert n_p == opt
        wins += n_p > n_g
    assert wins > 0


def test_pace_ejection_chain_fixes_greedy_trap():
    # Greedy puts user 0 on AP 0 (smallest airtime 0.4); user 1 (only AP 0, 0.7) is
    # then blocked.  Optimum: user 0 on AP 1, user 1 on AP 0.
    cap = np.array([[2.5, 2.0], [1.0 / 0.7, 0.0]])
    assert np.sum(gap_greedy(cap, 1.0)[0] >= 0) == 1
    a, _, info = gap_pace(cap, 1.0, info=True)
    assert list(a) == [1, 0] and info["certified"]


def _scenario(seed=0, params=P):
    rng = np.random.default_rng(seed)
    return Scenario(params, generate_crowd(rng, params.crowd))


def test_crowd_constraints_and_determinism():
    rng = np.random.default_rng(5)
    cr = generate_crowd(rng, P.crowd)
    d = np.hypot(*(cr.xy[:, None, :] - cr.xy[None, :, :]).transpose(2, 0, 1))
    np.fill_diagonal(d, np.inf)
    assert d.min() >= P.crowd.min_separation_m
    for x, y in cr.xy:
        assert min(segment_distance(x, y, w) for w in WALLS) >= P.crowd.wall_clearance_m
    cr2 = generate_crowd(np.random.default_rng(5), P.crowd)
    assert np.array_equal(cr.xy, cr2.xy)
    nxt = drift_crowd(cr, rng, P.crowd)
    assert np.array_equal(nxt.active, cr.active) and nxt.n_people == cr.n_people
    assert density_map(cr, P.crowd).max() <= 1.0


def test_single_ap_sinr_equals_snr():
    sc = _scenario(1)
    cfg = milp_config(P)
    terms = THzTerms(P, cfg, sc.true_view.users)
    p = np.zeros(cfg.n)
    p[3] = 0.1
    s = terms.sinr(p)
    snr = 0.1 * terms.Gt[3] * terms.L[3] * terms.g_ue / terms.noise_w
    assert np.allclose(s[:, 3], snr)


def test_power_control_keeps_users_and_lowers_power():
    for seed in range(5):
        sc = _scenario(seed)
        cfg = milp_config(P)
        full, _ = evaluate(P, cfg, sc.true_view, "gap", True, power_control=False)
        pc, terms = evaluate(P, cfg, sc.true_view, "gap", True, power_control=True)
        assert pc.satisfaction >= full.satisfaction - 1e-12
        assert np.all(pc.p <= 0.1 + 1e-12)
        # every THz-served user meets R_min at the final powers
        cap = thz_capacity(P, terms.sinr(pc.p))
        for u in np.flatnonzero((pc.assign >= 0) & (pc.assign < cfg.n)):
            assert cap[u, pc.assign[u]] >= P.opt.r_min_bps * (1 - 1e-6)
        # idle APs are off
        for a in range(cfg.n):
            if not np.any(pc.assign == a):
                assert pc.p[a] == 0.0


def test_yates_is_monotone_from_feasible_start():
    sc = _scenario(2)
    cfg = milp_config(P)
    terms = THzTerms(P, cfg, sc.true_view.users)
    p0 = np.full(cfg.n, 0.1)
    cap = np.hstack([thz_capacity(P, terms.sinr(p0)), sc.true_view.wifi_rate])
    assign, _ = gap_greedy(cap, P.opt.r_min_bps)
    gamma = sinr_targets(P, cap, assign, P.opt.r_min_bps, cfg.n)
    p, it, conv = yates_min_power(terms, p0, assign, gamma, 0.1)
    assert conv
    s = terms.sinr(p)
    for u in np.flatnonzero((assign >= 0) & (assign < cfg.n)):
        assert s[u, assign[u]] >= gamma[u] * (1 - 1e-6)


def test_decode_respects_rooms_and_grid():
    cfg = milp_config(P)
    rng = np.random.default_rng(0)
    for _ in range(50):
        v = encode(cfg) + rng.normal(0, 20, cfg.n * 5)
        d = decode(v, cfg, 0.25)
        for i in range(cfg.n):
            x0, x1, y0, y1 = ROOMS[cfg.room[i]]
            assert x0 < d.x[i] < x1 and y0 < d.y[i] < y1
            assert abs(d.x[i] / 0.25 - round(d.x[i] / 0.25)) < 1e-9
        assert set(np.round(d.z, 1)) <= {2.0, 2.2, 2.4, 2.6, 2.8, 3.0}


def test_hungarian_never_increases_displacement():
    cfg = milp_config(P)
    rng = np.random.default_rng(1)
    for _ in range(20):
        new = decode(encode(cfg) + rng.normal(0, 5, cfg.n * 5), cfg, 0.25)
        h = hungarian_by_room(cfg, new)
        assert movement(cfg, h).sum() <= movement(cfg, new).sum() + 1e-9
        assert np.array_equal(h.room, cfg.room)


def test_ga_tier_respects_locked_dimensions():
    sc = _scenario(6, FAST)
    cfg = milp_config(FAST)
    from teramove_h.optimizer import genetic

    def fit(c):
        o, _ = evaluate(FAST, c, sc.true_view, "gap", True, fast=True)
        return o.satisfaction
    f0 = fit(cfg)
    for tier in (2, 3, 4):
        best, fbest, curve, _ = genetic(cfg, fit, FAST.opt, np.random.default_rng(tier), 4,
                                        tier=tier, flat=False)
        assert fbest >= f0 - 1e-12 and fit(best) == pytest.approx(fbest)
        if tier < 4:
            assert np.allclose(best.x, cfg.x) and np.allclose(best.y, cfg.y)
        if tier < 3:
            assert np.allclose(best.z, cfg.z)


def test_pso_never_worse_than_start():
    sc = _scenario(3, FAST)
    cfg = milp_config(FAST)

    def fit(c):
        o, _ = evaluate(FAST, c, sc.true_view, "gap", True, fast=True)
        return o.satisfaction - 0.3 * cluster_penalty(c, 3.0)
    f0 = fit(cfg)
    for tier in (2, 3, 4):
        best, fbest, curve, ev = pso(cfg, fit, tier, FAST.opt, np.random.default_rng(tier))
        assert fbest >= f0 - 1e-12 and fit(best) == pytest.approx(fbest)
        assert all(b >= a for a, b in zip(curve, curve[1:]))
        if tier < 4:
            assert np.allclose(best.x, cfg.x) and np.allclose(best.y, cfg.y)
        if tier < 3:
            assert np.allclose(best.z, cfg.z)


@pytest.mark.parametrize("method", ["static", "wifi_only", "teramove", "naive", "thz_only",
                                    "proposed", "proposed_nopc", "proposed_nomove",
                                    "proposed_hpso", "proposed_greedy", "flat_pso", "ga"])
def test_methods_run_and_are_consistent(method):
    sc = _scenario(4, FAST)
    cfg = milp_config(FAST)
    r = run_method(FAST, sc, cfg, method, np.random.default_rng(0))
    assert 0.0 <= r["satisfaction"] <= 1.0
    assert r["n_thz_served"] + r["n_wifi_served"] == round(r["satisfaction"] * r["n_users"])
    if method in ("static", "wifi_only"):
        assert r["displacement_m"] == 0.0
    if method.startswith("proposed"):
        t0 = r["stages"][0][1]
        assert r["satisfaction"] >= t0 - 1e-12
    if method == "proposed_nomove":
        assert r["displacement_m"] == 0.0
