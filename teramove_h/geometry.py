"""Floor plan, rooms, initial deployments and the azimuth convention.

Azimuth convention (fixes legacy defect D1): every azimuth in this package is a
*compass bearing* in degrees, 0 = North = +y axis, increasing clockwise
(90 = East = +x).  This is the convention of the MILP paper (Table II, "from
North").  Internally, trigonometry uses the mathematical angle
(0 = +x, counter-clockwise); convert only through the two helpers below.
"""
import math

import numpy as np

from chsr_sim.environment import gen_walls  # legacy floor plan, reused verbatim

MATERIAL_CODE = {"solid": 0, "wood": 1, "glass": 2}


def compass_to_math(bearing_deg):
    return (90.0 - np.asarray(bearing_deg, dtype=float)) % 360.0


def math_to_compass(angle_deg):
    return (90.0 - np.asarray(angle_deg, dtype=float)) % 360.0


def bearing_deg(dx, dy):
    """Compass bearing of the vector (dx, dy)."""
    return math.degrees(math.atan2(dx, dy)) % 360.0


def walls_array():
    """Walls as float array: [orient(0=h,1=v), pos, start, end, height, material]."""
    ws = gen_walls()
    arr = np.zeros((len(ws), 6))
    for i, w in enumerate(ws):
        arr[i] = (0.0 if w["o"] == "h" else 1.0, w["p"], w["s"], w["e"], w["h"],
                  MATERIAL_CODE[w["m"]])
    return arr


WALLS = walls_array()

# Rooms bounded by full-height (3 m) walls of gen_walls(): (x0, x1, y0, y1).
ROOMS = np.array([
    [0, 3, 0, 5],       # R0  small room, bottom-left
    [0, 3, 5, 10],      # R1  small room
    [3, 16, 0, 10],     # R2  large room, bottom-left (cubicles)
    [16, 29, 0, 10],    # R3  large room, bottom-right (cubicles)
    [29, 32, 0, 5],     # R4  small room, bottom-right
    [29, 32, 5, 10],    # R5  small room
    [0, 32, 10, 12],    # R6  corridor
    [0, 4, 12, 16],     # R7  small room, top-left
    [0, 4, 16, 20],     # R8  small room
    [4, 28, 12, 20],    # R9  hall (cubicles)
    [28, 32, 12, 16],   # R10 small room, top-right
    [28, 32, 16, 20],   # R11 small room
], dtype=float)

ROOM_NAMES = [f"R{i}" for i in range(len(ROOMS))]


def room_of(x, y):
    """Index of the room containing (x, y); points on a boundary go to the first match."""
    for i, (x0, x1, y0, y1) in enumerate(ROOMS):
        if x0 <= x <= x1 and y0 <= y <= y1:
            return i
    raise ValueError(f"point ({x}, {y}) is outside the floor plan")


# 14-AP deployment of MILP.pdf Fig. 1: (x, y, z, compass azimuth).  The MILP
# was solved in the earlier work and is not re-run here.
MILP_LAYOUT = np.array([
    [0.5, 19.5, 2.4, 135], [0.5, 15.5, 2.2, 135], [17.5, 18.5, 2.6, 270],
    [28.5, 16.5, 2.2, 45], [28.5, 12.5, 2.8, 45], [0.5, 10.5, 3.0, 45],
    [0.5, 9.5, 2.8, 135], [14.5, 12.5, 3.0, 45], [16.5, 11.5, 2.4, 135],
    [29.5, 9.5, 2.6, 135], [0.5, 4.5, 2.8, 135], [3.5, 0.5, 2.2, 45],
    [16.5, 0.5, 2.4, 45], [29.5, 4.5, 3.0, 135],
], dtype=float)
MILP_ALPHA_DEG = 60.0   # beamwidth of the TeraMove initial layout (main.py)

# Fixed ceiling Wi-Fi APs: centres of the large lower rooms R2 and R3, and two in the hall R9.
WIFI_POSITIONS = np.array([
    [9.5, 5.0, 3.0], [22.5, 5.0, 3.0], [10.0, 16.0, 3.0], [22.0, 16.0, 3.0],
], dtype=float)


def cell_centres(length=32, breadth=20):
    """Centres of the 1 m grid cells, shape (length*breadth, 2), x-major order."""
    xs, ys = np.meshgrid(np.arange(length) + 0.5, np.arange(breadth) + 0.5, indexing="ij")
    return np.column_stack([xs.ravel(), ys.ravel()])


def segment_distance(px, py, w):
    """Euclidean distance from point (px, py) to wall segment w (row of WALLS)."""
    orient, pos, s, e = w[0], w[1], w[2], w[3]
    if orient == 0:      # horizontal: y = pos, x in [s, e]
        cx = min(max(px, s), e)
        return math.hypot(px - cx, py - pos)
    cy = min(max(py, s), e)
    return math.hypot(px - pos, py - cy)
