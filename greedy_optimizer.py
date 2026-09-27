import numpy as np
import time
from numba import njit
from chsr_sim.config import *
from chsr_sim.physics import calculate_sinr
from chsr_sim.environment import gen_walls, generate_human_density

def greedy_set_cover_optimize(human_density, walls, n_routers, candidates_per_step=1000):
    """
    Greedy Set Cover algorithm for Router Placement.
    Iteratively picks the best router configuration that maximizes marginal coverage.
    """
    print(f"Running Greedy Set Cover Optimization for {n_routers} routers...")
    start_time = time.time()
    
    selected_routers = []
    
    for i in range(n_routers):
        best_router = None
        best_score = -float('inf')
        
        # Sample candidates
        xs = np.random.randint(0, LENGTH, candidates_per_step)
        ys = np.random.randint(0, BREADTH, candidates_per_step)
        zs = np.random.choice(CANDIDATE_Z, candidates_per_step)
        phis = np.random.choice(CANDIDATE_PHI, candidates_per_step)
        alphas = np.random.choice(CANDIDATE_ALPHA, candidates_per_step)
        
        for j in range(candidates_per_step):
            candidate = {
                'x': xs[j],
                'y': ys[j],
                'z': zs[j],
                'phi': phis[j],
                'alpha': alphas[j],
                'power': ROUTER_POWER
            }
            
            test_routers = selected_routers + [candidate]
            
            sinr_map, coverage = calculate_sinr(test_routers, human_density, walls)
            
            covered_mask = sinr_map >= SINR_TH
            total_density = np.sum(human_density)
            if total_density > 0:
                density_ratio = np.sum(human_density[covered_mask]) / total_density
            else:
                density_ratio = np.sum(covered_mask) / (LENGTH * BREADTH)
                
            score = density_ratio
            
            if score > best_score:
                best_score = score
                best_router = candidate
                
        selected_routers.append(best_router)
        print(f"  Step {i+1}/{n_routers} | Best Greedy Score: {best_score:.4f} | Router: (x={best_router['x']}, y={best_router['y']}, z={best_router['z']})")
        
    end_time = time.time()
    print(f"Greedy Optimization completed in {end_time - start_time:.2f} seconds.")
    return selected_routers, best_score

if __name__ == "__main__":
    walls = gen_walls()
    density = generate_human_density(t=0)
    # Run once to compile JIT
    dummy_routers = [{'x': 10, 'y': 10, 'z': 2.5, 'phi': 0, 'alpha': 60, 'power': ROUTER_POWER}]
    calculate_sinr(dummy_routers, density, walls)
    
    # Let's run it with a good number of candidates
    routers, score = greedy_set_cover_optimize(density, walls, n_routers=7, candidates_per_step=1000)
    print(f"Final Greedy Coverage Score: {score:.4f}")
