import hashlib

import numpy as np
from numba import njit
from .config import *

@njit
def dbm_to_mw(dbm):
    return 10**(dbm / 10.0)

@njit
def mw_to_dbm(mw):
    return 10 * np.log10(mw + 1e-12)

@njit
def _wall_loss_jit(p1x, p1y, p1z, p2x, p2y, p2z, walls_arr):
    loss = 0.0
    mx = min(p1x, p2x)
    Mx = max(p1x, p2x)
    my = min(p1y, p2y)
    My = max(p1y, p2y)
    
    for i in range(len(walls_arr)):
        o = walls_arr[i, 0]
        ml = walls_arr[i, 1]
        p = walls_arr[i, 2]
        s = walls_arr[i, 3]
        e = walls_arr[i, 4]
        h = walls_arr[i, 5]
        
        if o == 0.0: # 'h'
            if my < p and p < My:
                if p2y != p1y:
                    t = (p - p1y) / (p2y - p1y)
                    xi = p1x + t * (p2x - p1x)
                    if s <= xi and xi <= e:
                        zi = p1z + t * (p2z - p1z)
                        if zi <= h:
                            loss += ml
        elif o == 1.0: # 'v'
            if mx < p and p < Mx:
                if p2x != p1x:
                    t = (p - p1x) / (p2x - p1x)
                    yi = p1y + t * (p2y - p1y)
                    if s <= yi and yi <= e:
                        zi = p1z + t * (p2z - p1z)
                        if zi <= h:
                            loss += ml
    return loss

@njit
def _link_keep_jit(rx, ry, rz, ux, uy, z_u, ucx, ucy, human_density, length, breadth, h_human,
                   ray_from_user):
    """Probability that no body blocks the link: prod over crossed cells of (1 - D_h(c)).

    The cells crossed by the 2-D segment AP -> user are visited exactly once (grid
    traversal).  The AP's and the user's own cells are excluded.  A cell counts if the
    ray is at or below h_human anywhere inside it; z is linear along the link, so its
    lowest value in a cell is at the entry or the exit point."""
    dx = ux - rx
    dy = uy - ry
    cx = int(np.floor(rx))
    cy = int(np.floor(ry))
    ax_c = cx
    ay_c = cy
    step_x = 1 if dx > 0 else -1
    step_y = 1 if dy > 0 else -1
    if dx != 0.0:
        t_max_x = ((cx + (1 if dx > 0 else 0)) - rx) / dx
        t_dx = abs(1.0 / dx)
    else:
        t_max_x = np.inf
        t_dx = np.inf
    if dy != 0.0:
        t_max_y = ((cy + (1 if dy > 0 else 0)) - ry) / dy
        t_dy = abs(1.0 / dy)
    else:
        t_max_y = np.inf
        t_dy = np.inf
    keep = 1.0
    t_in = 0.0
    while True:
        t_out = min(t_max_x, t_max_y, 1.0)
        if ray_from_user:              # t = 0 at the AP, 1 at the user
            z_lo = z_u + (1.0 - max(t_in, t_out)) * (rz - z_u)
        else:
            z_lo = z_u + min(t_in, t_out) * (rz - z_u)
        inside = 0 <= cx and cx < length and 0 <= cy and cy < breadth
        own = (cx == ax_c and cy == ay_c) or (cx == ucx and cy == ucy)
        if inside and (not own) and z_lo <= h_human and t_out > t_in:
            keep *= 1.0 - human_density[cx, cy]
        if t_out >= 1.0:
            break
        t_in = t_out
        if t_max_x < t_max_y:
            cx += step_x
            t_max_x += t_dx
        elif t_max_y < t_max_x:
            cy += step_y
            t_max_y += t_dy
        else:                          # exactly through a grid corner
            cx += step_x
            cy += step_y
            t_max_x += t_dx
            t_max_y += t_dy
    return keep

