import numpy as np
from scipy.optimize import linear_sum_assignment
from .config import *
from .physics import calculate_sinr


# AP positions stay inside the building, 0.25 m from the outer walls.  (The earlier
# bounds [0, LENGTH-1] x [0, BREADTH-1] moved APs mounted at y = 19.5 m by 0.5 m.)
WALL_MARGIN = 0.25
X_LO, X_HI = WALL_MARGIN, LENGTH - WALL_MARGIN
Y_LO, Y_HI = WALL_MARGIN, BREADTH - WALL_MARGIN


def snap_phi(phi_raw, candidates):
    """Snap to nearest candidate angle using circular distance."""
    phi_raw = phi_raw % 360
    dists = np.minimum(np.abs(candidates - phi_raw), 360 - np.abs(candidates - phi_raw))
    return candidates[np.argmin(dists)]


def decode_routers(pos, n_routers, original_routers=None):
    """Decode a flat position vector into a list of router dicts."""
    routers = []
    for i in range(n_routers):
        x = np.clip(pos[i*5 + 0], X_LO, X_HI)
        y = np.clip(pos[i*5 + 1], Y_LO, Y_HI)
        z = CANDIDATE_Z[np.argmin(np.abs(CANDIDATE_Z - pos[i*5 + 2]))]
        phi = snap_phi(pos[i*5 + 3], CANDIDATE_PHI)
        alpha = CANDIDATE_ALPHA[np.argmin(np.abs(CANDIDATE_ALPHA - pos[i*5 + 4]))]
        r = {'x': x, 'y': y, 'z': z, 'phi': phi, 'alpha': alpha}
        if original_routers is not None:
            r['power'] = original_routers[i].get('power', ROUTER_POWER)
        routers.append(r)
    return routers


def compute_fitness(test_routers, human_density, walls, prev_routers):
    """
    Composite fitness:
      F = w1*cell_ratio + w2*density_ratio + bonus - beta*movement - gamma*clustering
    """
    sinr_map, _ = calculate_sinr(test_routers, human_density, walls)
    covered_mask = sinr_map >= SINR_TH

    # Objective 1: maximize number of covered cells
    cell_ratio = np.sum(covered_mask) / (LENGTH * BREADTH)

    # Objective 2: maximize sum of densities in covered cells
    total_density = np.sum(human_density)
    if total_density > 0:
        density_ratio = np.sum(human_density[covered_mask]) / total_density
    else:
        density_ratio = cell_ratio

    coverage_score = CELL_WEIGHT * cell_ratio + DENSITY_WEIGHT * density_ratio

    # Bonus for meeting target
    if density_ratio >= TARGET_COVERAGE:
        coverage_score += BONUS

    # Movement penalty
    movement_penalty = 0.0
    if prev_routers is not None:
        total_movement = 0.0
        for i in range(len(test_routers)):
            dx = test_routers[i]['x'] - prev_routers[i]['x']
            dy = test_routers[i]['y'] - prev_routers[i]['y']
            dz = test_routers[i]['z'] - prev_routers[i]['z']
            total_movement += np.sqrt(dx**2 + dy**2 + dz**2)
        max_possible = len(test_routers) * np.sqrt(LENGTH**2 + BREADTH**2 + 3.0**2)
        movement_penalty = total_movement / max_possible

    # Anti-clustering penalty
    n = len(test_routers)
    cluster_penalty = 0.0
    num_pairs = max(n * (n - 1) / 2.0, 1.0)
    for i in range(n):
        for j in range(i + 1, n):
            dist = np.sqrt(
                (test_routers[i]['x'] - test_routers[j]['x'])**2 +
                (test_routers[i]['y'] - test_routers[j]['y'])**2
            )
            if dist < MIN_ROUTER_DIST:
                cluster_penalty += (MIN_ROUTER_DIST - dist) / MIN_ROUTER_DIST
    cluster_penalty /= num_pairs

    return coverage_score - MOVEMENT_BETA * movement_penalty - CLUSTER_GAMMA * cluster_penalty


def hungarian_reassign(prev_routers, new_routers):
    """Optimally assign new positions to existing routers to minimize total displacement."""
    n = len(prev_routers)
    cost = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            cost[i, j] = np.sqrt(
                (prev_routers[i]['x'] - new_routers[j]['x'])**2 +
                (prev_routers[i]['y'] - new_routers[j]['y'])**2 +
                (prev_routers[i]['z'] - new_routers[j]['z'])**2
            )
    _, col_ind = linear_sum_assignment(cost)
    assigned = []
    for i, j in enumerate(col_ind):
        r = dict(new_routers[j])
        if 'power' in prev_routers[i]:
            r['power'] = prev_routers[i]['power']
        assigned.append(r)
    return assigned


