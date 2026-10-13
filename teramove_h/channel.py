"""Geometric link computation (numba) and THz / Wi-Fi path gains.

For one transmitter position and K receive points the kernel returns the 3-D
distance, the compass bearing transmitter->receiver, the THz static penetration
loss (walls + cubicles crossed below their height), the number of full-height
walls crossed, and the number of human bodies intersected.

Human bodies are vertical cylinders (radius r, height h).  The 2-D projection of
the ray is intersected with the disc exactly; inside the chord the ray height is
monotone, so the body blocks iff the lowest ray point inside the chord is at or
below h (fixes legacy defect D6).  The receiver's own body is excluded (it is
handled by the 3GPP self-blocking model).
"""
import math
from collections import OrderedDict

import numpy as np
from numba import njit

from .config import SPEED_OF_LIGHT, Params, THzParams

FULL_HEIGHT = 3.0 - 1e-9


@njit(cache=True)
def _link_geometry(tx, rx, rx_person, people, body_r, body_h, walls, wall_loss):
    k = rx.shape[0]
    dist = np.empty(k)
    bearing = np.empty(k)
    static_db = np.zeros(k)
    n_full = np.zeros(k, dtype=np.int64)
    n_body = np.zeros(k, dtype=np.int64)
    tx_x, tx_y, tx_z = tx[0], tx[1], tx[2]
    r2 = body_r * body_r
    for i in range(k):
        ux, uy, uz = rx[i, 0], rx[i, 1], rx[i, 2]
        dx, dy, dz = ux - tx_x, uy - tx_y, uz - tx_z
        dist[i] = max(math.sqrt(dx * dx + dy * dy + dz * dz), 1e-3)
        bearing[i] = math.degrees(math.atan2(dx, dy)) % 360.0
        # walls (axis-aligned vertical planes)
        for w in range(walls.shape[0]):
            o, p, s, e, h = walls[w, 0], walls[w, 1], walls[w, 2], walls[w, 3], walls[w, 4]
            if o == 0.0:  # horizontal wall y = p
                lo, hi = min(tx_y, uy), max(tx_y, uy)
                if lo < p < hi:
                    t = (p - tx_y) / dy
                    xi = tx_x + t * dx
                    if s <= xi <= e and tx_z + t * dz <= h:
                        static_db[i] += wall_loss[int(walls[w, 5])]
                        if h >= FULL_HEIGHT:
                            n_full[i] += 1
            else:         # vertical wall x = p
                lo, hi = min(tx_x, ux), max(tx_x, ux)
                if lo < p < hi:
                    t = (p - tx_x) / dx
                    yi = tx_y + t * dy
                    if s <= yi <= e and tx_z + t * dz <= h:
                        static_db[i] += wall_loss[int(walls[w, 5])]
                        if h >= FULL_HEIGHT:
                            n_full[i] += 1
        # human bodies
        a = dx * dx + dy * dy
        if a < 1e-12:
            continue
        for j in range(people.shape[0]):
            if j == rx_person[i]:
                continue
            cx, cy = people[j, 0] - tx_x, people[j, 1] - tx_y
            # receiver inside this disc (virtual grid receivers): treat as own body
            ex, ey = ux - people[j, 0], uy - people[j, 1]
            if ex * ex + ey * ey < r2:
                continue
            b = -2.0 * (dx * cx + dy * cy)
            c = cx * cx + cy * cy - r2
            disc = b * b - 4.0 * a * c
            if disc <= 0.0:
                continue
            sq = math.sqrt(disc)
            t1 = (-b - sq) / (2.0 * a)
            t2 = (-b + sq) / (2.0 * a)
            if t1 < 0.0:
                t1 = 0.0
            if t2 > 1.0:
                t2 = 1.0
            if t1 >= t2:
                continue
            z_low = min(tx_z + t1 * dz, tx_z + t2 * dz)
            if z_low <= body_h:
                n_body[i] += 1
    return dist, bearing, static_db, n_full, n_body


def thz_wall_losses(t: THzParams):
    return np.array([t.wall_loss_solid_db, t.wall_loss_wood_db, t.wall_loss_glass_db])


def fspl_db(d, freq_hz):
    return 20.0 * np.log10(4.0 * np.pi * freq_hz * d / SPEED_OF_LIGHT)


