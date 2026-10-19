"""Adaptation pipelines: the proposed TeraMove-H cascade and all baselines.

Proposed cascade (stop at the first stage that reaches S >= eta):
  T0  re-associate users over THz + Wi-Fi APs (no hardware change)
  T1  switch off idle THz APs, re-associate, minimum-power control
  T2  search over azimuth and sector width only (electronic, 1 budget unit)
  M   search over height, (x, y) inside the AP's room (ceiling rail) and beams
      (mechanical, 3 budget units), Hungarian matching inside each room
A final minimum-power trim is always applied.  One budget unit is
swarm * iters fitness evaluations; flat baselines receive the same worst-case
budget (4 units).  The published TeraMove (legacy fitness, PSO tiers 2/3/4 of
one unit each) is reproduced by method ``teramove``.
"""
import time
from dataclasses import dataclass

import numpy as np

from .evaluator import evaluate
from .network import grid_coverage
from .optimizer import (cluster_penalty, genetic, hungarian_by_room, movement,
                        movement_penalty, pso)


FLAT_BUDGET_UNITS = 4   # one unit = swarm * iters fitness evaluations


@dataclass(frozen=True)
class Method:
    name: str
    kind: str                 # static | cascade | legacy | flat_pso | ga | wifi
    rule: str = "gap"
    use_wifi: bool = True
    power_control: bool = True
    max_tier: int = 4
    tier_alg: str = "pso"     # optimiser inside each cascade tier: pso | ga
    # (tier, budget multiple of swarm*iters); tier 4 frees every dimension.
    schedule: tuple = ((2, 1), (3, 1), (4, 1))


PROPOSED_SCHEDULE = ((2, 1), (4, 3))          # beams (1 unit), then all dimensions (3 units)
HPSO_SCHEDULE = ((2, 1), (3, 1), (4, 2))      # TeraMove tiers, same 4-unit worst case

METHODS = {
    # baselines
    "static": Method("static", "static", rule="maxsinr", use_wifi=False, power_control=False),
    "teramove": Method("teramove", "legacy", rule="maxsinr", use_wifi=False, power_control=False),
    "wifi_only": Method("wifi_only", "wifi", rule="wifi", use_wifi=True, power_control=False),
    "naive": Method("naive", "cascade", rule="naive", tier_alg="ga", schedule=PROPOSED_SCHEDULE),
    "thz_only": Method("thz_only", "cascade", use_wifi=False, tier_alg="ga", schedule=PROPOSED_SCHEDULE),
    "flat_pso": Method("flat_pso", "flat_pso"),
    "ga": Method("ga", "ga"),
    # proposed and ablations
    "proposed": Method("proposed", "cascade", tier_alg="ga", schedule=PROPOSED_SCHEDULE),
    "proposed_nopc": Method("proposed_nopc", "cascade", power_control=False, tier_alg="ga",
                            schedule=PROPOSED_SCHEDULE),
    "proposed_nomove": Method("proposed_nomove", "cascade", tier_alg="ga", schedule=PROPOSED_SCHEDULE,
                              max_tier=2),
    "proposed_hpso": Method("proposed_hpso", "cascade", tier_alg="pso", schedule=HPSO_SCHEDULE),
    "proposed_greedy": Method("proposed_greedy", "cascade", rule="greedy", tier_alg="ga",
                              schedule=PROPOSED_SCHEDULE),
}


def proposed_fitness(params, view, start_cfg, method):
    o = params.opt

    def f(cfg):
        out, _ = evaluate(params, cfg, view, method.rule, method.use_wifi, fast=True)
        bonus = o.bonus if out.satisfaction >= o.target_satisfaction else 0.0
        return (o.w_sat * out.satisfaction + o.w_quality * out.quality + bonus
                - o.beta_move * movement_penalty(start_cfg, cfg, params)
                - o.gamma_cluster * cluster_penalty(cfg, o.d_min_m))
    return f


def legacy_fitness(params, view, start_cfg, p_max):
    """TeraMove fitness: 0.4 cell coverage + 0.6 density coverage + bonus - penalties."""
    o = params.opt

    def f(cfg):
        cfg = cfg.copy()
        cfg.p[:] = p_max
        _, cell, dens = grid_coverage(params, cfg, view)
        bonus = o.bonus if dens >= o.target_satisfaction else 0.0
        return (0.4 * cell + 0.6 * dens + bonus
                - o.beta_move * movement_penalty(start_cfg, cfg, params)
                - o.gamma_cluster * cluster_penalty(cfg, o.d_min_m))
    return f


def _p_max(params):
    return 10 ** (params.thz.p_max_dbm / 10) / 1000.0


