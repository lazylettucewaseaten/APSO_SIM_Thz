"""Physics and geometry tests."""
import math

import numpy as np
import pytest

from teramove_h.antenna import (ap_main_gain_dbi, ap_main_gain_lin, db2lin,
                                ue_main_lobe_halfangle_deg)
from teramove_h.channel import _link_geometry, fspl_db, self_block_mask, thz_wall_losses, wifi_rates
from teramove_h.config import CANDIDATE_ALPHA, DEFAULT as P
from teramove_h.geometry import (MILP_LAYOUT, ROOMS, WALLS, WIFI_POSITIONS, bearing_deg,
                                 compass_to_math, math_to_compass, room_of)


def _sphere_integral(gain_fn, n=720):
    """Integrate a gain pattern over the sphere (midpoint rule, 0.25 deg grid aligned
    with the sector edges so the main lobe is resolved exactly in azimuth)."""
    th = (np.arange(n) + 0.5) * np.pi / n            # polar angle from +z
    ph = (np.arange(2 * n) + 0.5) * np.pi / n         # azimuth
    T, PH = np.meshgrid(th, ph, indexing="ij")
    g = gain_fn(T, PH)
    return np.sum(g * np.sin(T)) * (np.pi / n) * (np.pi / n)


@pytest.mark.parametrize("alpha", CANDIDATE_ALPHA)
def test_ap_pattern_conserves_energy(alpha):
    gm = ap_main_gain_lin(alpha, P.thz.ap_side_lobe_dbi)
    gs = db2lin(P.thz.ap_side_lobe_dbi)
    a = math.radians(alpha)

    def g(T, PH):
        lower = T > np.pi / 2
        in_sector = np.abs((PH - np.pi + np.pi) % (2 * np.pi) - np.pi) <= a / 2
        return np.where(lower & in_sector, gm, gs)
    assert _sphere_integral(g) == pytest.approx(4 * np.pi, rel=2e-3)


def test_ap_gain_decreases_with_width():
    gains = [ap_main_gain_dbi(a, -10) for a in CANDIDATE_ALPHA]
    assert all(g1 > g2 for g1, g2 in zip(gains, gains[1:]))
    assert ap_main_gain_dbi(60, -10) == pytest.approx(10.374, abs=1e-3)


def test_ue_pattern_conserves_energy():
    psi = math.radians(ue_main_lobe_halfangle_deg(20.0, -10.0))
    gm, gs = db2lin(20.0), db2lin(-10.0)
    # Axially symmetric pattern: 1-D integral over the polar angle, fine grid.
    th = (np.arange(2_000_000) + 0.5) * np.pi / 2_000_000
    total = np.sum(np.where(th <= psi, gm, gs) * 2 * np.pi * np.sin(th)) * np.pi / 2_000_000
    assert total == pytest.approx(4 * np.pi, rel=1e-5)


def test_noise_and_absorption():
    assert P.thz.noise_dbm == pytest.approx(-64.0, abs=1e-9)   # -174 + 10log10(1e10) + 10
    assert 4.343 * P.thz.absorption_coeff * 1000 == pytest.approx(6.677, rel=1e-3)
    assert fspl_db(np.array([1.0]), 300e9)[0] == pytest.approx(81.990, abs=1e-3)  # 20log10(4 pi f / c)


def test_compass_convention():
    assert bearing_deg(0, 1) == pytest.approx(0.0)
    assert bearing_deg(1, 0) == pytest.approx(90.0)
    assert bearing_deg(0, -1) == pytest.approx(180.0)
    assert bearing_deg(-1, 0) == pytest.approx(270.0)
    assert compass_to_math(0) == pytest.approx(90.0)
    assert math_to_compass(compass_to_math(135.0)) == pytest.approx(135.0)


def test_milp_layout_points_into_building():
    """Every Fig. 1 AP's boresight, 1 m ahead, stays inside the floor plan."""
    for x, y, _, b in MILP_LAYOUT:
        dx, dy = math.sin(math.radians(b)), math.cos(math.radians(b))
        assert 0 < x + dx < 32 and 0 < y + dy < 20, (x, y, b)


