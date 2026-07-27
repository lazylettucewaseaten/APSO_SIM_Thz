"""
Interactive human placement tool using matplotlib.

Left-click:  Place a human at that position (with current radius).
Right-click: Remove the nearest placed human.
Slider:      Adjust the radius for the NEXT placed human.
Done button: Close the window and return the placed points.
"""

import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.widgets import Slider, Button
from .config import LENGTH, BREADTH, RADIUS


def _draw_walls(ax, walls):
    """Draw all walls on the given axes."""
    for w in walls:
        if w['m'] == 'solid':
            c = '#555555'
        elif w['m'] == 'wood':
            c = '#8b4513' if w['h'] >= 3.0 else '#d2b48c'
        else:
            c = '#87ceeb'

        alpha = 1.0 if w['m'] != 'glass' else 0.5
        if w['o'] == 'h':
            ax.add_patch(patches.Rectangle(
                (w['s'], w['p'] - 0.2), w['e'] - w['s'], 0.4,
                facecolor=c, alpha=alpha, edgecolor='black', linewidth=0.5))
        else:
            ax.add_patch(patches.Rectangle(
                (w['p'] - 0.2, w['s']), 0.4, w['e'] - w['s'],
                facecolor=c, alpha=alpha, edgecolor='black', linewidth=0.5))


def _redraw(ax, walls, points, title_text):
    """Clear and redraw the room with current human placements."""
    ax.clear()
    ax.set_xlim(0, LENGTH)
    ax.set_ylim(0, BREADTH)
    ax.set_facecolor('#f5f5f5')
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_title(title_text)
    ax.set_aspect('equal')
    ax.grid(True, linestyle=':', alpha=0.4)

    _draw_walls(ax, walls)

    # Draw each human as a filled circle showing radius + center marker
    for pt in points:
        circle = plt.Circle((pt['x'], pt['y']), pt['radius'],
                            color='red', alpha=0.25, zorder=2)
        ax.add_patch(circle)
        ax.plot(pt['x'], pt['y'], 'r+', markersize=8, markeredgewidth=2, zorder=3)
        ax.annotate(f"r={pt['radius']:.1f}", (pt['x'], pt['y']),
                    textcoords="offset points", xytext=(5, 5),
                    fontsize=7, color='darkred')

    ax.figure.canvas.draw_idle()


def interactive_place_humans(walls, default_radius=None):
    """
    Open an interactive matplotlib window to place humans on the room layout.

    Parameters
    ----------
    walls : list
        Wall definitions from gen_walls().
    default_radius : float, optional
        Starting radius value for the slider. Defaults to config.RADIUS.

    Returns
    -------
    points : list of dict
        Each dict has keys 'x', 'y', 'radius'.
    """
    if default_radius is None:
        default_radius = RADIUS

    points = []
    current_radius = [default_radius]  # mutable container for closure

    fig, ax = plt.subplots(figsize=(12, 8))
    plt.subplots_adjust(bottom=0.22)

    title_base = ("Left-click: place human | Right-click: remove nearest | "
                  "Adjust radius below | Click 'Done' when finished")
    _redraw(ax, walls, points, title_base)

    # --- Radius slider ---
    ax_slider = plt.axes([0.20, 0.08, 0.45, 0.03])
    slider = Slider(ax_slider, 'Radius (m)', 0.5, 8.0,
                    valinit=default_radius, valstep=0.5)

    def on_slider(val):
        current_radius[0] = val

    slider.on_changed(on_slider)

    # --- Done button ---
    ax_button = plt.axes([0.75, 0.07, 0.12, 0.05])
    btn_done = Button(ax_button, 'Done', color='lightgreen', hovercolor='green')

    def on_done(event):
        plt.close(fig)

    btn_done.on_clicked(on_done)

    # --- Click handler ---
    def on_click(event):
        # Ignore clicks outside the main axes or on widgets
        if event.inaxes != ax:
            return

        x, y = event.xdata, event.ydata
        if x is None or y is None:
            return

        # Clamp to room bounds
        x = np.clip(x, 0, LENGTH)
        y = np.clip(y, 0, BREADTH)

        if event.button == 1:  # Left click — place
            points.append({'x': float(x), 'y': float(y),
                           'radius': float(current_radius[0])})
            _redraw(ax, walls, points,
                    f"{len(points)} humans placed | {title_base}")

        elif event.button == 3:  # Right click — remove nearest
            if not points:
                return
            dists = [np.sqrt((p['x'] - x)**2 + (p['y'] - y)**2) for p in points]
            nearest = int(np.argmin(dists))
            points.pop(nearest)
            _redraw(ax, walls, points,
                    f"{len(points)} humans placed | {title_base}")

    fig.canvas.mpl_connect('button_press_event', on_click)

    plt.show()  # Blocks until window closed

    print(f"Placed {len(points)} humans interactively.")
    return points


def generate_density_from_interactive_points(points):
    """
    Build a density grid from interactively placed points.
    Each point has its own radius (not the global config RADIUS).

    Parameters
    ----------
    points : list of dict
        Each dict has 'x', 'y', 'radius'.

    Returns
    -------
    density : np.ndarray of shape (LENGTH, BREADTH)
    """
    density = np.zeros((LENGTH, BREADTH))
    for pt in points:
        hx, hy, r = pt['x'], pt['y'], pt['radius']
        for x in range(LENGTH):
            for y in range(BREADTH):
                d = np.sqrt((x - hx)**2 + (y - hy)**2)
                if d < r:
                    density[x, y] = max(density[x, y], 1.0 - d / r)
    return density
