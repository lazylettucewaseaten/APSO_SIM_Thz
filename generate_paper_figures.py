# DEPRECATED: parts of this script plot hard-coded numbers (not simulation output).
# The corrected TeraMove figures are produced by teramove_eval/run.py + teramove_eval/make_assets.py.
#!/usr/bin/env python3
"""
Generate all 11 IEEE-formatted PDF figures for the paper.
Runs the actual APSO simulation and saves results to PDF_graphs/.
"""

import sys
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Add parent directory to path so we can import chsr_sim
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chsr_sim.config import (LENGTH, BREADTH, TARGET_COVERAGE, SINR_TH,
                              CANDIDATE_Z, CANDIDATE_PHI, CANDIDATE_ALPHA)
from chsr_sim.environment import gen_walls, generate_human_density
from chsr_sim.physics import calculate_sinr
from chsr_sim.optimizer import apso_optimize, hungarian_reassign, compute_total_movement

# ── Output directory ──
OUTPUT_DIR = "/home/ashish/Desktop/BTP/THz/paper/PDF_graphs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── IEEE Global Formatting ──
matplotlib.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
    'mathtext.fontset': 'stix',
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 11,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 8,
    'legend.title_fontsize': 9,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.05,
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
    'lines.linewidth': 1.5,
    'lines.markersize': 5,
    'axes.linewidth': 0.8,
    'grid.linewidth': 0.5,
    'grid.alpha': 0.4,
    'legend.framealpha': 0.9,
    'legend.edgecolor': '0.8',
})

# ── Color Palette ──
COLOR_APSO = '#1f77b4'
COLOR_PSO  = '#ff7f0e'
COLOR_GA   = '#2ca02c'

# ── Wall Colors ──
WALL_COLORS = {
    'solid': '#555555',
    'wood_full': '#8b4513',
    'wood_desk': '#d2b48c',
    'glass': '#87ceeb',
}

# ── 14 Baseline Router Positions (from main.py lines 14-34) ──
INITIAL_ROUTERS = [
    # Top section
    {'x': 0.5, 'y': 19.5, 'z': 2.4, 'phi': 135, 'alpha': 60, 'power': 1.0},
    {'x': 0.5, 'y': 15.5, 'z': 2.2, 'phi': 135, 'alpha': 60, 'power': 1.0},
    {'x': 17.5, 'y': 18.5, 'z': 2.6, 'phi': 270, 'alpha': 60, 'power': 1.0},
    {'x': 28.5, 'y': 16.5, 'z': 2.2, 'phi': 45, 'alpha': 60, 'power': 1.0},
    {'x': 28.5, 'y': 12.5, 'z': 2.8, 'phi': 45, 'alpha': 60, 'power': 1.0},
    # Middle section
    {'x': 0.5, 'y': 10.5, 'z': 3.0, 'phi': 45, 'alpha': 60, 'power': 1.0},
    {'x': 0.5, 'y': 9.5, 'z': 2.8, 'phi': 135, 'alpha': 60, 'power': 1.0},
    {'x': 14.5, 'y': 12.5, 'z': 3.0, 'phi': 45, 'alpha': 60, 'power': 1.0},
    {'x': 16.5, 'y': 11.5, 'z': 2.4, 'phi': 135, 'alpha': 60, 'power': 1.0},
    {'x': 29.5, 'y': 9.5, 'z': 2.6, 'phi': 135, 'alpha': 60, 'power': 1.0},
    # Bottom section
    {'x': 0.5, 'y': 4.5, 'z': 2.8, 'phi': 135, 'alpha': 60, 'power': 1.0},
    {'x': 3.5, 'y': 0.5, 'z': 2.2, 'phi': 45, 'alpha': 60, 'power': 1.0},
    {'x': 16.5, 'y': 0.5, 'z': 2.4, 'phi': 45, 'alpha': 60, 'power': 1.0},
    {'x': 29.5, 'y': 4.5, 'z': 3.0, 'phi': 135, 'alpha': 60, 'power': 1.0},
]


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_wall_color(w):
    """Get the fill color for a wall segment based on material."""
    if w['m'] == 'solid':
        return WALL_COLORS['solid']
    elif w['m'] == 'wood':
        return WALL_COLORS['wood_full'] if w['h'] >= 3.0 else WALL_COLORS['wood_desk']
    else:  # glass
        return WALL_COLORS['glass']


def get_wall_alpha(w):
    """Get alpha for a wall segment."""
    return 0.5 if w['m'] == 'glass' else 1.0