def compute_total_movement(prev_routers, new_routers):
    """Compute total Euclidean displacement across all routers."""
    total = 0.0
    for i in range(len(prev_routers)):
        dx = new_routers[i]['x'] - prev_routers[i]['x']
        dy = new_routers[i]['y'] - prev_routers[i]['y']
        dz = new_routers[i]['z'] - prev_routers[i]['z']
        total += np.sqrt(dx**2 + dy**2 + dz**2)
    return total


def apso_optimize(routers, human_density, walls, tier, prev_routers=None,
                  iters=None, seed_near=True, history=None, verbose=True, include_current=True,
                  seed_routers=None):
    """
    APSO with composite fitness, movement penalty, anti-clustering, and velocity clamping.

    Optional arguments (defaults reproduce the original behaviour):
      iters      number of iterations (default APSO_ITERS)
      seed_near  Tier 4 seeds one third of the swarm near the current positions;
                 False gives the uniform initialisation of a standard PSO
      history    list that receives the global-best fitness after each iteration
      include_current  particle 0 is the current configuration, so the returned
                 configuration is never worse (in fitness) than the input
      seed_routers  Tier 4 only: particle 1 starts at this configuration (e.g. the
                 crowd-aware greedy layout of chsr_sim.greedy_seed)
    """
    if verbose:
        print(f"    Running APSO Optimization Tier {tier}...")
    num_particles = NUM_PARTICLES
    iters = APSO_ITERS if iters is None else iters

    best_global_pos = None
    best_global_score = -float('inf')

    n_routers = len(routers)
    dim = n_routers * 5

    # Per-dimension velocity limits
    v_max = np.zeros(dim)
    for i in range(n_routers):
        v_max[i*5 + 0] = LENGTH * 0.1
        v_max[i*5 + 1] = BREADTH * 0.1
        v_max[i*5 + 2] = 0.4
        v_max[i*5 + 3] = 45.0
        v_max[i*5 + 4] = 30.0

    # Initialize swarm
    swarm = []
    for p_idx in range(num_particles):
        p = []
        for r in routers:
            if tier < 4:
                x, y = r['x'], r['y']
            elif seed_near and p_idx < num_particles // 3:
                # Seed 1/3 near current positions
                x = np.clip(r['x'] + np.random.uniform(-2, 2), X_LO, X_HI)
                y = np.clip(r['y'] + np.random.uniform(-2, 2), Y_LO, Y_HI)
            else:
                x = np.random.uniform(X_LO, X_HI)
                y = np.random.uniform(Y_LO, Y_HI)

            z = r['z'] if tier < 3 else np.random.choice(CANDIDATE_Z)
            phi = np.random.choice(CANDIDATE_PHI)
            alpha = np.random.choice(CANDIDATE_ALPHA)
            p.extend([x, y, z, phi, alpha])

        pos = np.array(p, dtype=float)
        if include_current and p_idx == 0:
            pos = np.array([v for r in routers for v in (r['x'], r['y'], r['z'], r['phi'], r['alpha'])],
                           dtype=float)
        if seed_routers is not None and tier >= 4 and p_idx == 1:
            pos = np.array([v for r in seed_routers for v in (r['x'], r['y'], r['z'], r['phi'], r['alpha'])],
                           dtype=float)
        swarm.append({
            'pos': pos,
            'vel': np.random.uniform(-0.1, 0.1, dim) * v_max,
            'best_pos': pos.copy(),
            'best_score': -float('inf')
        })

    for it in range(iters):
        for particle in swarm:
            test_routers = decode_routers(particle['pos'], n_routers, routers)
            score = compute_fitness(test_routers, human_density, walls, prev_routers)

            if score > particle['best_score']:
                particle['best_score'] = score
                particle['best_pos'] = particle['pos'].copy()

            if score > best_global_score:
                best_global_score = score
                best_global_pos = particle['pos'].copy()
        if history is not None:
            history.append(best_global_score)

        # Velocity and position update
        w = 0.9 - 0.5 * (it / iters)
        c1, c2 = 1.5, 1.5
        for particle in swarm:
            r1 = np.random.rand(dim)
            r2 = np.random.rand(dim)
            particle['vel'] = (w * particle['vel'] +
                               c1 * r1 * (particle['best_pos'] - particle['pos']) +
                               c2 * r2 * (best_global_pos - particle['pos']))

            # Lock dimensions based on tier
            for i in range(n_routers):
                if tier < 4:
                    particle['vel'][i*5 + 0] = 0
                    particle['vel'][i*5 + 1] = 0
                if tier < 3:
                    particle['vel'][i*5 + 2] = 0

            # Clamp velocities
            particle['vel'] = np.clip(particle['vel'], -v_max, v_max)
            particle['pos'] += particle['vel']

    return decode_routers(best_global_pos, n_routers, routers)
