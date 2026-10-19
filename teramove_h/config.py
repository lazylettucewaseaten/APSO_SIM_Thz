"""Simulation parameters for TeraMove-H.

Every constant used anywhere in the package is defined here, with its source.
Derived quantities (noise power, antenna gains) are computed in code from these
primitives so that the paper can print them from one place.
"""
from dataclasses import dataclass, field, replace
import math

import numpy as np

SPEED_OF_LIGHT = 299_792_458.0  # m/s
THERMAL_NOISE_DBM_HZ = -174.0   # kT at 290 K, dBm/Hz


@dataclass(frozen=True)
class THzParams:
    freq_hz: float = 300e9                 # TeraMove / MILP Table II
    bandwidth_hz: float = 10e9             # contiguous THz channel
    noise_figure_db: float = 10.0
    p_max_dbm: float = 20.0                # TeraMove Table II
    # ITU-R P.676 (ITU-Rpy 0.4.0, 'exact'): 6.68 dB/km at 300 GHz, 23 C,
    # 1013.25 hPa, 10 g/m^3 water vapour.  k = A / (4.343 * 1000 m).
    absorption_db_per_km: float = 6.677
    ap_side_lobe_dbi: float = -10.0
    ue_gain_dbi: float = 20.0
    ue_side_lobe_dbi: float = -10.0
    sinr_th_db: float = 5.0                # TeraMove: QPSK link establishment
    max_spectral_eff: float = 6.0          # b/s/Hz cap (64-QAM)
    human_loss_db: float = 20.0            # MILP/TeraMove L_h per body
    human_loss_cap_db: float = 40.0        # saturation (two bodies)
    self_block_loss_db: float = 30.0       # 3GPP TR 38.901 7.6.4.1
    # 3GPP TR 38.901 Table 7.6.4.1-1, portrait mode (degrees)
    self_block_phi_center: float = 260.0
    self_block_phi_width: float = 120.0
    self_block_theta_center: float = 100.0
    self_block_theta_width: float = 80.0
    # MILP Table II penetration penalties at 300 GHz (dB)
    wall_loss_solid_db: float = 30.0
    wall_loss_wood_db: float = 20.0
    wall_loss_glass_db: float = 15.0

    @property
    def wavelength(self) -> float:
        return SPEED_OF_LIGHT / self.freq_hz

    @property
    def absorption_coeff(self) -> float:
        """k(f) in 1/m such that loss_dB = 4.343 k d."""
        return self.absorption_db_per_km / (10.0 * math.log10(math.e) * 1000.0)

    @property
    def noise_dbm(self) -> float:
        return THERMAL_NOISE_DBM_HZ + 10 * math.log10(self.bandwidth_hz) + self.noise_figure_db

    @property
    def sinr_th_lin(self) -> float:
        return 10 ** (self.sinr_th_db / 10)


@dataclass(frozen=True)
class WiFiParams:
    freq_ghz: float = 6.0                  # 802.11ax in the 6 GHz band
    tx_power_dbm: float = 20.0
    ap_gain_dbi: float = 3.0               # EIRP 23 dBm (< 27 dBm LPI limit at 160 MHz)
    ue_gain_dbi: float = 0.0
    mac_efficiency: float = 0.7
    # 802.11ax, 160 MHz, 2 spatial streams, 0.8 us GI: PHY rate (Mb/s), MCS0..11
    phy_rate_mbps: tuple = (144.1, 288.2, 432.4, 576.5, 864.7, 1152.9,
                            1297.1, 1441.2, 1729.4, 1921.6, 2161.8, 2401.9)
    # Minimum input sensitivity, 20 MHz (dBm), MCS0..11 (802.11-2020 Table 21-25,
    # 802.11ax MCS10/11); +3 dB per bandwidth doubling -> +9 dB at 160 MHz.
    sensitivity_20mhz_dbm: tuple = (-82, -79, -77, -74, -70, -66,
                                    -65, -64, -59, -57, -54, -52)
    bandwidth_offset_db: float = 9.0


@dataclass(frozen=True)
class CrowdParams:
    n_people: int = 120
    n_clusters: int = 6
    cluster_sigma_m: float = 1.0
    background_fraction: float = 0.2
    active_prob: float = 0.5
    body_radius_m: float = 0.2
    body_height_m: float = 1.6             # MILP h_human
    min_separation_m: float = 0.4          # two body radii
    wall_clearance_m: float = 0.25
    ue_height_m: float = 1.0               # MILP/TeraMove z_u
    n_max_per_cell: float = 4.0            # Eq. (12) normalisation
    drift_m: float = 1.5                   # cluster drift per epoch
    jitter_m: float = 0.3                  # individual jitter per epoch
    facing_jitter_deg: float = 30.0


@dataclass(frozen=True)
class OptParams:
    target_satisfaction: float = 0.90      # eta
    r_min_bps: float = 1e9
    swarm: int = 40
    iters: int = 40
    w_start: float = 0.9
    w_end: float = 0.4
    c1: float = 1.5
    c2: float = 1.5
    w_sat: float = 0.6
    w_quality: float = 0.4
    bonus: float = 0.5
    beta_move: float = 0.25                # TeraMove configuration D
    gamma_cluster: float = 0.3
    d_min_m: float = 3.0
    seed_near_fraction: float = 1.0 / 3.0  # Tier 4 seeding (TeraMove)
    seed_near_radius_m: float = 2.0
    rail_step_m: float = 0.25
    rail_speed_mps: float = 0.2            # assumed actuator speed (latency only)
    ga_crossover_prob: float = 0.9
    ga_blx_alpha: float = 0.5
    ga_mutation_sigma: float = 0.1
    yates_tol: float = 1e-9
    yates_max_iter: int = 500
    assoc_rounds: int = 3
    assoc_iters: int = 200                 # PACE: dual (subgradient) iterations
    assoc_every: int = 5                   # PACE: price-guided restart period


CANDIDATE_Z = np.round(np.arange(2.0, 3.0 + 1e-9, 0.2), 1)
CANDIDATE_ALPHA = np.array([30.0, 45.0, 60.0, 75.0, 90.0, 120.0])
CANDIDATE_PHI = np.arange(0.0, 360.0, 45.0)   # compass bearing, 0 = North (+y)


@dataclass(frozen=True)
class Params:
    thz: THzParams = field(default_factory=THzParams)
    wifi: WiFiParams = field(default_factory=WiFiParams)
    crowd: CrowdParams = field(default_factory=CrowdParams)
    opt: OptParams = field(default_factory=OptParams)
    length_m: float = 32.0
    breadth_m: float = 20.0
    height_m: float = 3.0

    def with_(self, **kw) -> "Params":
        """Return a copy with nested fields replaced, e.g. with_(opt={'r_min_bps': 2e9})."""
        out = self
        for key, val in kw.items():
            if isinstance(val, dict):
                out = replace(out, **{key: replace(getattr(out, key), **val)})
            else:
                out = replace(out, **{key: val})
        return out


DEFAULT = Params()