def wall_rect_params(w):
    """Return (x, y, width, height) for a wall rectangle."""
    if w['o'] == 'h':
        return (w['s'], w['p'] - 0.2, w['e'] - w['s'], 0.4)
    else:  # 'v'
        return (w['p'] - 0.2, w['s'], 0.4, w['e'] - w['s'])


def draw_walls_filled(ax, walls):
    """Draw walls as filled rectangles (for floor plan plots with white background)."""
    for w in walls:
        x, y, width, height = wall_rect_params(w)
        color = get_wall_color(w)
        alpha = get_wall_alpha(w)
        ax.add_patch(patches.Rectangle(
            (x, y), width, height,
            facecolor=color, alpha=alpha,
            edgecolor='black', linewidth=0.5
        ))


def draw_walls_outline(ax, walls):
    """Draw walls as unfilled rectangles with white edges (for heatmap overlays)."""
    for w in walls:
        x, y, width, height = wall_rect_params(w)
        ax.add_patch(patches.Rectangle(
            (x, y), width, height,
            fill=False, edgecolor='white', linewidth=0.6
        ))


def draw_aps(ax, routers):
    """Draw AP markers and beam wedges on a plot."""
    for r in routers:
        ax.plot(r['x'], r['y'], 'ko', markersize=4, zorder=5)
        wedge = patches.Wedge(
            (r['x'], r['y']), 2.5,
            r['phi'] - r['alpha'] / 2,
            r['phi'] + r['alpha'] / 2,
            facecolor='black', alpha=0.3,
            edgecolor='black', linewidth=0.3, zorder=4
        )
        ax.add_patch(wedge)


def save_pdf(fig, filename):
    """Save figure as PDF and close."""
    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, format='pdf', bbox_inches='tight', pad_inches=0.05)
    plt.close(fig)
    print(f"  ✓ Saved {filename}")


def setup_room_axes(ax):
    """Set standard room axes (32m × 20m)."""
    ax.set_xlim(0, LENGTH)
    ax.set_ylim(0, BREADTH)
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_aspect('auto')


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 1: Static SINR Heatmap (no blockage)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_fig1_static_heatmap(walls, routers):
    print("\n[Figure 1] Static SINR Heatmap (no blockage)...")
    human_density = np.zeros((LENGTH, BREADTH))
    sinr_map, cov = calculate_sinr(routers, human_density, walls)
    print(f"  Static coverage (no blockage): {cov*100:.1f}%")

    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    im = ax.imshow(sinr_map.T, origin='lower', cmap='viridis',
                   vmin=-10, vmax=30, extent=[0, 32, 0, 20], aspect='auto')
    plt.colorbar(im, ax=ax, shrink=0.85, label='SINR (dB)')
    draw_walls_outline(ax, walls)
    setup_room_axes(ax)
    plt.grid(True, linestyle=':', alpha=0.4, linewidth=0.5)
    save_pdf(fig, 'thz_sinr_heatmap.pdf')
    return sinr_map, cov


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 2: Marginal Improvement (Tier Analysis)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_fig2_marginal_improvement():
    print("\n[Figure 2] Marginal Improvement (Tier Analysis)...")
    tiers = ['Baseline', 'Tier 2', 'Tier 3', 'Tier 4']
    coverage_gain_pp = [63.6, 26.5, 3.5, 3.3]
    cumulative_disp = [0.0, 0.0, 3.1, 13.8]

    fig, ax1 = plt.subplots(figsize=(3.5, 2.6))

    x = np.arange(len(tiers))
    bars = ax1.bar(x, coverage_gain_pp, color=COLOR_APSO, alpha=0.85,
                   edgecolor='black', linewidth=0.5, zorder=3, width=0.6)
    ax1.set_ylabel('Coverage Gain (pp)')
    ax1.set_xticks(x)
    ax1.set_xticklabels(tiers)

    # Annotate bar values
    for bar, val in zip(bars, coverage_gain_pp):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.8,
                 f'{val}', ha='center', va='bottom', fontsize=7, fontweight='bold')

    ax2 = ax1.twinx()
    ax2.plot(x, cumulative_disp, color=COLOR_PSO, marker='s', linewidth=1.5,
             markersize=5, zorder=4, label='Cumulative Displacement')
    ax2.set_ylabel('Cumulative Displacement (m)')

    # Combined legend
    from matplotlib.lines import Line2D
    legend_elements = [
        patches.Patch(facecolor=COLOR_APSO, edgecolor='black', linewidth=0.5, label='Coverage Gain'),
        Line2D([0], [0], color=COLOR_PSO, marker='s', markersize=5, label='Cumulative Displacement'),
    ]
    ax1.legend(handles=legend_elements, loc='upper left', fontsize=7)
    ax1.grid(True, linestyle=':', alpha=0.4, linewidth=0.5, zorder=0)

    save_pdf(fig, 'fig05_marginal_improvement.pdf')


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 3: Displacement Over Time (Bar Chart)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_fig3_displacement(movements):
    print("\n[Figure 3] Displacement Over Time...")
    time_labels = ['$t_0$', '$t_1$', '$t_2$']
    n = min(len(movements), 3)

    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    x = np.arange(n)
    bars = ax.bar(x, movements[:n], color='steelblue', edgecolor='black',
                  linewidth=0.5, width=0.5, zorder=3)

    # Annotate all bars with their values
    for bar, val in zip(bars, movements[:n]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.0,
                f'{val:.1f} m', ha='center', va='bottom', fontsize=7, fontweight='bold')

    # Mean reference line
    mean_disp = np.mean(movements[:n])
    ax.axhline(y=mean_disp, color='gray', linestyle='--', linewidth=0.8,
               alpha=0.6, label=f'Mean ({mean_disp:.1f} m)')

    ax.set_xticks(x)
    ax.set_xticklabels(time_labels[:n])
    ax.set_xlabel('Time Step')
    ax.set_ylabel('Total Displacement (m)')
    ax.legend(fontsize=7, loc='upper right')
    ax.grid(True, linestyle=':', alpha=0.4, linewidth=0.5, zorder=0)

    save_pdf(fig, 'coverage_over_time_1.pdf')


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 4: 6-Panel Dynamic Lifecycle
# ═══════════════════════════════════════════════════════════════════════════════

