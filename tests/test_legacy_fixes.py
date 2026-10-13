"""Regression tests for the corrections made to the legacy TeraMove simulator (chsr_sim)."""
import numpy as np

import chsr_sim.physics as lp
from chsr_sim.config import CANDIDATE_Z, K_F
from chsr_sim.environment import gen_walls
from chsr_sim.optimizer import apso_optimize, compute_fitness, compute_total_movement, decode_routers

WALLS = gen_walls()
EMPTY = np.zeros((32, 20))


def _sinr(routers):
    lp._ROUTER_STATIC_CACHE.clear()
    return lp.calculate_sinr(routers, EMPTY, WALLS)[0]


def test_compass_azimuth():
    """An AP in the open hall pointing North (0 deg) must cover the cell north of it,
    not the cell east of it; pointing East (90 deg) the opposite."""
    ap = {"x": 16.0, "y": 14.0, "z": 2.4, "alpha": 30.0, "power": 1.0}
    north = _sinr([dict(ap, phi=0.0)])
    east = _sinr([dict(ap, phi=90.0)])
    assert north[16, 18] > north[20, 14] + 20
    assert east[20, 14] > east[16, 18] + 20


def test_heights_and_absorption():
    assert np.isclose(CANDIDATE_Z.max(), 3.0) and np.isclose(CANDIDATE_Z.min(), 2.0)
    assert np.isclose(4.343 * K_F * 1000, 6.677, rtol=1e-3)


def test_decode_keeps_wall_mounted_aps():
    r = [{"x": 0.5, "y": 19.5, "z": 2.4, "phi": 135.0, "alpha": 60.0, "power": 1.0}]
    pos = np.array([0.5, 19.5, 2.4, 135.0, 60.0])
    d = decode_routers(pos, 1, r)[0]
    assert d["x"] == 0.5 and d["y"] == 19.5


def test_tier2_never_moves_and_never_worsens():
    np.random.seed(0)
    routers = [{"x": x, "y": y, "z": 2.4, "phi": 45.0, "alpha": 60.0, "power": 1.0}
               for x, y in ((0.5, 19.5), (16.5, 0.5), (28.5, 12.5), (14.5, 12.5))]
    dens = np.zeros((32, 20))
    dens[10:14, 14:18] = 1.0
    f0 = compute_fitness(routers, dens, WALLS, routers)
    out = apso_optimize(routers, dens, WALLS, tier=2, prev_routers=routers, iters=3, verbose=False)
    assert compute_total_movement(routers, out) == 0.0
    assert compute_fitness(out, dens, WALLS, routers) >= f0 - 1e-12


def test_cache_follows_density_content_not_identity():
    """A different crowd map in a re-used buffer must not reuse stale path losses."""
    routers = [{"x": 16.0, "y": 14.0, "z": 2.4, "phi": 0.0, "alpha": 60.0, "power": 1.0}]
    buf = np.zeros((32, 20))
    clear = lp.calculate_sinr(routers, buf, WALLS)[0].copy()
    buf[14:19, 15:17] = 1.0            # same object, new content: a crowd in front of the AP
    blocked = lp.calculate_sinr(routers, buf, WALLS)[0]
    lp._ROUTER_STATIC_CACHE.clear()
    fresh = lp.calculate_sinr(routers, buf, WALLS)[0]
    assert np.array_equal(blocked, fresh)
    assert not np.array_equal(clear, blocked)


def test_gain_coupled_to_beamwidth():
    assert np.isclose(lp.main_lobe_gain(60), 30.0)
    assert np.isclose(lp.main_lobe_gain(30), 33.0103, atol=1e-3)
    assert np.isclose(lp.main_lobe_gain(120), 26.9897, atol=1e-3)


def _base_power(dens, ap=(16.0, 2.0, 3.0), sat=True):
    w = np.zeros((0, 6))
    bp, _ = lp._compute_single_router_static_data(
        ap[0], ap[1], ap[2], dens, w, 32, 20, lp.Z_U, lp.F_HZ, lp.C, lp.K_F, lp.H_HUMAN,
        lp.HUMAN_PENALTY_DB, lp.PTX_DBM, True, sat, True, True)
    return bp


def test_saturating_blockage_bounded_and_monotone():
    empty = _base_power(np.zeros((32, 20)))
    # a crowd line between the AP (16, 2) and the user cells near y = 18
    losses = []
    for level in (0.25, 0.5, 1.0):
        dens = np.zeros((32, 20))
        dens[10:23, 12:18] = level
        losses.append(empty[16, 18] - _base_power(dens)[16, 18])
    assert all(0.0 <= L <= lp.HUMAN_PENALTY_DB + 1e-9 for L in losses)
    assert losses[0] < losses[1] < losses[2]
    assert np.isclose(losses[2], lp.HUMAN_PENALTY_DB)          # a full cell blocks completely


