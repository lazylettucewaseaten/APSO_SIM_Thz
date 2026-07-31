from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import time
import subprocess
import os
from typing import List, Dict, Any
import uvicorn
import numpy as np

from chsr_sim.config import TARGET_COVERAGE, LENGTH, BREADTH
from chsr_sim.environment import gen_walls, generate_density_from_points
from chsr_sim.physics import calculate_sinr
from chsr_sim.optimizer import apso_optimize, hungarian_reassign, compute_total_movement

app = FastAPI(title="APSO_SIM_Thz Dashboard API")

os.makedirs("output_interactive", exist_ok=True)
app.mount("/static_root", StaticFiles(directory="."), name="static_root")
app.mount("/static_interactive", StaticFiles(directory="output_interactive"), name="static_interactive")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from typing import List, Dict, Any, Optional

class RunRequest(BaseModel):
    steps: int = 3


class Point(BaseModel):
    x: int
    y: int

class RouterState(BaseModel):
    x: float
    y: float
    z: float
    phi: float
    alpha: float
    power: float

class SimulationRequest(BaseModel):
    points: List[Point]
    routers: Optional[List[RouterState]] = None

# Default static initial routers
DEFAULT_ROUTERS = [
    {'x': 5, 'y': 5, 'z': 2.4, 'phi': 0, 'alpha': 60, 'power': 1.0},
    {'x': 15, 'y': 5, 'z': 2.4, 'phi': 90, 'alpha': 60, 'power': 1.0},
    {'x': 25, 'y': 5, 'z': 2.4, 'phi': 180, 'alpha': 60, 'power': 1.0},
    {'x': 5, 'y': 15, 'z': 2.4, 'phi': 270, 'alpha': 60, 'power': 1.0},
    {'x': 15, 'y': 15, 'z': 2.4, 'phi': 45, 'alpha': 60, 'power': 1.0},
    {'x': 25, 'y': 15, 'z': 2.4, 'phi': 135, 'alpha': 60, 'power': 1.0},
    {'x': 10, 'y': 10, 'z': 2.4, 'phi': 0, 'alpha': 120, 'power': 1.0}
]

walls = gen_walls()

@app.get("/environment")
def get_environment():
    return {
        "length": LENGTH,
        "breadth": BREADTH,
        "walls": walls,
        "routers": DEFAULT_ROUTERS
    }

@app.post("/simulate")
def simulate(req: SimulationRequest):
    pts = [{"x": p.x, "y": p.y} for p in req.points]
    
    # 1. Generate human density from given points
    human_density = generate_density_from_points(pts)
    
    if req.routers:
        original_routers = [r.dict() for r in req.routers]
        routers = [r.dict() for r in req.routers]
    else:
        original_routers = [dict(r) for r in DEFAULT_ROUTERS]
        routers = [dict(r) for r in DEFAULT_ROUTERS]
    
    start_time = time.time()
    
    # Calculate coverage before
    sinr_map_before, cov_before = calculate_sinr(routers, human_density, walls)
    initial_cov = cov_before
    
    # APSO optimization tiers
    if initial_cov < TARGET_COVERAGE:
        # Tier 2
        r_t12 = apso_optimize(routers, human_density, walls, tier=2, prev_routers=original_routers)
        _, cov_t12 = calculate_sinr(r_t12, human_density, walls)
        if cov_t12 >= TARGET_COVERAGE:
            routers = hungarian_reassign(original_routers, r_t12)
            cov = cov_t12
        else:
            # Tier 3
            r_t3 = apso_optimize(r_t12, human_density, walls, tier=3, prev_routers=original_routers)
            _, cov_t3 = calculate_sinr(r_t3, human_density, walls)
            if cov_t3 >= TARGET_COVERAGE:
                routers = hungarian_reassign(original_routers, r_t3)
                cov = cov_t3
            else:
                # Tier 4
                r_t4 = apso_optimize(r_t3, human_density, walls, tier=4, prev_routers=original_routers)
                _, cov_t4 = calculate_sinr(r_t4, human_density, walls)
                routers = hungarian_reassign(original_routers, r_t4)
                cov = cov_t4
    
    end_time = time.time()
    opt_time = end_time - start_time
    
    # Re-calculate post movement
    move = compute_total_movement(original_routers, routers)
    sinr_map_after, cov_after = calculate_sinr(routers, human_density, walls)
    reach_inc = (cov_after - initial_cov) * 100

    # Ensure json serializable by converting numpy array directly to list-of-lists, ignoring NaN/Inf safely if needed
    sinr_map_after_list = np.nan_to_num(sinr_map_after, nan=-100.0, neginf=-100.0, posinf=100.0).tolist()
    density_list = human_density.tolist()

    return {
        "status": "success",
        "initial_coverage": float(initial_cov * 100),
        "final_coverage": float(cov_after * 100),
        "reachability_increase": float(reach_inc),
        "optimization_time": float(opt_time),
        "total_movement": float(move),
        "routers": [{k: float(v) if isinstance(v, (float, np.floating)) else int(v) if isinstance(v, (int, np.integer)) else v for k, v in r.items()} for r in routers],
        "sinr_map": sinr_map_after_list,
        "density_map": density_list
    }

@app.post("/run/random")
def run_random(req: RunRequest):
    subprocess.run(["python3", "main.py", "--steps", str(req.steps)], check=True)
    return {"status": "success", "mode": "random", "steps": req.steps}

@app.post("/run/manual")
def run_manual(req: RunRequest):
    subprocess.run(["python3", "main2.py", "--steps", str(req.steps)], check=True)
    return {"status": "success", "mode": "manual", "steps": req.steps}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