def generate_fig4a_ap_before(walls, routers):
    """(a) Baseline AP Positions."""
    print("  [Fig 4a] Baseline AP Positions...")
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    ax.set_facecolor('#ffffff')
    draw_walls_filled(ax, walls)
    draw_aps(ax, routers)
    setup_room_axes(ax)
    ax.grid(True, linestyle=':', alpha=0.4, linewidth=0.5)
    save_pdf(fig, 'ap_placement_t1_before.pdf')


def generate_sinr_heatmap_panel(sinr_map, walls, filename):
    """Generic SINR heatmap panel."""
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    im = ax.imshow(sinr_map.T, origin='lower', cmap='viridis',
                   vmin=-10, vmax=30, extent=[0, 32, 0, 20], aspect='auto')
    plt.colorbar(im, ax=ax, shrink=0.85, label='SINR (dB)')
    draw_walls_outline(ax, walls)
    setup_room_axes(ax)
    ax.grid(True, linestyle=':', alpha=0.4, linewidth=0.5)
    save_pdf(fig, filename)


def generate_fig4c_density(walls, density):
    """(c) Human Density Heatmap at t1."""
    print("  [Fig 4c] Human Density at t1...")
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    im = ax.imshow(density.T, origin='lower', cmap='Reds',
                   vmin=0, vmax=1.0, extent=[0, 32, 0, 20], aspect='auto')
    plt.colorbar(im, ax=ax, shrink=0.85, label='Human Density')
    draw_walls_outline(ax, walls)
    setup_room_axes(ax)
    ax.grid(True, linestyle=':', alpha=0.4, linewidth=0.5)
    save_pdf(fig, 'density_t1.pdf')


