import numpy as np

# Simulation Constants
LENGTH = 32
BREADTH = 20
GRID_RES = 1
F_GHZ = 300
C = 3e8
F_HZ = F_GHZ * 1e9
PTX_DBM = 20
G_MAX = 30
NOISE_DBM = -94
HUMAN_PENALTY_DB = 20
H_HUMAN = 1.6
Z_U = 1.0 # User height

K_F = 0.0033 # Absorption for 300 GHz

# Swarm Constraints
CANDIDATE_Z = np.arange(2.0, 3.2, 0.2)
CANDIDATE_ALPHA = np.array([30, 45, 60, 75, 90, 120])
CANDIDATE_PHI = np.arange(0, 360, 45)
TARGET_COVERAGE = 0.95
SINR_TH = 5

# Optimizer Constraints
MIN_ROUTER_DIST = 3.0       # Minimum 2D distance between routers (meters)
MOVEMENT_BETA = 0.15        # Movement penalty weight
CLUSTER_GAMMA = 0.3         # Anti-clustering penalty weight
CELL_WEIGHT = 0.4           # Weight for cell count objective
DENSITY_WEIGHT = 0.6        # Weight for density sum objective