@njit
def _compute_single_router_static_data(rx, ry, rz, human_density, walls_arr,
                                       length, breadth, z_u, f_hz, c, k_f, h_human, human_penalty, ptx_dbm,
                                       compass, saturating, cell_centres, ray_from_user):
    base_power = np.zeros((length, breadth))
    angles = np.zeros((length, breadth))
    off = 0.5 if cell_centres else 0.0
    ax_c = int(np.floor(rx))
    ay_c = int(np.floor(ry))
    
    for x in range(length):
        for y in range(breadth):
            ux = x + off
            uy = y + off
            d_2d = np.sqrt((ux - rx)**2 + (uy - ry)**2)
            d_3d = np.sqrt(d_2d**2 + (rz - z_u)**2)
            if d_3d == 0.0: 
                d_3d = 1e-3
            
            fspl = 20.0 * np.log10(4.0 * np.pi * f_hz * d_3d / c)
            abs_loss = 4.343 * k_f * d_3d
            
            if d_2d == 0.0:
                angle_to_user = -1.0   # user directly below the AP: inside the main lobe
            else:
                if compass:   # bearing from North (+y), clockwise
                    angle_to_user = np.degrees(np.arctan2(ux - rx, uy - ry))
                else:         # legacy: math angle from +x, counter-clockwise
                    angle_to_user = np.degrees(np.arctan2(uy - ry, ux - rx))
                if angle_to_user < 0.0:
                    angle_to_user += 360.0
            
            angles[x, y] = angle_to_user
            
            blockage_penalty = 0.0
            if d_2d > 0.0 and saturating:
                blockage_penalty = human_penalty * (1.0 - _link_keep_jit(
                    rx, ry, rz, ux, uy, z_u, x, y, human_density, length, breadth, h_human,
                    ray_from_user))
            elif d_2d > 0.0:
                # earlier model: unbounded sum over cells sampled at 1 m steps
                steps = int(d_2d)
                if steps > 0:
                    for step in range(1, steps):
                        px = int(rx + step * (ux - rx) / steps)
                        py = int(ry + step * (uy - ry) / steps)
                        if 0 <= px and px < length and 0 <= py and py < breadth:
                            d2d_c = np.sqrt((px - rx)**2 + (py - ry)**2)
                            if ray_from_user:
                                d2d_c = d_2d - d2d_c
                            z_c = z_u + (d2d_c / d_2d) * (rz - z_u)
                            if z_c <= h_human:
                                blockage_penalty += human_density[px, py] * human_penalty
            
            static_loss = _wall_loss_jit(rx, ry, rz, ux, uy, z_u, walls_arr)
            base_power[x, y] = ptx_dbm - fspl - abs_loss - blockage_penalty - static_loss
            
    return base_power, angles

@njit
def _apply_router_gain_jit(powers_i, base_power, angles, rphi, ralpha, rpower, g_main):
    length, breadth = base_power.shape
    for x in range(length):
        for y in range(breadth):
            ang_dev = abs((angles[x, y] - rphi + 180.0) % 360.0 - 180.0)
            if angles[x, y] < 0.0 or ang_dev <= ralpha / 2.0:
                gain = g_main
            else:
                gain = -100.0
            p_rx = base_power[x, y] + gain
            powers_i[x, y] = 10**(p_rx / 10.0) * rpower


def main_lobe_gain(alpha):
    """Main-lobe gain (dBi) for azimuth beamwidth alpha (deg); elevation width fixed."""
    if GAIN_COUPLED:
        return G_REF + 10.0 * np.log10(ALPHA_REF / float(alpha))
    return float(G_MAX)

@njit
def _compute_sinr_map_jit(powers, human_density, length, breadth, noise_dbm, sinr_th, serving):
    """serving[x, y] = index of the serving AP, or -1 for the strongest AP (best server)."""
    sinr_map = np.zeros((length, breadth))
    used = np.zeros((length, breadth), dtype=np.int64)
    noise_mw = 10**(noise_dbm / 10.0)
    
    covered_cells = 0
    density_sum = 0.0
    total_density = 0.0
    num_routers = powers.shape[0]
    
    for x in range(length):
        for y in range(breadth):
            total_density += human_density[x, y]
            
            max_sig = -1.0
            best = 0
            total_sig = 0.0
            
            for i in range(num_routers):
                sig = powers[i, x, y]
                total_sig += sig
                if sig > max_sig:
                    max_sig = sig
                    best = i
            
            if serving[x, y] >= 0:
                best = serving[x, y]
            used[x, y] = best
            signal = powers[best, x, y]
            interference = total_sig - signal
            sinr_mw = signal / (noise_mw + interference + 1e-12)
            sinr_db = 10.0 * np.log10(sinr_mw + 1e-12)
            sinr_map[x, y] = sinr_db
            
            if sinr_db >= sinr_th:
                covered_cells += 1
                density_sum += human_density[x, y]
                
    if total_density > 0.0:
        coverage = density_sum / total_density
    else:
        coverage = covered_cells / (length * breadth)
        
    return sinr_map, coverage, used

_WALLS_CACHE_ID = None
_WALLS_ARR_CACHE = None
_HUMAN_DENSITY_CACHE_ID = None
_ROUTER_STATIC_CACHE = {}
_CACHE_MAX = 20000   # ~10 kB per entry -> at most ~200 MB

