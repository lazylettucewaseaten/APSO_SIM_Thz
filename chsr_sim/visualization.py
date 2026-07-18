import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from .config import *

def plot_room_scenario(walls, save_path="room_scenario.png"):
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlim(0, LENGTH)
    ax.set_ylim(0, BREADTH)
    ax.set_facecolor('#ffffff')
    
    for w in walls:
        if w['m'] == 'solid':
            c = '#555555'
        elif w['m'] == 'wood':
            c = '#8b4513' if w['h'] >= 3.0 else '#d2b48c'
        else:
            c = '#87ceeb'
            
        alpha = 1.0 if w['m'] != 'glass' else 0.5
        width = 0.4 if w['o'] == 'v' else w['e'] - w['s']
        height = 0.4 if w['o'] == 'h' else w['e'] - w['s']
        x = w['p'] - 0.2 if w['o'] == 'v' else w['s']
        y = w['s'] if w['o'] == 'v' else w['p'] - 0.2
        
        ax.add_patch(patches.Rectangle((x, y), width, height, facecolor=c, alpha=alpha, edgecolor='black', linewidth=0.5))

    solid_patch = patches.Patch(color='#555555', label='Solid Wall (30 dB, 3m)')
    wood_patch = patches.Patch(color='#8b4513', label='Wood Door (20 dB, 3m)')
    desk_patch = patches.Patch(color='#d2b48c', label='Wood Desk/Cubicle (20 dB, 1m)')
    glass_patch = patches.Patch(color='#87ceeb', alpha=0.5, label='Glass Window (15 dB, 3m)')
    
    ax.set_title("Room Scenario Layout (Top-Down View)")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.legend(handles=[solid_patch, wood_patch, desk_patch, glass_patch], loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=4)
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()

def plot_environment(sinr_map, routers, human_density, walls, t, cov):
    plt.figure(figsize=(10, 6))
    plt.imshow(sinr_map.T, origin='lower', cmap='viridis', vmin=-10, vmax=30)
    plt.colorbar(label='SINR (dB)')
    plt.imshow(human_density.T, origin='lower', cmap='Reds', alpha=0.3)
    
    ax = plt.gca()
    for w in walls:
        if w['m'] == 'solid':
            c = '#555555'
        elif w['m'] == 'wood':
            c = '#8b4513' if w['h'] >= 3.0 else '#d2b48c'
        else:
            c = '#87ceeb'
            
        alpha = 1.0 if w['m'] != 'glass' else 0.5
        if w['o'] == 'h':
            ax.add_patch(patches.Rectangle((w['s'], w['p']-0.2), w['e']-w['s'], 0.4, facecolor=c, alpha=alpha))
        else:
            ax.add_patch(patches.Rectangle((w['p']-0.2, w['s']), 0.4, w['e']-w['s'], facecolor=c, alpha=alpha))

    for r in routers:
        plt.plot(r['x'], r['y'], 'k^', markersize=10)
        dx = np.cos(np.radians(r['phi'])) * 3
        dy = np.sin(np.radians(r['phi'])) * 3
        plt.arrow(r['x'], r['y'], dx, dy, head_width=0.5, head_length=0.5, fc='k', ec='k')
    
    plt.title(f"Time {t} | Cov >= {SINR_TH}dB: {cov*100:.1f}%")
    plt.xlim(0, LENGTH); plt.ylim(0, BREADTH)
    plt.tight_layout()
    plt.savefig(f'simulation_t{t}.png')
    plt.close()
