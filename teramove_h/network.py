"""Network state: THz AP configuration, scenario, and per-pair THz SINR/capacity."""
from dataclasses import dataclass

import numpy as np

from .antenna import ap_main_gain_lin, db2lin, ue_main_lobe_halfangle_deg
from .channel import LinkCache, wifi_rates
from .config import CANDIDATE_ALPHA, Params
from .crowd import Crowd, density_map
from .geometry import MILP_ALPHA_DEG, MILP_LAYOUT, WALLS, WIFI_POSITIONS, cell_centres, room_of

AP_GAIN_TABLE = {}


def ap_gain_lookup(alpha, side_lobe_dbi):
    key = (float(alpha), float(side_lobe_dbi))
    if key not in AP_GAIN_TABLE:
        AP_GAIN_TABLE[key] = ap_main_gain_lin(alpha, side_lobe_dbi)
    return AP_GAIN_TABLE[key]


@dataclass
class APConfig:
    """THz AP state. Azimuth phi is a compass bearing (deg); power p in watts."""
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    phi: np.ndarray
    alpha: np.ndarray
    p: np.ndarray
    room: np.ndarray

    @property
    def n(self):
        return len(self.x)

    def copy(self):
        return APConfig(*(a.copy() for a in (self.x, self.y, self.z, self.phi, self.alpha,
                                             self.p, self.room)))

    def xyz(self):
        return np.column_stack([self.x, self.y, self.z])


def milp_config(params: Params) -> APConfig:
    """Initial deployment of MILP.pdf Fig. 1 with all APs at P_max."""
    lay = MILP_LAYOUT
    n = len(lay)
    p_max_w = 10 ** (params.thz.p_max_dbm / 10) / 1000.0
    rooms = np.array([room_of(x, y) for x, y in lay[:, :2]])
    return APConfig(lay[:, 0].copy(), lay[:, 1].copy(), lay[:, 2].copy(), lay[:, 3].copy(),
                    np.full(n, MILP_ALPHA_DEG), np.full(n, p_max_w), rooms)


class Scenario:
    """One crowd snapshot seen by the network.

    ``truth`` is the real crowd (used for evaluation); ``context`` is what the
    optimiser believes (equal to ``truth`` unless sensing error is injected).
    """

    def __init__(self, params: Params, truth: Crowd, context: Crowd = None, wifi=True):
        self.p = params
        self.truth = truth
        self.context = context if context is not None else truth
        self.wifi_xyz = WIFI_POSITIONS if wifi else np.zeros((0, 3))
        self.true_view = _View(params, truth, self.wifi_xyz)
        self.ctx_view = self.true_view if self.context is truth else _View(params, self.context, self.wifi_xyz)

    @property
    def n_users(self):
        return self.true_view.k


class _View:
    """Link tables for one crowd realisation (users + virtual grid receivers)."""

    def __init__(self, params: Params, crowd: Crowd, wifi_xyz):
        self.p = params
        self.crowd = crowd
        uidx = crowd.user_idx
        self.user_idx = uidx
        self.k = len(uidx)
        z_u = params.crowd.ue_height_m
        self.rx = np.column_stack([crowd.xy[uidx], np.full(self.k, z_u)])
        self.users = LinkCache(params, self.rx, uidx, crowd.facing[uidx], crowd.xy, WALLS)
        if len(wifi_xyz):
            self.wifi_rate, self.wifi_rx_dbm = wifi_rates(params, wifi_xyz, self.rx, uidx, crowd.xy, WALLS)
        else:
            self.wifi_rate = np.zeros((self.k, 0))
            self.wifi_rx_dbm = np.zeros((self.k, 0))
        self._grid = None
        self.density = density_map(crowd, params.crowd)

    @property
    def grid(self):
        if self._grid is None:
            cc = cell_centres(int(self.p.length_m), int(self.p.breadth_m))
            rx = np.column_stack([cc, np.full(len(cc), self.p.crowd.ue_height_m)])
            self._grid = LinkCache(self.p, rx, np.full(len(cc), -1), np.zeros(len(cc)),
                                   self.crowd.xy, WALLS, self_block=False, max_entries=4000)
        return self._grid


