import numpy as np
from .config import *

def dbm_to_mw(dbm):
    return 10**(dbm / 10.0)

def mw_to_dbm(mw):
    return 10 * np.log10(mw + 1e-12)

def wall_loss(p1, p2, ws):
    loss = 0.0
    mx, Mx = min(p1[0], p2[0]), max(p1[0], p2[0])
    my, My = min(p1[1], p2[1]), max(p1[1], p2[1])
    
    for w in ws:
        ml = 30.0 if w['m'] == 'solid' else 20.0 if w['m'] == 'wood' else 15.0
        if w['o'] == 'h': 
            yw = w['p']
            if my < yw < My:
                if p2[1] != p1[1]:
                    t = (yw - p1[1]) / (p2[1] - p1[1])
                    xi = p1[0] + t * (p2[0] - p1[0])
                    if w['s'] <= xi <= w['e']:
                        zi = p1[2] + t * (p2[2] - p1[2])
                        if zi <= w['h']: loss += ml
        elif w['o'] == 'v': 
            xw = w['p']
            if mx < xw < Mx:
                if p2[0] != p1[0]:
                    t = (xw - p1[0]) / (p2[0] - p1[0])
                    yi = p1[1] + t * (p2[1] - p1[1])
                    if w['s'] <= yi <= w['e']:
                        zi = p1[2] + t * (p2[2] - p1[2])
                        if zi <= w['h']: loss += ml
    return loss

def calculate_sinr(routers, human_density, walls):
    powers = np.zeros((len(routers), LENGTH, BREADTH))
    for i, r in enumerate(routers):
        for x in range(LENGTH):
            for y in range(BREADTH):
                d_2d = np.sqrt((x - r['x'])**2 + (y - r['y'])**2)
                d_3d = np.sqrt(d_2d**2 + (r['z'] - Z_U)**2)
                if d_3d == 0: d_3d = 1e-3
                
                fspl = 20 * np.log10(4 * np.pi * F_HZ * d_3d / C)
                abs_loss = 4.343 * K_F * d_3d
                
                angle_to_user = np.degrees(np.arctan2(y - r['y'], x - r['x']))
                if angle_to_user < 0: angle_to_user += 360
                
                ang_dev = abs((angle_to_user - r['phi'] + 180) % 360 - 180)
                if ang_dev <= r['alpha'] / 2.0:
                    gain = G_MAX
                else:
                    gain = -100 
                
                blockage_penalty = 0
                if d_2d > 0:
                    steps = int(d_2d)
                    if steps > 0:
                        for step in range(1, steps):
                            px = int(r['x'] + step * (x - r['x']) / steps)
                            py = int(r['y'] + step * (y - r['y']) / steps)
                            if 0 <= px < LENGTH and 0 <= py < BREADTH:
                                d2d_c = np.sqrt((px - r['x'])**2 + (py - r['y'])**2)
                                z_c = Z_U + (d2d_c / d_2d) * (r['z'] - Z_U)
                                if z_c <= H_HUMAN:
                                    blockage_penalty += human_density[px, py] * HUMAN_PENALTY_DB
                
                static_loss = wall_loss((r['x'], r['y'], r['z']), (x, y, Z_U), walls)
                p_rx = PTX_DBM + gain - fspl - abs_loss - blockage_penalty - static_loss
                powers[i, x, y] = dbm_to_mw(p_rx)
                
    sinr_map = np.zeros((LENGTH, BREADTH))
    noise_mw = dbm_to_mw(NOISE_DBM)
    for x in range(LENGTH):
        for y in range(BREADTH):
            sig_powers = powers[:, x, y]
            best_ap = np.argmax(sig_powers)
            signal = sig_powers[best_ap]
            interference = np.sum(sig_powers) - signal
            sinr_mw = signal / (noise_mw + interference)
            sinr_map[x, y] = 10 * np.log10(sinr_mw + 1e-12)
            
    coverage = np.sum(sinr_map >= SINR_TH) / (LENGTH * BREADTH)
    return sinr_map, coverage
