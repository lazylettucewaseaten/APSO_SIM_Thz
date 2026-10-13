"""Energy-conserving flat-top antenna models (fixes legacy defect D2).

A flat-top pattern radiates gain G_m inside a main-lobe solid angle Omega and
g_s elsewhere.  Conservation of radiated power, (1/4pi) * integral(G dOmega) = 1,
gives

    G_m = (4 pi - g_s (4 pi - Omega)) / Omega.

AP: the main lobe covers the lower half-space over an azimuth sector of width
alpha, i.e. Omega = alpha * integral_{-pi/2}^{0} cos(el) d(el) = alpha [sr].
UE: a pencil beam (circular cone of half-angle psi), Omega = 2 pi (1 - cos psi);
given the UE gain, psi follows from the same identity.
"""
import math


def db2lin(x):
    return 10.0 ** (x / 10.0)


def lin2db(x):
    return 10.0 * math.log10(x)


def ap_main_gain_lin(alpha_deg: float, side_lobe_dbi: float) -> float:
    omega = math.radians(alpha_deg)
    g_s = db2lin(side_lobe_dbi)
    return (4 * math.pi - g_s * (4 * math.pi - omega)) / omega


def ap_main_gain_dbi(alpha_deg: float, side_lobe_dbi: float) -> float:
    return lin2db(ap_main_gain_lin(alpha_deg, side_lobe_dbi))


def ue_main_lobe_halfangle_deg(gain_dbi: float, side_lobe_dbi: float) -> float:
    g_m, g_s = db2lin(gain_dbi), db2lin(side_lobe_dbi)
    omega = 4 * math.pi * (1 - g_s) / (g_m - g_s)
    return math.degrees(math.acos(1 - omega / (2 * math.pi)))