def _final(params, scen, cfg, method, start_cfg, stages, evals, t0, curves, t0_out=None):
    out, _ = evaluate(params, cfg, scen.true_view, method.rule, method.use_wifi,
                      power_control=method.power_control)
    cfg = cfg.copy()
    cfg.p = out.p.copy()
    mv = movement(start_cfg, cfg)
    return {
        "method": method.name,
        "satisfaction": out.satisfaction,
        "n_users": scen.n_users,
        "n_thz_served": out.n_thz_served,
        "n_wifi_served": out.n_wifi_served,
        "tier": stages[-1][0] if stages else 0,
        "stages": stages,
        "evals": evals,
        "displacement_m": float(mv.sum()),
        "max_displacement_m": float(mv.max()),
        "n_moved": int(np.sum(mv > 1e-9)),
        "latency_s": float(mv.max() / params.opt.rail_speed_mps),
        "p_sum_w": float(out.p.sum()),
        "n_asleep": int(np.sum(out.p <= 0)),
        "runtime_s": time.perf_counter() - t0,
        "curves": curves,
        # T0 association bound (PACE): no association at the starting geometry and
        # P_max serves more than floor(t0_ub) of the sensed users.
        "t0_ub": t0_out.assoc_ub if t0_out is not None else float("nan"),
        "t0_certified": bool(t0_out.assoc_certified) if t0_out is not None else False,
        "assign": out.assign,
        "cfg": cfg,
    }


def run_method(params, scen, start_cfg, method_name, rng):
    """Adapt ``start_cfg`` to scenario ``scen`` with one method; returns a result dict."""
    m = METHODS[method_name] if isinstance(method_name, str) else method_name
    o = params.opt
    t0 = time.perf_counter()
    p_max = _p_max(params)
    cfg = start_cfg.copy()
    cfg.p[:] = p_max
    ctx = scen.ctx_view
    stages, curves, evals = [], {}, 0

    if m.kind in ("static", "wifi"):
        out, _ = evaluate(params, cfg, ctx, m.rule, m.use_wifi)
        stages.append((0, out.satisfaction))
        return _final(params, scen, cfg, m, start_cfg, stages, evals, t0, curves)

    if m.kind == "legacy":
        _, _, dens = grid_coverage(params, cfg, ctx)
        stages.append((0, dens))
        if dens < o.target_satisfaction:
            fit = legacy_fitness(params, ctx, start_cfg, p_max)
            cur = cfg
            for tier in (2, 3, 4):
                new, _, curve, ev = pso(cur, fit, tier, o, rng)
                if tier == 4:
                    new = hungarian_by_room(start_cfg, new)
                evals += ev
                curves[tier] = curve
                new.p[:] = p_max
                _, _, dens = grid_coverage(params, new, ctx)
                stages.append((tier, dens))
                cur = new
                if dens >= o.target_satisfaction:
                    break
            cfg = cur
        return _final(params, scen, cfg, m, start_cfg, stages, evals, t0, curves)

    # T0: re-association only
    out, _ = evaluate(params, cfg, ctx, m.rule, m.use_wifi, power_control=False)
    t0_out = out
    stages.append((0, out.satisfaction))
    best_s = out.satisfaction
    if best_s >= o.target_satisfaction:
        return _final(params, scen, cfg, m, start_cfg, stages, evals, t0, curves, t0_out)
    # T1: sleep idle APs + re-association + minimum power
    if m.power_control:
        out, _ = evaluate(params, cfg, ctx, m.rule, m.use_wifi, power_control=True)
        stages.append((1, out.satisfaction))
        best_s = max(best_s, out.satisfaction)
        if best_s >= o.target_satisfaction:
            return _final(params, scen, cfg, m, start_cfg, stages, evals, t0, curves, t0_out)

    fit = proposed_fitness(params, ctx, start_cfg, m)
    if m.kind == "cascade":
        cur = cfg
        for tier, mult in m.schedule:
            if tier > m.max_tier:
                break
            if m.tier_alg == "ga":
                new, _, curve, ev = genetic(cur, fit, o, rng, mult * o.iters, tier=tier, flat=False)
            else:
                new, _, curve, ev = pso(cur, fit, tier, o, rng, iters=mult * o.iters)
            if tier == 4:
                new = hungarian_by_room(start_cfg, new)
            evals += ev
            curves[tier] = curve
            new.p[:] = p_max
            out, _ = evaluate(params, new, ctx, m.rule, m.use_wifi, power_control=m.power_control)
            stages.append((tier, out.satisfaction))
            if out.satisfaction >= best_s:      # never accept a configuration that serves fewer users
                cur, best_s = new, out.satisfaction
            if best_s >= o.target_satisfaction:
                break
        cfg = cur
    else:  # flat_pso / ga with the worst-case budget of the cascade
        budget_iters = FLAT_BUDGET_UNITS * o.iters
        if m.kind == "flat_pso":
            new, _, curve, ev = pso(cfg, fit, 4, o, rng, iters=budget_iters, flat=True)
        else:
            new, _, curve, ev = genetic(cfg, fit, o, rng, generations=budget_iters)
        new = hungarian_by_room(start_cfg, new)
        new.p[:] = p_max
        evals += ev
        curves["flat"] = curve
        out, _ = evaluate(params, new, ctx, m.rule, m.use_wifi, power_control=m.power_control)
        stages.append((4, out.satisfaction))
        if out.satisfaction >= best_s:
            cfg = new
    return _final(params, scen, cfg, m, start_cfg, stages, evals, t0, curves, t0_out)
