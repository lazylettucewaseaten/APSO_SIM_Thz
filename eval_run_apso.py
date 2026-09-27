import sys
import time
import numpy as np
from chsr_sim import config

def evaluate_run_apso(wc, wd, beta, gamma):
    config.CELL_WEIGHT = wc
    config.DENSITY_WEIGHT = wd
    config.MOVEMENT_BETA = beta
    config.CLUSTER_GAMMA = gamma

    import chsr_sim.optimizer
    chsr_sim.optimizer.CELL_WEIGHT = config.CELL_WEIGHT
    chsr_sim.optimizer.DENSITY_WEIGHT = config.DENSITY_WEIGHT
    chsr_sim.optimizer.MOVEMENT_BETA = config.MOVEMENT_BETA
    chsr_sim.optimizer.CLUSTER_GAMMA = config.CLUSTER_GAMMA
    
    np.random.seed(42)

    from chsr_sim.environment import gen_walls, generate_human_density
    from chsr_sim.physics import calculate_sinr
    from chsr_sim.optimizer import apso_optimize, compute_total_movement
    
    walls = gen_walls()
    density = generate_human_density(t=0)
    
    initial_routers = [{'x': 16, 'y': 10, 'z': 2.5, 'phi': 0, 'alpha': 60, 'power': config.ROUTER_POWER} for _ in range(7)]
    
    optimized_routers = apso_optimize(initial_routers, density, walls, tier=4, prev_routers=initial_routers)
    
    sinr_map, coverage = calculate_sinr(optimized_routers, density, walls)
    move = compute_total_movement(initial_routers, optimized_routers)
    
    return coverage * 100, move

configs = {
    'A': (0.5, 0.5, 0.15, 0.3),
    'B': (0.4, 0.6, 0.15, 0.3),
    'C': (0.4, 0.6, 0.05, 0.3),
    'D': (0.4, 0.6, 0.15, 0.1)
}

print("Evaluating using run_apso.py logic...")
for name, (wc, wd, beta, gamma) in configs.items():
    cov, disp = evaluate_run_apso(wc, wd, beta, gamma)
    print(f"Config {name}: Coverage={cov:.1f}%, Displacement={disp:.1f}m")