def test_ray_height_measured_from_user():
    """A crowd right next to the AP is above head height (ray still high there) and must
    not block; the same crowd next to the user must."""
    empty = _base_power(np.zeros((32, 20)))
    near_ap = np.zeros((32, 20))
    near_ap[16, 3:5] = 1.0
    near_user = np.zeros((32, 20))
    near_user[16, 15:17] = 1.0
    assert np.isclose(empty[16, 18], _base_power(near_ap)[16, 18])
    assert empty[16, 18] - _base_power(near_user)[16, 18] > 10.0


def test_users_at_cell_centres():
    """AP at (16.5, 14.5) pointing North with a 30 deg beam (+-15 deg).  The user of cell
    (15, 18) sits at (15.5, 18.5), bearing -14.0 deg: inside.  At the corner (15, 18) the
    bearing would be -23.2 deg: outside.  Cell (14, 18) is outside either way."""
    ap = {"x": 16.5, "y": 14.5, "z": 2.4, "alpha": 30.0, "phi": 0.0, "power": 1.0}
    s = _sinr([ap])
    assert s[15, 18] > s[14, 18] + 20


def test_fixed_association_never_beats_best_server():
    routers = [{"x": x, "y": y, "z": 2.6, "phi": p, "alpha": 90.0, "power": 1.0}
               for x, y, p in ((16.5, 13.0, 90.0), (16.5, 19.5, 180.0), (5.0, 13.0, 90.0))]
    lp._ROUTER_STATIC_CACHE.clear()
    _, _, serving = lp.calculate_sinr(routers, EMPTY, WALLS, return_serving=True)
    dens = np.zeros((32, 20))
    dens[8:24, 14:17] = 0.8
    s_best, c_best = lp.calculate_sinr(routers, dens, WALLS)
    s_fix, c_fix = lp.calculate_sinr(routers, dens, WALLS, serving=serving)
    assert np.all(s_fix <= s_best + 1e-9)
    assert c_fix <= c_best + 1e-12
    # with the same crowd as at design time, fixed and best server agree
    s0, _ = lp.calculate_sinr(routers, EMPTY, WALLS, serving=serving)
    assert np.allclose(s0, lp.calculate_sinr(routers, EMPTY, WALLS)[0])


def _keep_by_sampling(rx, ry, rz, ux, uy, dens, n=20000):
    """Reference for _link_keep_jit: dense sampling of the segment."""
    zu, h = lp.Z_U, lp.H_HUMAN
    ax_c, ay_c, ucx, ucy = int(np.floor(rx)), int(np.floor(ry)), int(np.floor(ux)), int(np.floor(uy))
    blocked = set()
    for k in range(n + 1):
        t = k / n
        cx, cy = int(np.floor(rx + t * (ux - rx))), int(np.floor(ry + t * (uy - ry)))
        z = zu + (1 - t) * (rz - zu)
        if 0 <= cx < 32 and 0 <= cy < 20 and (cx, cy) not in ((ax_c, ay_c), (ucx, ucy)) and z <= h:
            blocked.add((cx, cy))
    return float(np.prod([1 - dens[c] for c in blocked])) if blocked else 1.0


def test_grid_traversal_matches_dense_sampling():
    rng = np.random.default_rng(1)
    dens = rng.uniform(0, 1, (32, 20))
    for _ in range(40):
        rx, ry = rng.uniform(0.3, 31.7), rng.uniform(0.3, 19.7)
        x, y = int(rng.integers(0, 32)), int(rng.integers(0, 20))
        rz = float(rng.choice([2.0, 2.4, 3.0]))
        k = lp._link_keep_jit(rx, ry, rz, x + 0.5, y + 0.5, lp.Z_U, x, y, dens, 32, 20, lp.H_HUMAN, True)
        assert np.isclose(k, _keep_by_sampling(rx, ry, rz, x + 0.5, y + 0.5, dens), atol=1e-9)


def test_greedy_seed_beats_static_layout_under_a_crowd():
    from chsr_sim.greedy_seed import greedy_seed
    routers = [{"x": x, "y": y, "z": 2.4, "phi": 45.0, "alpha": 60.0, "power": 1.0}
               for x, y in ((0.5, 19.5), (16.5, 0.5), (28.5, 12.5), (14.5, 12.5))]
    dens = np.zeros((32, 20))
    dens[8:13, 3:8] = 1.0
    lp._ROUTER_STATIC_CACHE.clear()
    seed = greedy_seed(routers, dens, WALLS)
    assert len(seed) == len(routers)
    assert lp.calculate_sinr(seed, dens, WALLS)[1] >= lp.calculate_sinr(routers, dens, WALLS)[1]
