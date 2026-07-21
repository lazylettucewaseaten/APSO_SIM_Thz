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
def _compute_single_router_static_data(rx, ry, rz, human_density, walls_arr, 
                                       length, breadth, z_u, f_hz, c, k_f, h_human, human_penalty, ptx_dbm):
    base_power = np.zeros((length, breadth))
    angles = np.zeros((length, breadth))
    
    for x in range(length):
        for y in range(breadth):
            d_2d = np.sqrt((x - rx)**2 + (y - ry)**2)
            d_3d = np.sqrt(d_2d**2 + (rz - z_u)**2)
            if d_3d == 0.0: 
                d_3d = 1e-3
            
            fspl = 20.0 * np.log10(4.0 * np.pi * f_hz * d_3d / c)
            abs_loss = 4.343 * k_f * d_3d
            
            angle_to_user = np.degrees(np.arctan2(y - ry, x - rx))
            if angle_to_user < 0.0: 
                angle_to_user += 360.0
            
            angles[x, y] = angle_to_user
            
            blockage_penalty = 0.0
            if d_2d > 0.0:
                steps = int(d_2d)
                if steps > 0:
                    for step in range(1, steps):
                        px = int(rx + step * (x - rx) / steps)
                        py = int(ry + step * (y - ry) / steps)
                        if 0 <= px and px < length and 0 <= py and py < breadth:
                            d2d_c = np.sqrt((px - rx)**2 + (py - ry)**2)
                            z_c = z_u + (d2d_c / d_2d) * (rz - z_u)
                            if z_c <= h_human:
                                blockage_penalty += human_density[px, py] * human_penalty
            
            static_loss = _wall_loss_jit(rx, ry, rz, float(x), float(y), z_u, walls_arr)
            base_power[x, y] = ptx_dbm - fspl - abs_loss - blockage_penalty - static_loss
            
    return base_power, angles

@njit
def _apply_router_gain_jit(powers_i, base_power, angles, rphi, ralpha, rpower, g_max):
    length, breadth = base_power.shape
    for x in range(length):
        for y in range(breadth):
            ang_dev = abs((angles[x, y] - rphi + 180.0) % 360.0 - 180.0)
            if ang_dev <= ralpha / 2.0:
                gain = g_max
            else:
                gain = -100.0
            p_rx = base_power[x, y] + gain
            powers_i[x, y] = 10**(p_rx / 10.0) * rpower

@njit
def _compute_sinr_map_jit(powers, human_density, length, breadth, noise_dbm, sinr_th):
    sinr_map = np.zeros((length, breadth))
    noise_mw = 10**(noise_dbm / 10.0)
    
    covered_cells = 0
    density_sum = 0.0
    total_density = 0.0
    num_routers = powers.shape[0]
    
    for x in range(length):
        for y in range(breadth):
            total_density += human_density[x, y]
            
            max_sig = -1.0
            total_sig = 0.0
            
            for i in range(num_routers):
                sig = powers[i, x, y]
                total_sig += sig
                if sig > max_sig:
                    max_sig = sig
                    
            signal = max_sig
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
        
    return sinr_map, coverage

_WALLS_CACHE_ID = None
_WALLS_ARR_CACHE = None
_HUMAN_DENSITY_CACHE_ID = None
_ROUTER_STATIC_CACHE = {}

def calculate_sinr(routers, human_density, walls):
    global _WALLS_CACHE_ID, _WALLS_ARR_CACHE
    global _HUMAN_DENSITY_CACHE_ID, _ROUTER_STATIC_CACHE
    
    # 1. Convert walls to cache if changed
    if id(walls) != _WALLS_CACHE_ID:
        walls_arr = np.zeros((len(walls), 6))
        for i, w in enumerate(walls):
            walls_arr[i, 0] = 0.0 if w['o'] == 'h' else 1.0
            walls_arr[i, 1] = 30.0 if w['m'] == 'solid' else (20.0 if w['m'] == 'wood' else 15.0)
            walls_arr[i, 2] = float(w['p'])
            walls_arr[i, 3] = float(w['s'])
            walls_arr[i, 4] = float(w['e'])
            walls_arr[i, 5] = float(w['h'])
        _WALLS_ARR_CACHE = walls_arr
        _WALLS_CACHE_ID = id(walls)
    else:
        walls_arr = _WALLS_ARR_CACHE
        
    # 2. Reset router data cache if new time step (human density changed)
    if id(human_density) != _HUMAN_DENSITY_CACHE_ID:
        _ROUTER_STATIC_CACHE.clear()
        _HUMAN_DENSITY_CACHE_ID = id(human_density)
        
    length = int(LENGTH)
    breadth = int(BREADTH)
    powers = np.zeros((len(routers), length, breadth))
    
    for i, r in enumerate(routers):
        rx, ry, rz = float(r['x']), float(r['y']), float(r['z'])
        rphi, ralpha = float(r['phi']), float(r['alpha'])
        rpower = float(r.get('power', ROUTER_POWER))
        
        cache_key = (rx, ry, rz)
        if cache_key not in _ROUTER_STATIC_CACHE:
            base_power, angles = _compute_single_router_static_data(
                rx, ry, rz, human_density, walls_arr, 
                length, breadth, float(Z_U), float(F_HZ), float(C), 
                float(K_F), float(H_HUMAN), float(HUMAN_PENALTY_DB), float(PTX_DBM)
            )
            _ROUTER_STATIC_CACHE[cache_key] = (base_power, angles)
            
        base_power, angles = _ROUTER_STATIC_CACHE[cache_key]
        
        _apply_router_gain_jit(powers[i], base_power, angles, rphi, ralpha, rpower, float(G_MAX))
        
    return _compute_sinr_map_jit(powers, human_density, length, breadth, float(NOISE_DBM), float(SINR_TH))

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
