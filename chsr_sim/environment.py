import numpy as np
from .config import LENGTH, BREADTH

def gen_walls():
    ws = []
    def aw(o, p, s, e, m, h=3.0):
        ws.append({'o': o, 'p': p, 's': s, 'e': e, 'm': m, 'h': h})

    aw('h', 0, 0, 32, 'solid')
    aw('h', 20, 0, 32, 'solid')
    aw('v', 0, 0, 20, 'solid')
    aw('v', 32, 0, 20, 'solid')
    aw('v', 3, 0, 4, 'glass')
    aw('v', 3, 4, 6, 'wood')
    aw('v', 3, 6, 10, 'glass')
    aw('v', 4, 12, 15, 'glass')
    aw('v', 4, 15, 17, 'wood')
    aw('v', 4, 17, 20, 'glass')
    aw('v', 29, 0, 4, 'glass')
    aw('v', 29, 4, 6, 'wood')
    aw('v', 29, 6, 10, 'glass')
    aw('v', 28, 12, 15, 'glass')
    aw('v', 28, 15, 17, 'wood')
    aw('v', 28, 17, 20, 'glass')
    aw('h', 5, 0, 3, 'solid')
    aw('h', 16, 0, 4, 'solid')
    aw('h', 5, 29, 32, 'solid')
    aw('h', 16, 28, 32, 'solid')
    aw('h', 10, 0, 6, 'solid')
    aw('h', 10, 6, 8, 'wood')
    aw('h', 10, 8, 12, 'solid')
    aw('h', 10, 12, 14, 'wood')
    aw('h', 10, 14, 18, 'solid')
    aw('h', 10, 18, 20, 'wood')
    aw('h', 10, 20, 24, 'solid')
    aw('h', 10, 24, 26, 'wood')
    aw('h', 10, 26, 32, 'solid')
    aw('h', 12, 0, 6, 'solid')
    aw('h', 12, 6, 8, 'wood')
    aw('h', 12, 8, 10, 'solid')
    aw('h', 12, 10, 12, 'wood')
    aw('h', 12, 12, 20, 'solid')
    aw('h', 12, 20, 22, 'wood')
    aw('h', 12, 22, 24, 'solid')
    aw('h', 12, 24, 26, 'wood')
    aw('h', 12, 26, 32, 'solid')
    aw('v', 16, 0, 10, 'solid')
    aw('v', 12, 2, 8, 'wood', 1.0)
    aw('h', 4, 10, 14, 'wood', 1.0)
    aw('h', 6, 10, 14, 'wood', 1.0)
    aw('v', 20, 2, 8, 'wood', 1.0)
    aw('h', 4, 18, 22, 'wood', 1.0)
    aw('h', 6, 18, 22, 'wood', 1.0)
    aw('v', 7, 2, 8, 'wood', 1.0)
    aw('h', 4, 5, 9, 'wood', 1.0)
    aw('h', 6, 5, 9, 'wood', 1.0)
    aw('v', 25, 2, 8, 'wood', 1.0)
    aw('h', 4, 23, 27, 'wood', 1.0)
    aw('h', 6, 23, 27, 'wood', 1.0)
    aw('h', 16, 8, 12, 'wood', 1.0)
    aw('v', 10, 14, 18, 'wood', 1.0)
    aw('h', 16, 14, 18, 'wood', 1.0)
    aw('v', 16, 14, 18, 'wood', 1.0)
    aw('h', 16, 20, 24, 'wood', 1.0)
    aw('v', 22, 14, 18, 'wood', 1.0)
    return ws

def generate_human_density(t):
    density = np.zeros((LENGTH, BREADTH))
    num_hotspots = 3
    for h in range(num_hotspots):
        hx = int(LENGTH/2 + 10 * np.sin(t*0.5 + h*2))
        hy = int(BREADTH/2 + 8 * np.cos(t*0.5 + h*2))
        for x in range(LENGTH):
            for y in range(BREADTH):
                d = np.sqrt((x-hx)**2 + (y-hy)**2)
                if d < 5:
                    density[x, y] = max(density[x,y], 1.0 - d/5.0)
    return density
