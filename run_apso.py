import time
from chsr_sim.config import *
from chsr_sim.environment import gen_walls, generate_human_density
from chsr_sim.optimizer import apso_optimize, compute_fitness
from chsr_sim.physics import calculate_sinr

walls = gen_walls()
density = generate_human_density(t=0)

# Dummy initial routers (e.g., center of the grid)
initial_routers = [{'x': 16, 'y': 10, 'z': 2.5, 'phi': 0, 'alpha': 60, 'power': ROUTER_POWER} for _ in range(7)]

# Compile JIT
calculate_sinr(initial_routers, density, walls)

start_time = time.time()
# Run tier 4 (full 3D) for a fair comparison against greedy which places anywhere
optimized_routers = apso_optimize(initial_routers, density, walls, tier=4, prev_routers=initial_routers)
end_time = time.time()

sinr_map, coverage = calculate_sinr(optimized_routers, density, walls)
fitness = compute_fitness(optimized_routers, density, walls, initial_routers)

print(f"APSO Optimization completed in {end_time - start_time:.2f} seconds.")
print(f"Final APSO Coverage Score: {coverage:.4f}")
print(f"Final APSO Composite Fitness: {fitness:.4f}")
