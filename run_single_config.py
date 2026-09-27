import sys
import time
import numpy as np
import gc

# Disable matplotlib/tkinter strictly
import matplotlib
matplotlib.use('Agg')

from chsr_sim import config

def evaluate_config(wc, wd, beta, gamma, steps):
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
    from chsr_sim.optimizer import apso_optimize, hungarian_reassign, compute_total_movement
    import chsr_sim.physics as phys
    
    # Patch to avoid OOM
    original_calculate_sinr = phys.calculate_sinr
    def patched_calculate_sinr(r, hd, w):
        if len(phys._ROUTER_STATIC_CACHE) > 5000:
            phys._ROUTER_STATIC_CACHE.clear()
        return original_calculate_sinr(r, hd, w)
    
    phys.calculate_sinr = patched_calculate_sinr
    chsr_sim.optimizer.calculate_sinr = patched_calculate_sinr

    walls = gen_walls()
    routers = [
        {'x': 0.5, 'y': 19.5, 'z': 2.4, 'phi': 135, 'alpha': 60, 'power': 1.0},
        {'x': 0.5, 'y': 15.5, 'z': 2.2, 'phi': 135, 'alpha': 60, 'power': 1.0},
        {'x': 17.5, 'y': 18.5, 'z': 2.6, 'phi': 270, 'alpha': 60, 'power': 1.0},
        {'x': 28.5, 'y': 16.5, 'z': 2.2, 'phi': 45, 'alpha': 60, 'power': 1.0},
        {'x': 28.5, 'y': 12.5, 'z': 2.8, 'phi': 45, 'alpha': 60, 'power': 1.0},
        {'x': 0.5, 'y': 10.5, 'z': 3.0, 'phi': 45, 'alpha': 60, 'power': 1.0},
        {'x': 0.5, 'y': 9.5, 'z': 2.8, 'phi': 135, 'alpha': 60, 'power': 1.0},
        {'x': 14.5, 'y': 12.5, 'z': 3.0, 'phi': 45, 'alpha': 60, 'power': 1.0},
        {'x': 16.5, 'y': 11.5, 'z': 2.4, 'phi': 135, 'alpha': 60, 'power': 1.0},
        {'x': 29.5, 'y': 9.5, 'z': 2.6, 'phi': 135, 'alpha': 60, 'power': 1.0},
        {'x': 0.5, 'y': 4.5, 'z': 2.8, 'phi': 135, 'alpha': 60, 'power': 1.0},
        {'x': 3.5, 'y': 0.5, 'z': 2.2, 'phi': 45, 'alpha': 60, 'power': 1.0},
        {'x': 16.5, 'y': 0.5, 'z': 2.4, 'phi': 45, 'alpha': 60, 'power': 1.0},
        {'x': 29.5, 'y': 4.5, 'z': 3.0, 'phi': 135, 'alpha': 60, 'power': 1.0}
    ]

    total_movement_sum = 0
    avg_coverage = 0

    for t in range(steps):
        t_step = time.time()
        original_routers = [dict(r) for r in routers]
        human_density = generate_human_density(t)
        
        sinr_map_before, cov_before = calculate_sinr(routers, human_density, walls)
        initial_cov = cov_before
        
        if initial_cov < config.TARGET_COVERAGE:
            r_t12 = apso_optimize(routers, human_density, walls, tier=2, prev_routers=original_routers)
            _, cov_t12 = calculate_sinr(r_t12, human_density, walls)
            
            if cov_t12 >= config.TARGET_COVERAGE:
                routers = hungarian_reassign(original_routers, r_t12)
                cov = cov_t12
            else:
                r_t3 = apso_optimize(r_t12, human_density, walls, tier=3, prev_routers=original_routers)
                _, cov_t3 = calculate_sinr(r_t3, human_density, walls)
                
                if cov_t3 >= config.TARGET_COVERAGE:
                    routers = hungarian_reassign(original_routers, r_t3)
                    cov = cov_t3
                else:
                    r_t4 = apso_optimize(r_t3, human_density, walls, tier=4, prev_routers=original_routers)
                    _, cov_t4 = calculate_sinr(r_t4, human_density, walls)
                    routers = hungarian_reassign(original_routers, r_t4)
                    cov = cov_t4
        else:
            cov = initial_cov

        move = compute_total_movement(original_routers, routers)
        total_movement_sum += move
        
        _, cov_after = calculate_sinr(routers, human_density, walls)
        avg_coverage += cov_after
        gc.collect()
        
    avg_coverage = avg_coverage / steps
    return avg_coverage * 100, total_movement_sum

if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Usage: python run_single_config.py wc wd beta gamma steps")
        sys.exit(1)
        
    wc = float(sys.argv[1])
    wd = float(sys.argv[2])
    beta = float(sys.argv[3])
    gamma = float(sys.argv[4])
    steps = int(sys.argv[5])
    
    cov, disp = evaluate_config(wc, wd, beta, gamma, steps)
    print(f"RESULT: cov={cov:.1f}, disp={disp:.1f}")