class THzTerms:
    """Configuration-dependent link terms for a set of receivers.

    L[a, u]  path gain, Gt[a, u] AP gain, Gr[u, a, b] UE gain towards AP b when
    the UE beam points at AP a.
    """

    def __init__(self, params: Params, cfg: APConfig, cache: LinkCache):
        t = params.thz
        n, k = cfg.n, len(cache.rx)
        L = np.empty((n, k))
        brg = np.empty((n, k))
        for a in range(n):
            entry = cache.get(cfg.x[a], cfg.y[a], cfg.z[a])
            L[a], brg[a] = entry[0], entry[1]
        g_side = db2lin(t.ap_side_lobe_dbi)
        g_main = np.array([ap_gain_lookup(al, t.ap_side_lobe_dbi) for al in cfg.alpha])
        dev = np.abs((brg - cfg.phi[:, None] + 180.0) % 360.0 - 180.0)
        Gt = np.where(dev <= cfg.alpha[:, None] / 2.0, g_main[:, None], g_side)
        # UE pencil beam
        vec = cfg.xyz()[None, :, :] - cache.rx[:, None, :]          # (k, n, 3)
        vec /= np.linalg.norm(vec, axis=2, keepdims=True)
        cos = np.einsum("uad,ubd->uab", vec, vec)                    # (k, n, n)
        cos_psi = np.cos(np.radians(ue_main_lobe_halfangle_deg(t.ue_gain_dbi, t.ue_side_lobe_dbi)))
        self.Gr = np.where(cos >= cos_psi, db2lin(t.ue_gain_dbi), db2lin(t.ue_side_lobe_dbi))
        self.L, self.Gt = L, Gt
        self.noise_w = 10 ** (t.noise_dbm / 10) / 1000.0
        self.g_ue = db2lin(t.ue_gain_dbi)

    def sinr(self, p):
        """SINR[u, a] when user u is served by AP a; APs with p = 0 are silent."""
        h = (p[:, None] * self.Gt * self.L).T              # (k, n) power from b at u, before UE gain
        signal = h * self.g_ue
        rx_all = self.Gr * h[:, None, :]                    # (k, a, b)
        interf = rx_all.sum(axis=2) - signal                # remove b == a term (Gr[u,a,a] = g_ue)
        interf = np.maximum(interf, 0.0)
        return signal / (self.noise_w + interf)


def thz_capacity(params: Params, sinr):
    t = params.thz
    se = np.minimum(np.log2(1.0 + sinr), t.max_spectral_eff)
    return np.where(sinr >= t.sinr_th_lin, t.bandwidth_hz * se, 0.0)


def grid_coverage(params: Params, cfg: APConfig, view: _View):
    """Legacy coverage metric on the 1 m grid (THz only).

    Each virtual receiver points its beam at the AP with the strongest received
    signal; returns (sinr map (L x B) in dB, cell ratio, density-weighted ratio).
    """
    terms = THzTerms(params, cfg, view.grid)
    sinr = terms.sinr(cfg.p)
    h = (cfg.p[:, None] * terms.Gt * terms.L).T
    best = np.argmax(h, axis=1)
    s = sinr[np.arange(len(best)), best]
    s_db = 10 * np.log10(np.maximum(s, 1e-30))
    cov = s_db >= params.thz.sinr_th_db
    shape = (int(params.length_m), int(params.breadth_m))
    dens = view.density.ravel()
    dens_ratio = dens[cov].sum() / dens.sum() if dens.sum() > 0 else cov.mean()
    return s_db.reshape(shape), cov.mean(), dens_ratio


__all__ = ["APConfig", "Scenario", "THzTerms", "thz_capacity", "grid_coverage", "milp_config",
           "CANDIDATE_ALPHA"]
