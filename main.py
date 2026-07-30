from chsr_sim.config import TARGET_COVERAGE
from chsr_sim.environment import gen_walls, generate_human_density
from chsr_sim.physics import calculate_sinr
from chsr_sim.optimizer import apso_optimize, hungarian_reassign, compute_total_movement
from chsr_sim.visualization import plot_environment, plot_room_scenario, plot_density_map, plot_ap_placement, plot_sinr_map
import matplotlib.pyplot as plt
import time

def main():
    print("Starting Modular CHSR Simulation...")
    walls = gen_walls()
    
    routers = [
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
    {'x': 29.5, 'y': 4.5, 'z': 3.0, 'phi': 135, 'alpha': 60, 'power': 1.0}
]
    time_steps = 3
    coverages = []
    movements = []
    reachability_increases = []
    optimization_times = []
    
    for t in range(time_steps):
        print(f"\n--- Time Step {t} ---")
        original_routers = [dict(r) for r in routers]
        human_density = generate_human_density(t)
        
        plot_density_map(human_density, walls, t, f"density_t{t}.png")
        
        sinr_map_before, cov_before = calculate_sinr(routers, human_density, walls)
        initial_cov = cov_before
        print(f"  Initial Density Coverage: {cov_before*100:.1f}%")
        
        plot_ap_placement(original_routers, walls, f"AP Placement Time {t} (Before)", f"ap_placement_t{t}_before.png")
        plot_sinr_map(sinr_map_before, walls, f"SINR Time {t} (Before) | Cov: {cov_before*100:.1f}%", f"sinr_t{t}_before.png")
        
        start_time = time.time()
        if initial_cov < TARGET_COVERAGE:
            # Tier 2: beam parameters only (phi, alpha)
            r_t12 = apso_optimize(routers, human_density, walls, tier=2,
                                  prev_routers=original_routers)
            _, cov_t12 = calculate_sinr(r_t12, human_density, walls)
            print(f"  Tier 2 Coverage: {cov_t12*100:.1f}%")
            
            if cov_t12 >= TARGET_COVERAGE:
                routers = hungarian_reassign(original_routers, r_t12)
                cov = cov_t12
            else:
                # Tier 3: + height adjustment (z)
                r_t3 = apso_optimize(r_t12, human_density, walls, tier=3,
                                     prev_routers=original_routers)
                _, cov_t3 = calculate_sinr(r_t3, human_density, walls)
                print(f"  Tier 3 Coverage: {cov_t3*100:.1f}%")
                
                if cov_t3 >= TARGET_COVERAGE:
                    routers = hungarian_reassign(original_routers, r_t3)
                    cov = cov_t3
                else:
                    # Tier 4: full repositioning (x, y)
                    r_t4 = apso_optimize(r_t3, human_density, walls, tier=4,
                                         prev_routers=original_routers)
                    _, cov_t4 = calculate_sinr(r_t4, human_density, walls)
                    print(f"  Tier 4 Coverage: {cov_t4*100:.1f}%")
                    routers = hungarian_reassign(original_routers, r_t4)
                    cov = cov_t4
                    
        end_time = time.time()
        opt_time = end_time - start_time
        optimization_times.append(opt_time)
        print(f"  Optimization Time: {opt_time:.2f} s")
        
        # Log movement
        move = compute_total_movement(original_routers, routers)
        movements.append(move)
        print(f"  Total Router Movement: {move:.2f} m")
        
        sinr_map_after, cov_after = calculate_sinr(routers, human_density, walls)
        coverages.append(cov_after)
        
        reach_inc = (cov_after - initial_cov) * 100
        reachability_increases.append(reach_inc)
        
        plot_ap_placement(routers, walls, f"AP Placement Time {t} (After)", f"ap_placement_t{t}_after.png")
        plot_sinr_map(sinr_map_after, walls, f"SINR Time {t} (After) | Cov: {cov_after*100:.1f}%", f"sinr_t{t}_after.png")
        
        # Original combined plot can still be generated if desired
        plot_environment(sinr_map_after, routers, human_density, walls, t, cov_after)

    # Summary plots: coverage + movement
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    ax1.plot(range(time_steps), [c*100 for c in coverages], marker='o', linewidth=2)
    ax1.axhline(y=TARGET_COVERAGE*100, color='r', linestyle='--', label='Target')
    ax1.set_xlabel('Time Step')
    ax1.set_ylabel('Coverage (%)')
    ax1.set_title('Density Coverage Over Time')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2.bar(range(time_steps), movements, color='steelblue', alpha=0.8)
    ax2.set_xlabel('Time Step')
    ax2.set_ylabel('Total Movement (m)')
    ax2.set_title('Router Movement Per Time Step')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('coverage_over_time.png', dpi=150)
    plt.close()
    
    # 3rd Graph: Scatter plot of Movement vs Reachability Increase
    plt.figure(figsize=(8, 5))
    plt.scatter(movements, reachability_increases, color='purple', s=100, zorder=5)
    for i in range(time_steps):
        plt.annotate(f"t={i}", (movements[i], reachability_increases[i]), textcoords="offset points", xytext=(0,10), ha='center')
    plt.xlabel('Movement (m)')
    plt.ylabel('Reachability Increase (%)')
    plt.title('Increase in Reachability for Each Movement')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig('reachability_vs_movement.png', dpi=150)
    plt.close()
    
    # 4th Graph: Optimization Time vs Time Step
    plt.figure(figsize=(8, 5))
    plt.plot(range(time_steps), optimization_times, marker='s', color='orange', linewidth=2, markersize=8)
    plt.xlabel('Time Step')
    plt.ylabel('Optimization Time (s)')
    plt.title('Algorithm Optimization Time per Time Step')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig('optimization_time.png', dpi=150)
    plt.close()
    
    print("\nDone")

if __name__ == "__main__":
    main()