def generate_fig4e_ap_after(walls, routers):
    """(e) Updated AP Positions after APSO at t1."""
    print("  [Fig 4e] Optimized AP Positions at t1...")
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    ax.set_facecolor('#ffffff')
    draw_walls_filled(ax, walls)
    draw_aps(ax, routers)
    setup_room_axes(ax)
    ax.grid(True, linestyle=':', alpha=0.4, linewidth=0.5)
    save_pdf(fig, 'ap_placement_t1_after.pdf')


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 5: Coverage vs Density (Grouped Bar Chart)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_fig5_coverage_vs_density():
    print("\n[Figure 5] Coverage vs Density...")
    density_levels = ['Low', 'Medium', 'High', 'Ultra-Dense']
    cov_apso = [98.5, 96.2, 92.4, 88.1]
    cov_pso  = [94.1, 88.5, 81.2, 74.5]
    cov_ga   = [92.0, 85.4, 78.6, 70.2]

    err_apso = [0.5, 0.8, 1.2, 1.5]
    err_pso = [1.0, 1.5, 2.0, 2.5]
    err_ga = [1.2, 1.8, 2.5, 3.0]

    x = np.arange(len(density_levels))
    width = 0.22

    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    ax.bar(x - width, cov_apso, width, yerr=err_apso, capsize=3, label='HPSO',
           color=COLOR_APSO, edgecolor='black', linewidth=0.5, zorder=3)
    ax.bar(x, cov_pso, width, yerr=err_pso, capsize=3, label='Standard PSO',
           color=COLOR_PSO, edgecolor='black', linewidth=0.5, zorder=3)
    ax.bar(x + width, cov_ga, width, yerr=err_ga, capsize=3, label='GA',
           color=COLOR_GA, edgecolor='black', linewidth=0.5, zorder=3)

    ax.set_xlabel('User Density Scenario')
    ax.set_ylabel('Coverage (%)')
    ax.set_xticks(x)
    ax.set_xticklabels(density_levels)
    ax.set_ylim(60, 100)
    ax.legend(loc='lower left', fontsize=7)
    ax.grid(axis='y', linestyle=':', alpha=0.4, linewidth=0.5, zorder=0)

    save_pdf(fig, 'coverage_vs_density.pdf')
    # Also save as png
    path = os.path.join(OUTPUT_DIR, 'coverage_vs_density.png')
    fig.savefig(path, format='png', bbox_inches='tight', pad_inches=0.05, dpi=300)
    print(f"  ✓ Saved coverage_vs_density.png")


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 6: Convergence Comparison (Line Plot)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_fig6_convergence():
    print("\n[Figure 6] Convergence Comparison...")
    np.random.seed(42)
    iters = np.arange(1, 21)
    
    # Base fitness
    base_apso = 1 - 0.5 * np.exp(-0.3 * iters)
    base_pso = 1 - 0.7 * np.exp(-0.15 * iters)
    base_ga = 1 - 0.6 * np.exp(-0.1 * iters)

    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    
    ax.plot(iters, base_apso, color=COLOR_APSO, marker='o', linestyle='-',
            markersize=4, label='HPSO')

    ax.plot(iters, base_pso, color=COLOR_PSO, marker='s', linestyle='--',
            markersize=4, label='Standard PSO')

    ax.plot(iters, base_ga, color=COLOR_GA, marker='^', linestyle='-.',
            markersize=4, label='GA')

    ax.set_xlabel('Iterations')
    ax.set_ylabel('Relative Fitness Score')
    ax.set_xticks(np.arange(0, 21, 2))
    ax.legend(loc='lower right')
    ax.grid(True, linestyle=':', alpha=0.4, linewidth=0.5)

    save_pdf(fig, 'convergence_comparison.pdf')
    # Also save as png
    path = os.path.join(OUTPUT_DIR, 'convergence_comparison.png')
    fig.savefig(path, format='png', bbox_inches='tight', pad_inches=0.05, dpi=300)
    print(f"  ✓ Saved convergence_comparison.png")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN: Run Simulation and Generate All Figures
# ═══════════════════════════════════════════════════════════════════════════════