def calculate_sinr(routers, human_density, walls, serving=None, return_serving=False):
    """SINR map and density-weighted coverage.

    serving: optional (LENGTH, BREADTH) int array of fixed serving-AP indices (design-time
    association, no re-association).  None means every cell uses its strongest AP.
    return_serving: also return the serving-AP index map that was used.
    """
    global _WALLS_CACHE_ID, _WALLS_ARR_CACHE
    global _HUMAN_DENSITY_CACHE_ID, _ROUTER_STATIC_CACHE
    
    # Caches are keyed by *content*.  (Keying by id() was unsafe: CPython reuses the
    # address of a freed array, so a new crowd map could inherit stale path losses.)
    walls_key = tuple((w['o'], w['p'], w['s'], w['e'], w['m'], w['h']) for w in walls)
    density_key = hashlib.blake2b(np.ascontiguousarray(human_density, dtype=float).tobytes(),
                                  digest_size=16).digest()

    # 1. Convert walls to cache if changed
    if walls_key != _WALLS_CACHE_ID:
        walls_arr = np.zeros((len(walls), 6))
        for i, w in enumerate(walls):
            walls_arr[i, 0] = 0.0 if w['o'] == 'h' else 1.0
            walls_arr[i, 1] = 30.0 if w['m'] == 'solid' else (20.0 if w['m'] == 'wood' else 15.0)
            walls_arr[i, 2] = float(w['p'])
            walls_arr[i, 3] = float(w['s'])
            walls_arr[i, 4] = float(w['e'])
            walls_arr[i, 5] = float(w['h'])
        _WALLS_ARR_CACHE = walls_arr
        _WALLS_CACHE_ID = walls_key
    else:
        walls_arr = _WALLS_ARR_CACHE
        
    # 2. Reset router data cache if new time step (human density changed)
    if density_key != _HUMAN_DENSITY_CACHE_ID:
        _ROUTER_STATIC_CACHE.clear()
        _HUMAN_DENSITY_CACHE_ID = density_key
        
    length = int(LENGTH)
    breadth = int(BREADTH)
    powers = np.zeros((len(routers), length, breadth))
    
    for i, r in enumerate(routers):
        rx, ry, rz = float(r['x']), float(r['y']), float(r['z'])
        rphi, ralpha = float(r['phi']), float(r['alpha'])
        rpower = float(r.get('power', ROUTER_POWER))
        
        cache_key = (rx, ry, rz, bool(AZIMUTH_COMPASS), float(K_F), bool(BLOCKAGE_SATURATING),
                     bool(CELL_CENTRES), bool(RAY_FROM_USER))
        if cache_key not in _ROUTER_STATIC_CACHE:
            if len(_ROUTER_STATIC_CACHE) >= _CACHE_MAX:   # bound memory (continuous Tier-4 positions)
                _ROUTER_STATIC_CACHE.clear()
            base_power, angles = _compute_single_router_static_data(
                rx, ry, rz, human_density, walls_arr,
                length, breadth, float(Z_U), float(F_HZ), float(C),
                float(K_F), float(H_HUMAN), float(HUMAN_PENALTY_DB), float(PTX_DBM),
                bool(AZIMUTH_COMPASS), bool(BLOCKAGE_SATURATING), bool(CELL_CENTRES), bool(RAY_FROM_USER)
            )
            _ROUTER_STATIC_CACHE[cache_key] = (base_power, angles)
            
        base_power, angles = _ROUTER_STATIC_CACHE[cache_key]
        
        _apply_router_gain_jit(powers[i], base_power, angles, rphi, ralpha, rpower,
                               float(main_lobe_gain(ralpha) + G_RX))
        
    if serving is None:
        serving = np.full((length, breadth), -1, dtype=np.int64)
    else:
        serving = np.ascontiguousarray(serving, dtype=np.int64)
    sinr_map, coverage, used = _compute_sinr_map_jit(powers, human_density, length, breadth,
                                                     float(NOISE_DBM), float(SINR_TH), serving)
    if return_serving:
        return sinr_map, coverage, used
    return sinr_map, coverage

def wall_loss(p1, p2, ws):
    walls_arr = np.zeros((len(ws), 6))
    for i, w in enumerate(ws):
        walls_arr[i, 0] = 0.0 if w['o'] == 'h' else 1.0
        walls_arr[i, 1] = 30.0 if w['m'] == 'solid' else (20.0 if w['m'] == 'wood' else 15.0)
        walls_arr[i, 2] = float(w['p'])
        walls_arr[i, 3] = float(w['s'])
        walls_arr[i, 4] = float(w['e'])
        walls_arr[i, 5] = float(w['h'])
    return _wall_loss_jit(float(p1[0]), float(p1[1]), float(p1[2]), float(p2[0]), float(p2[1]), float(p2[2]), walls_arr)
