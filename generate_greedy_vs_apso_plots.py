import time
import numpy as np
import matplotlib.pyplot as plt
import os
from chsr_sim.config import *
from chsr_sim.environment import gen_walls, generate_human_density
from chsr_sim.optimizer import apso_optimize, hungarian_reassign, compute_total_movement
from chsr_sim.physics import calculate_sinr
from greedy_optimizer import greedy_set_cover_optimize

plt.style.use('seaborn-v0_8-paper')
plt.rcParams.update({
    'font.size': 14, 'axes.labelsize': 16, 'axes.titlesize': 18,
    'xtick.labelsize': 14, 'ytick.labelsize': 14,
    'legend.fontsize': 14, 'figure.dpi': 300, 'lines.linewidth': 2
})

output_dir = "paper_plots"
os.makedirs(output_dir, exist_ok=True)

walls = gen_walls()
n_routers = 7

# Scenarios
time_steps = [0, 1, 2]
scenario_names = ['Scenario 1 (t=0)', 'Scenario 2 (t=1)', 'Scenario 3 (t=2)']

apso_cov = []
apso_time = []
apso_move = []

greedy_cov = []
greedy_time = []
greedy_move = []

# Initial random routers for the very first step
np.random.seed(42)
initial_routers = []
for _ in range(n_routers):
    initial_routers.append({
        'x': np.random.randint(0, LENGTH),
        'y': np.random.randint(0, BREADTH),
        'z': 2.5, 'phi': 0, 'alpha': 60, 'power': ROUTER_POWER
    })

prev_routers_apso = [dict(r) for r in initial_routers]
prev_routers_greedy = [dict(r) for r in initial_routers]

print("Running pipeline for plots...")

for t in time_steps:
    print(f"\n--- Running {scenario_names[t]} ---")
    density = generate_human_density(t=t)
    
    # JIT warmup
    if t == 0:
        calculate_sinr(initial_routers, density, walls)
        
    # --- APSO ---
    start = time.time()
    # Using tier 4 for fair movement comparison
    optimized_apso = apso_optimize(prev_routers_apso, density, walls, tier=4, prev_routers=prev_routers_apso)
    apso_t = time.time() - start
    _, cov_apso = calculate_sinr(optimized_apso, density, walls)
    move_apso = compute_total_movement(prev_routers_apso, optimized_apso)
    
    apso_cov.append(cov_apso * 100)
    apso_time.append(apso_t)
    apso_move.append(move_apso)
    
    # --- GREEDY ---
    start = time.time()
    # Greedy set cover
    optimized_greedy, cov_greedy = greedy_set_cover_optimize(density, walls, n_routers, candidates_per_step=1000)
    greedy_t = time.time() - start
    
    # Assign greedy output optimally to minimize movement distance (giving greedy the best case)
    optimized_greedy_assigned = hungarian_reassign(prev_routers_greedy, optimized_greedy)
    move_greedy = compute_total_movement(prev_routers_greedy, optimized_greedy_assigned)
    
    greedy_cov.append(cov_greedy * 100) # Cov greedy from the function is density ratio
    greedy_time.append(greedy_t)
    greedy_move.append(move_greedy)
    
    # Update previous positions for next time step
    prev_routers_apso = optimized_apso
    prev_routers_greedy = optimized_greedy_assigned

# --- Plot 1: Coverage Comparison ---
x = np.arange(len(scenario_names))
width = 0.35

plt.figure(figsize=(8, 6))
plt.bar(x - width/2, apso_cov, width, label='HPSO', color='#1f77b4', edgecolor='black')
plt.bar(x + width/2, greedy_cov, width, label='Greedy Set Cover', color='#ff7f0e', edgecolor='black')
plt.xlabel('Dynamic Scenarios')
plt.ylabel('Effective Coverage (%)')
# plt.title('Actual Pipeline: Coverage Comparison')
plt.xticks(x, scenario_names)
plt.legend(loc='lower right')
plt.ylim(0, 105)
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig(f"{output_dir}/pipeline_coverage_comparison.pdf")
plt.close()

# --- Plot 2: Movement Comparison ---
plt.figure(figsize=(8, 6))
plt.bar(x - width/2, apso_move, width, label='HPSO', color='#1f77b4', edgecolor='black')
plt.bar(x + width/2, greedy_move, width, label='Greedy Set Cover (with Hungarian Assignment)', color='#ff7f0e', edgecolor='black')
plt.xlabel('Dynamic Scenarios')
plt.ylabel('Total Physical Displacement (meters)')
# plt.title('Actual Pipeline: Kinetic Energy Expenditure (Movement)')
plt.xticks(x, scenario_names)
plt.legend(loc='upper right')
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig(f"{output_dir}/pipeline_movement_comparison.pdf")
plt.close()

# --- Plot 3: Execution Time Comparison ---
plt.figure(figsize=(8, 6))
plt.plot(scenario_names, apso_time, marker='o', label='HPSO', color='#1f77b4', markersize=10, linewidth=3)
plt.plot(scenario_names, greedy_time, marker='s', label='Greedy Set Cover', color='#ff7f0e', markersize=10, linewidth=3)
plt.xlabel('Dynamic Scenarios')
plt.ylabel('Execution Time (seconds)')
# plt.title('Actual Pipeline: Computational Speed')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig(f"{output_dir}/pipeline_execution_time.pdf")
plt.close()

print("Pipeline comparison plots generated successfully.")