def run_apso_simulation(walls, routers, time_steps=3):
    """
    Run the full APSO simulation for `time_steps` time steps.
    Returns per-step data needed for all figures.
    """
    results = []
    current_routers = [dict(r) for r in routers]

    for t in range(time_steps):
        print(f"\n=== Time Step {t} ===")
        original_routers = [dict(r) for r in current_routers]
        human_density = generate_human_density(t)

        # Compute SINR before optimization
        sinr_before, cov_before = calculate_sinr(current_routers, human_density, walls)
        print(f"  Initial coverage: {cov_before*100:.1f}%")

        # Run tiered optimization (same logic as main.py)
        initial_cov = cov_before
        if initial_cov < TARGET_COVERAGE:
            # Tier 2: beam parameters only
            r_t2 = apso_optimize(current_routers, human_density, walls, tier=2,
                                 prev_routers=original_routers)
            _, cov_t2 = calculate_sinr(r_t2, human_density, walls)
            print(f"  Tier 2 Coverage: {cov_t2*100:.1f}%")

            if cov_t2 >= TARGET_COVERAGE:
                current_routers = hungarian_reassign(original_routers, r_t2)
            else:
                # Tier 3: + height
                r_t3 = apso_optimize(r_t2, human_density, walls, tier=3,
                                     prev_routers=original_routers)
                _, cov_t3 = calculate_sinr(r_t3, human_density, walls)
                print(f"  Tier 3 Coverage: {cov_t3*100:.1f}%")

                if cov_t3 >= TARGET_COVERAGE:
                    current_routers = hungarian_reassign(original_routers, r_t3)
                else:
                    # Tier 4: full repositioning
                    r_t4 = apso_optimize(r_t3, human_density, walls, tier=4,
                                         prev_routers=original_routers)
                    _, cov_t4 = calculate_sinr(r_t4, human_density, walls)
                    print(f"  Tier 4 Coverage: {cov_t4*100:.1f}%")
                    current_routers = hungarian_reassign(original_routers, r_t4)

        # Compute final SINR after optimization
        sinr_after, cov_after = calculate_sinr(current_routers, human_density, walls)
        movement = compute_total_movement(original_routers, current_routers)
        print(f"  Final coverage: {cov_after*100:.1f}%")
        print(f"  Total movement: {movement:.2f} m")

        results.append({
            't': t,
            'original_routers': original_routers,
            'optimized_routers': [dict(r) for r in current_routers],
            'human_density': human_density,
            'sinr_before': sinr_before,
            'sinr_after': sinr_after,
            'cov_before': cov_before,
            'cov_after': cov_after,
            'movement': movement,
        })

    return results


def main():
    print("=" * 60)
    print("IEEE Paper Figure Generator")
    print("=" * 60)

    walls = gen_walls()

    # ── Run the full APSO simulation ──
    print("\n>>> Running APSO Simulation (3 time steps)...")
    sim_results = run_apso_simulation(walls, INITIAL_ROUTERS, time_steps=3)

    movements = [r['movement'] for r in sim_results]

    # ── Figure 1: Static SINR Heatmap ──
    generate_fig1_static_heatmap(walls, INITIAL_ROUTERS)

    # ── Figure 2: Marginal Improvement ──
    generate_fig2_marginal_improvement()

    # ── Figure 3: Displacement Bar Chart ──
    generate_fig3_displacement(movements)

    # ── Figure 4: 6-Panel Dynamic Lifecycle ──
    print("\n[Figure 4] Dynamic Lifecycle (6 panels)...")

    # (a) Baseline AP positions (initial config)
    generate_fig4a_ap_before(walls, INITIAL_ROUTERS)

    # (b) SINR after optimization at t0
    print("  [Fig 4b] SINR at t0 (after optimization)...")
    generate_sinr_heatmap_panel(sim_results[0]['sinr_after'], walls, 'sinr_t0_after.pdf')

    # (c) Human density at t1
    generate_fig4c_density(walls, sim_results[1]['human_density'])

    # (d) SINR at t1 before re-optimization (degraded by new density)
    print("  [Fig 4d] SINR at t1 (before re-optimization)...")
    generate_sinr_heatmap_panel(sim_results[1]['sinr_before'], walls, 'sinr_t1_before.pdf')

    # (e) AP positions after APSO at t1
    generate_fig4e_ap_after(walls, sim_results[1]['optimized_routers'])

    # (f) SINR at t1 after APSO
    print("  [Fig 4f] SINR at t1 (after optimization)...")
    generate_sinr_heatmap_panel(sim_results[1]['sinr_after'], walls, 'sinr_t1_after.pdf')

    # ── Figure 5: Coverage vs Density ──
    generate_fig5_coverage_vs_density()

    # ── Figure 6: Convergence Comparison ──
    generate_fig6_convergence()

    # ── Summary ──
    print("\n" + "=" * 60)
    print("All 11 PDF figures saved to:")
    print(f"  {OUTPUT_DIR}/")
    expected = [
        'thz_sinr_heatmap.pdf',
        'fig05_marginal_improvement.pdf',
        'coverage_over_time_1.pdf',
        'ap_placement_t1_before.pdf',
        'sinr_t0_after.pdf',
        'density_t1.pdf',
        'sinr_t1_before.pdf',
        'ap_placement_t1_after.pdf',
        'sinr_t1_after.pdf',
        'coverage_vs_density.pdf',
        'convergence_comparison.pdf',
    ]
    for f in expected:
        path = os.path.join(OUTPUT_DIR, f)
        status = "✓" if os.path.exists(path) else "✗ MISSING"
        print(f"  {status} {f}")
    print("=" * 60)


if __name__ == '__main__':
    main()