def self_block_mask(ap_xyz, rx_xyz, facing_math_deg, t: THzParams):
    """3GPP TR 38.901 7.6.4.1 self-blocking region (portrait), per receiver.

    Azimuth of the AP seen from the UE, relative to the UE orientation, and the
    zenith angle (0 = straight up) are tested against the blocked region.  The
    UE orientation is uniform, so the region's absolute rotation is immaterial.
    """
    d = ap_xyz[None, :] - rx_xyz
    az = (np.degrees(np.arctan2(d[:, 1], d[:, 0])) - facing_math_deg) % 360.0
    zen = np.degrees(np.arctan2(np.hypot(d[:, 0], d[:, 1]), d[:, 2]))
    in_az = np.abs((az - t.self_block_phi_center + 180.0) % 360.0 - 180.0) <= t.self_block_phi_width / 2
    in_zen = np.abs(zen - t.self_block_theta_center) <= t.self_block_theta_width / 2
    return in_az & in_zen


class LinkCache:
    """Per-crowd cache of static THz link data keyed by AP position (bounded LRU)."""

    def __init__(self, params: Params, rx_xyz, rx_person, rx_facing, people_xy,
                 walls, self_block=True, max_entries=20000):
        self.p = params
        self.rx = np.ascontiguousarray(rx_xyz, dtype=float)
        self.rx_person = np.ascontiguousarray(rx_person, dtype=np.int64)
        self.facing = rx_facing
        self.people = np.ascontiguousarray(people_xy, dtype=float)
        self.walls = walls
        self.self_block = self_block
        self.wall_loss = thz_wall_losses(params.thz)
        self.max_entries = max_entries
        self._cache = OrderedDict()

    def get(self, x, y, z):
        key = (round(float(x), 4), round(float(y), 4), round(float(z), 4))
        hit = self._cache.get(key)
        if hit is not None:
            self._cache.move_to_end(key)
            return hit
        t, c = self.p.thz, self.p.crowd
        tx = np.array([x, y, z], dtype=float)
        dist, bearing, static_db, n_full, n_body = _link_geometry(
            tx, self.rx, self.rx_person, self.people, c.body_radius_m, c.body_height_m,
            self.walls, self.wall_loss)
        loss = (fspl_db(dist, t.freq_hz) + 10 * np.log10(np.e) * t.absorption_coeff * dist
                + static_db + np.minimum(n_body * t.human_loss_db, t.human_loss_cap_db))
        if self.self_block:
            loss = loss + t.self_block_loss_db * self_block_mask(tx, self.rx, self.facing, t)
        entry = (10.0 ** (-loss / 10.0), bearing, dist, n_full, n_body)
        self._cache[key] = entry
        if len(self._cache) > self.max_entries:
            self._cache.popitem(last=False)
        return entry


def wifi_rates(params: Params, ap_xyz, rx_xyz, rx_person, people_xy, walls):
    """Effective 802.11ax rate (b/s) for every (receiver, Wi-Fi AP) pair.

    Path loss: 3GPP TR 38.901 InH-Office.  The link is LOS when the ray crosses
    no full-height wall and no human body; otherwise
    PL_NLOS = max(PL_LOS, 17.30 + 38.3 log10 d + 24.9 log10 fc).
    """
    w, c = params.wifi, params.crowd
    rates = np.zeros((len(rx_xyz), len(ap_xyz)))
    rx_dbm_all = np.zeros_like(rates)
    sens = np.array(w.sensitivity_20mhz_dbm, dtype=float) + w.bandwidth_offset_db
    phy = np.array(w.phy_rate_mbps) * 1e6
    zero_loss = np.zeros(3)
    for a, ap in enumerate(ap_xyz):
        dist, _, _, n_full, n_body = _link_geometry(
            np.asarray(ap, dtype=float), np.ascontiguousarray(rx_xyz, dtype=float),
            np.ascontiguousarray(rx_person, dtype=np.int64), np.ascontiguousarray(people_xy, dtype=float),
            c.body_radius_m, c.body_height_m, walls, zero_loss)
        pl_los = 32.4 + 17.3 * np.log10(dist) + 20.0 * np.log10(w.freq_ghz)
        pl_nlos = np.maximum(pl_los, 17.30 + 38.3 * np.log10(dist) + 24.9 * np.log10(w.freq_ghz))
        los = (n_full == 0) & (n_body == 0)
        pl = np.where(los, pl_los, pl_nlos)
        prx = w.tx_power_dbm + w.ap_gain_dbi + w.ue_gain_dbi - pl
        rx_dbm_all[:, a] = prx
        mcs = np.searchsorted(sens, prx, side="right") - 1   # highest MCS with prx >= sens
        rates[:, a] = np.where(mcs >= 0, w.mac_efficiency * phy[np.clip(mcs, 0, None)], 0.0)
    return rates, rx_dbm_all
