from chsr_sim.config import TARGET_COVERAGE
from chsr_sim.environment import gen_walls, generate_human_density
from chsr_sim.physics import calculate_sinr
from chsr_sim.optimizer import apso_optimize
from chsr_sim.visualization import plot_environment, plot_room_scenario
import matplotlib.pyplot as plt

def main():
    print("Starting Modular CHSR Simulation...")
    walls = gen_walls()
    
    routers = [
        {'x': 5, 'y': 5, 'z': 2.4, 'phi': 0, 'alpha': 60},
        {'x': 15, 'y': 5, 'z': 2.4, 'phi': 90, 'alpha': 60},
        {'x': 25, 'y': 5, 'z': 2.4, 'phi': 180, 'alpha': 60},
        {'x': 5, 'y': 15, 'z': 2.4, 'phi': 270, 'alpha': 60},
        {'x': 15, 'y': 15, 'z': 2.4, 'phi': 45, 'alpha': 60},
        {'x': 25, 'y': 15, 'z': 2.4, 'phi': 135, 'alpha': 60},
        {'x': 10, 'y': 10, 'z': 2.4, 'phi': 0, 'alpha': 120}
    ]
    
    time_steps = 3
    coverages = []
    
    for t in range(time_steps):
        print(f"\n--- Time Step {t} ---")
        human_density = generate_human_density(t)
        sinr_map, cov = calculate_sinr(routers, human_density, walls)
        print(f"  Initial Coverage: {cov*100:.1f}%")
        
        if cov < TARGET_COVERAGE:
            r_t12 = apso_optimize(routers, human_density, walls, tier=2)
            _, cov_t12 = calculate_sinr(r_t12, human_density, walls)
            if cov_t12 >= TARGET_COVERAGE:
                routers, cov = r_t12, cov_t12
            else:
                r_t3 = apso_optimize(r_t12, human_density, walls, tier=3)
                _, cov_t3 = calculate_sinr(r_t3, human_density, walls)
                if cov_t3 >= TARGET_COVERAGE:
                    routers, cov = r_t3, cov_t3
                else:
                    r_t4 = apso_optimize(r_t3, human_density, walls, tier=4)
                    _, cov_t4 = calculate_sinr(r_t4, human_density, walls)
                    routers, cov = r_t4, cov_t4
        
        sinr_map, cov = calculate_sinr(routers, human_density, walls)
        coverages.append(cov)
        plot_environment(sinr_map, routers, human_density, walls, t, cov)

    plt.figure(figsize=(8,4))
    plt.plot(range(time_steps), [c*100 for c in coverages], marker='o')
    plt.axhline(y=TARGET_COVERAGE*100, color='r', linestyle='--')
    plt.savefig('coverage_over_time.png')
    print("Done")

if __name__ == "__main__":
    main()
