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
NOISE_DBM = -64  # -174 dBm/Hz + 10log10(10 GHz) + 10 dB noise figure
HUMAN_PENALTY_DB = 20
H_HUMAN = 1.6
Z_U = 1.0 # User height

# Molecular absorption at 300 GHz: 6.68 dB/km for indoor air (23 C, 10 g/m^3 water
# vapour), ITU-R P.676 computed with ITU-Rpy 0.4.0; loss_dB = 4.343 * K_F * d.
# (The earlier value 0.05 1/m corresponds to 217 dB/km and was ~33x too high.)
K_F = 6.677 / (4.343 * 1000.0)
K_F_LEGACY = 0.05

# Azimuth convention: True = compass bearing (0 deg = North = +y, clockwise), as
# used by the MILP layout ("from North").  False reproduces the earlier code,
# which compared compass azimuths with math angles (0 deg = +x, counter-clockwise).
AZIMUTH_COMPASS = True

# Main-lobe gain coupled to the azimuth beamwidth alpha.  The elevation beamwidth is
# fixed (the model works in the horizontal plane), so G = K / (alpha * theta_el) gives
# G(alpha) = G_REF + 10 log10(ALPHA_REF / alpha) dBi, anchored at 60 deg -> 30 dBi.
# False keeps the earlier fixed G_MAX for every beamwidth.
GAIN_COUPLED = True
G_REF = 30.0
ALPHA_REF = 60.0
G_RX = 0.0   # receive antenna gain (dBi)

# Human blockage.  True: saturating model L = L_h * (1 - prod_c (1 - D_h(c) I_c)) over
# the cells crossed by the link.  False: the earlier unbounded sum of D_h(c) * L_h.
BLOCKAGE_SATURATING = True

# Users at cell centres (x + 0.5, y + 0.5).  False puts them at the integer cell
# corners as before, which places some users on top of walls (x = 0, y = 10, y = 12).
CELL_CENTRES = True

# Ray height along the link.  True: measured from the user end (Eq. 6 of the paper).
# False reproduces the earlier code, which measured it from the AP end.
RAY_FROM_USER = True

# Human Density Config
COUNT_CIRCLE = 9
RADIUS = 2.0

# Router Power Config
ROUTER_POWER = 1.0  # Multiplier from 0.0 to 1.0 (max power)

# Swarm Constraints
CANDIDATE_Z = np.round(np.arange(2.0, 3.0 + 1e-9, 0.2), 1)  # 2.0..3.0 m (arange(2.0, 3.2, 0.2) also produced 3.2 m, above the 3 m ceiling)
CANDIDATE_ALPHA = np.array([30, 45, 60, 75, 90, 120])
CANDIDATE_PHI = np.arange(0, 360, 45)
TARGET_COVERAGE = 0.90
SINR_TH = 5

# Optimizer Constraints
NUM_PARTICLES = 50          # Swarm size S (TeraMove paper, Sec. V)
APSO_ITERS = 20             # Iterations T per tier (TeraMove paper, Sec. V)
MIN_ROUTER_DIST = 3.0       # Minimum 2D distance between routers (meters)
MOVEMENT_BETA = 0.25        # Movement penalty weight
CLUSTER_GAMMA = 0.3         # Anti-clustering penalty weight
CELL_WEIGHT = 0.4           # Weight for cell count objective
DENSITY_WEIGHT = 0.6        # Weight for density sum objective
BONUS = 0.5                 # Fitness bonus B when density-weighted coverage >= TARGET_COVERAGE
RAIL_SPEED = 0.2            # AP actuator speed (m/s), used for actuation time
