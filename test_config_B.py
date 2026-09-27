import sys
from chsr_sim import config
config.CELL_WEIGHT = 0.4
config.DENSITY_WEIGHT = 0.6
config.MOVEMENT_BETA = 0.15
config.CLUSTER_GAMMA = 0.3

import chsr_sim.optimizer
chsr_sim.optimizer.CELL_WEIGHT = config.CELL_WEIGHT
chsr_sim.optimizer.DENSITY_WEIGHT = config.DENSITY_WEIGHT
chsr_sim.optimizer.MOVEMENT_BETA = config.MOVEMENT_BETA
chsr_sim.optimizer.CLUSTER_GAMMA = config.CLUSTER_GAMMA

import numpy as np
# Set random seed to ensure reproducibility
np.random.seed(42)

from main import main
main()
