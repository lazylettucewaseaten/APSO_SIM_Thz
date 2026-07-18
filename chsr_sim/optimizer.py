import numpy as np
from .config import *
from .physics import calculate_sinr

def apso_optimize(routers, human_density, walls, tier):
    print(f"    Running APSO Optimization Tier {tier}...")
    num_particles = 15
    iters = 10
    
    best_global_pos = None
    best_global_score = -float('inf')
    
    swarm = []
    for _ in range(num_particles):
        p = []
        for r in routers:
            x = r['x'] if tier < 4 else np.random.uniform(0, LENGTH-1)
            y = r['y'] if tier < 4 else np.random.uniform(0, BREADTH-1)
            z = r['z'] if tier < 3 else np.random.choice(CANDIDATE_Z)
            phi = np.random.choice(CANDIDATE_PHI)
            alpha = np.random.choice(CANDIDATE_ALPHA)
            p.extend([x, y, z, phi, alpha])
        swarm.append({'pos': np.array(p), 'vel': np.zeros(len(p)), 'best_pos': np.array(p), 'best_score': -float('inf')})
        
    for it in range(iters):
        for particle in swarm:
            test_routers = []
            for i in range(len(routers)):
                x = np.clip(particle['pos'][i*5+0], 0, LENGTH-1)
                y = np.clip(particle['pos'][i*5+1], 0, BREADTH-1)
                z = CANDIDATE_Z[np.argmin(np.abs(CANDIDATE_Z - particle['pos'][i*5+2]))]
                phi = CANDIDATE_PHI[np.argmin(np.abs(CANDIDATE_PHI - (particle['pos'][i*5+3]%360)))]
                alpha = CANDIDATE_ALPHA[np.argmin(np.abs(CANDIDATE_ALPHA - particle['pos'][i*5+4]))]
                test_routers.append({'x':x, 'y':y, 'z':z, 'phi':phi, 'alpha':alpha})
                
            _, cov = calculate_sinr(test_routers, human_density, walls)
            score = cov 
            if cov >= TARGET_COVERAGE:
                score += 1.0
                
            if score > particle['best_score']:
                particle['best_score'] = score
                particle['best_pos'] = particle['pos'].copy()
                
            if score > best_global_score:
                best_global_score = score
                best_global_pos = particle['pos'].copy()
                
        w = 0.9 - 0.5 * (it / iters)
        c1, c2 = 1.5, 1.5
        for particle in swarm:
            r1, r2 = np.random.rand(len(particle['pos'])), np.random.rand(len(particle['pos']))
            particle['vel'] = w * particle['vel'] + c1 * r1 * (particle['best_pos'] - particle['pos']) + c2 * r2 * (best_global_pos - particle['pos'])
            
            if tier < 4:
                for i in range(len(routers)):
                    particle['vel'][i*5+0] = 0
                    particle['vel'][i*5+1] = 0
            if tier < 3:
                for i in range(len(routers)):
                    particle['vel'][i*5+2] = 0
            
            particle['pos'] += particle['vel']
            
    res = []
    for i in range(len(routers)):
        x = np.clip(best_global_pos[i*5+0], 0, LENGTH-1)
        y = np.clip(best_global_pos[i*5+1], 0, BREADTH-1)
        z = CANDIDATE_Z[np.argmin(np.abs(CANDIDATE_Z - best_global_pos[i*5+2]))]
        phi = CANDIDATE_PHI[np.argmin(np.abs(CANDIDATE_PHI - (best_global_pos[i*5+3]%360)))]
        alpha = CANDIDATE_ALPHA[np.argmin(np.abs(CANDIDATE_ALPHA - best_global_pos[i*5+4]))]
        res.append({'x':x, 'y':y, 'z':z, 'phi':phi, 'alpha':alpha})
    return res