def test_rooms_partition_floor():
    area = np.sum((ROOMS[:, 1] - ROOMS[:, 0]) * (ROOMS[:, 3] - ROOMS[:, 2]))
    assert area == pytest.approx(32 * 20)
    for x, y, _, _ in MILP_LAYOUT:
        room_of(x, y)
    for x, y, _ in WIFI_POSITIONS:
        room_of(x, y)


def _geom(tx, rx, people=np.zeros((0, 2)), rx_person=None):
    rx = np.atleast_2d(np.asarray(rx, float))
    rp = np.full(len(rx), -1, dtype=np.int64) if rx_person is None else np.asarray(rx_person, np.int64)
    return _link_geometry(np.asarray(tx, float), rx, rp, np.asarray(people, float), 0.2, 1.6,
                          WALLS, thz_wall_losses(P.thz))


def test_wall_crossing():
    # From the bottom-left large room through the solid wall x = 16 into the right one.
    d, b, loss, n_full, _ = _geom([10.5, 5.5, 2.4], [20.5, 5.5, 1.0])
    assert n_full[0] == 1 and loss[0] == pytest.approx(30.0)
    # Same room: nothing crossed (cubicles are 1 m high, ray stays above them).
    d, b, loss, n_full, _ = _geom([3.5, 0.5, 2.2], [9.5, 5.5, 1.0])
    assert loss[0] == 0.0 and n_full[0] == 0


def test_body_blockage_matches_dense_sampling():
    rng = np.random.default_rng(0)
    tx = np.array([5.5, 5.5, 2.6])
    for _ in range(300):
        person = rng.uniform([3, 3], [12, 9], size=(1, 2))
        rx = np.array([rng.uniform(3, 12), rng.uniform(3, 9), 1.0])
        if np.hypot(*(rx[:2] - person[0])) < 0.2:
            continue
        _, _, _, _, nb = _geom(tx, rx, person)
        t = np.linspace(0, 1, 200001)
        pts = tx[None, :] + t[:, None] * (rx - tx)[None, :]
        inside = np.hypot(pts[:, 0] - person[0, 0], pts[:, 1] - person[0, 1]) <= 0.2
        brute = bool(np.any(inside & (pts[:, 2] <= 1.6)))
        assert bool(nb[0]) == brute


def test_own_body_and_overhead_ray():
    people = np.array([[8.0, 5.0], [6.0, 5.0]])
    # Receiver is person 0; person 0 must not block its own link.
    _, _, _, _, nb = _geom([8.0, 1.0, 3.0], [8.0, 5.0, 1.0], people, [0])
    assert nb[0] == 0
    # Body right under a 3 m AP: the ray there is far above 1.6 m.
    _, _, _, _, nb = _geom([6.0, 5.05, 3.0], [12.0, 5.0, 1.0], people[1:], [-1])
    assert nb[0] == 0


def test_self_blocking_region():
    t = P.thz
    rx = np.array([[10.0, 10.0, 1.0]])
    # AP at relative azimuth 260 deg (user facing 0 deg math), zenith ~ 80 deg -> blocked.
    az = math.radians(260.0)
    ap = np.array([10 + 8 * math.cos(az), 10 + 8 * math.sin(az), 2.4])
    assert self_block_mask(ap, rx, np.array([0.0]), t)[0]
    # Same direction but the user turned around -> not blocked.
    assert not self_block_mask(ap, rx, np.array([180.0]), t)[0]
    # AP almost overhead (zenith < 60 deg) -> not blocked.
    ap2 = np.array([10 + 0.5 * math.cos(az), 10 + 0.5 * math.sin(az), 2.4])
    assert not self_block_mask(ap2, rx, np.array([0.0]), t)[0]


def test_wifi_rates_monotone_and_bounded():
    rx = np.array([[9.5, 3.0, 1.0], [9.5, 8.5, 1.0], [25.0, 5.0, 1.0]])
    rates, prx = wifi_rates(P, WIFI_POSITIONS[:1], rx, np.full(3, -1), np.zeros((0, 2)), WALLS)
    assert rates.max() <= 0.7 * 2401.9e6 + 1
    assert prx[0, 0] > prx[2, 0]                 # farther + wall -> weaker
    assert rates[0, 0] >= rates[2, 0]
