import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.animation as animation
import copy

from chsr_sim.config import TARGET_COVERAGE, LENGTH, BREADTH, SINR_TH
from chsr_sim.environment import gen_walls, generate_human_density
from chsr_sim.physics import calculate_sinr
from chsr_sim.optimizer import apso_optimize, hungarian_reassign, snap_phi, CANDIDATE_PHI, CANDIDATE_ALPHA, CANDIDATE_Z

def run_simulation_sequence():
    walls = gen_walls()
    
    # 14 Routers Initial Start
    current_routers_t0 = [
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
    
    sequence_data = [] # List of tuples: (human_density, routers_list, is_transition, time_step, hold_sec)
    
    current_routers = copy.deepcopy(current_routers_t0)
    
    # Generate history of states
    for t in range(time_steps):
        print(f"Propagating Time Step {t}...")
        human_density = generate_human_density(t)
        
        # State: Hold initial for t, with current routers
        if t == 0:
            hold_sec = 10.0
        elif t == 1:
            hold_sec = 5.0
        else:
            hold_sec = 1.0
        sequence_data.append((human_density, copy.deepcopy(current_routers), False, t, hold_sec))
        
        _, initial_cov = calculate_sinr(current_routers, human_density, walls)
        print(f" Initial coverage: {initial_cov*100:.2f}%")
        
        # Run optimization
        original_routers = copy.deepcopy(current_routers)
        if initial_cov < TARGET_COVERAGE:
            # Tier 2
            r_temp = apso_optimize(current_routers, human_density, walls, tier=2, prev_routers=original_routers)
            _, cov_temp = calculate_sinr(r_temp, human_density, walls)
            if cov_temp >= TARGET_COVERAGE:
                current_routers = hungarian_reassign(original_routers, r_temp)
            else:
                # Tier 3
                r_temp = apso_optimize(r_temp, human_density, walls, tier=3, prev_routers=original_routers)
                _, cov_temp = calculate_sinr(r_temp, human_density, walls)
                if cov_temp >= TARGET_COVERAGE:
                    current_routers = hungarian_reassign(original_routers, r_temp)
                else:
                    # Tier 4
                    r_temp = apso_optimize(r_temp, human_density, walls, tier=4, prev_routers=original_routers)
                    current_routers = hungarian_reassign(original_routers, r_temp)
                    
        # State: Transition
        num_transition_frames = 20
        for i in range(1, num_transition_frames + 1):
            alpha = i / num_transition_frames
            interp_routers = []
            for r_old, r_new in zip(original_routers, current_routers):
                # Interpolate parameters
                r_i = {}
                for k in r_old.keys():
                    if k in ['phi']:
                        # Shortest circular path for phi
                        diff = (r_new[k] - r_old[k])
                        diff = (diff + 180) % 360 - 180
                        r_i[k] = r_old[k] + diff * alpha
                    else:
                        r_i[k] = r_old[k] + (r_new[k] - r_old[k]) * alpha
                interp_routers.append(r_i)
            sequence_data.append((human_density, interp_routers, True, t, None))
            
        # State: Hold new state for a moment
        if t == 0:
            hold_sec = 5.0
        else:
            hold_sec = 1.0
        sequence_data.append((human_density, copy.deepcopy(current_routers), False, t, hold_sec))
        
    return sequence_data, walls

def create_animation(sequence_data, walls, output_filename="simulation_video.mp4"):
    print(f"Total sequence keyframes: {len(sequence_data)}")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Create dummy image for the colorbar, the actual plot is cleared in animate
    dummy_im = ax.imshow(np.zeros((10, 10)), cmap='viridis', vmin=-10, vmax=30)
    fig.colorbar(dummy_im, ax=ax, label="SINR (dB)")
    
    # Frames to render (we will duplicate hold frames for duration)
    frames_to_render = []
    fps = 15
    
    for (density, routers, is_transition, t, hold_sec) in sequence_data:
        if is_transition:
            frames_to_render.append((density, routers, t))
        else:
            if hold_sec is None: hold_sec = 1.0
            hold_frames = int(fps * hold_sec)
            for _ in range(hold_frames):
                frames_to_render.append((density, routers, t))
                
    print(f"Total frames to render: {len(frames_to_render)}")

    # We update axes in animate function
    def animate(frame_idx):
        if frame_idx % 10 == 0:
            print(f"Rendering frame {frame_idx}/{len(frames_to_render)}")
        
        density, routers, t = frames_to_render[frame_idx]
        
        ax.clear()
        
        # Draw SINR map instead of recalculating if it's too slow? We can just draw density and routers nicely.
        # Actually SINR recalculation is fast enough for 32x20 grid
        sinr_map, cov = calculate_sinr(routers, density, walls)
        
        # Background SINR map
        im = ax.imshow(sinr_map.T, origin='lower', cmap='viridis', vmin=-10, vmax=30)
        
        # Overlay Density
        density_rgba = np.zeros((*density.T.shape, 4))
        density_rgba[density.T > 0] = [1.0, 0.0, 0.0, 0.6]  # Highlight in red
        ax.imshow(density_rgba, origin='lower')
        
        # Walls
        for w in walls:
            if w['m'] == 'solid':
                c = '#555555'
            elif w['m'] == 'wood':
                c = '#8b4513' if w.get('h', 0) >= 3.0 else '#d2b48c'
            else:
                c = '#87ceeb'
            alpha_w = 1.0 if w['m'] != 'glass' else 0.5
            if w['o'] == 'h':
                ax.add_patch(patches.Rectangle((w['s'], w['p']-0.2), w['e']-w['s'], 0.4, facecolor=c, alpha=alpha_w))
            else:
                ax.add_patch(patches.Rectangle((w['p']-0.2, w['s']), 0.4, w['e']-w['s'], facecolor=c, alpha=alpha_w))
                
        # Routers
        for r in routers:
            ax.plot(r['x'], r['y'], 'ko', markersize=6)
            wedge = patches.Wedge((r['x'], r['y']), 3, r['phi'] - r['alpha']/2, r['phi'] + r['alpha']/2, facecolor='black', alpha=0.4, edgecolor='black', zorder=3)
            ax.add_patch(wedge)
            
        ax.set_title(f"Time {t} | SINR Cov (>= {SINR_TH}dB): {cov*100:.1f}%")
        ax.set_xlim(0, LENGTH)
        ax.set_ylim(0, BREADTH)
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Y (m)')

    ani = animation.FuncAnimation(fig, animate, frames=len(frames_to_render), interval=1000/fps, blit=False)
    
    # Save the video
    print(f"Saving to {output_filename}...")
    ani.save(output_filename, fps=fps, extra_args=['-vcodec', 'libx264', '-crf', '18', '-preset', 'fast'])
    print("Done generating video!")

if __name__ == "__main__":
    import os
    if not os.path.exists("chsr_sim"):
        print("Please run this script from the directory containing 'chsr_sim'")
    else:
        seq, walls = run_simulation_sequence()
        create_animation(seq, walls)
