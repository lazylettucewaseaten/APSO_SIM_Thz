from chsr_sim.config import TARGET_COVERAGE
from chsr_sim.environment import gen_walls, generate_human_density
from chsr_sim.physics import calculate_sinr
from chsr_sim.optimizer import apso_optimize, hungarian_reassign, compute_total_movement
from chsr_sim.visualization import plot_environment, plot_room_scenario, plot_density_map, plot_ap_placement, plot_sinr_map
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
    movements = []
    reachability_increases = []
    
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
    
    print("\nDone")

if __name__ == "__main__":
    main()
