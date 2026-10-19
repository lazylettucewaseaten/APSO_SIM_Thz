# Edits to the TeraMove paper (2026-10-19)

Line numbers refer to the current `teramove_paper/main.tex`.
The paper compiles to 6 pages. `main.tex` already had uncommitted changes before
these edits, so `git diff HEAD -- main.tex` shows both together; this file lists only
the edits made here.

## 1. Requested changes

### 1.1 Figures: larger fonts, ticks in steps of 2
Script: `teramove_eval/make_short_assets.py`. Output is written to
`TeraHertz-short/figures/` and copied to the new folder
`teramove_paper/APSO_Results_ICC/`, so `main.tex` compiles as is.

- Global font sizes raised (base 8 -> 9 pt, ticks 7 -> 8 pt, legend 6.5 -> 7.5 pt).
- **Fig. 1** (`thz_sinr_heatmap.pdf`): redrawn at column width so fonts print at size;
  x/y ticks every 2 m; axis labels `x (m)`, `y (m)`; the "Deployed AP" legend is
  replaced by "(triangles: APs)" in the caption (line 308).
  The original plotting script is not in the repo, and the current simulator gives a
  different map, so the SINR values were read back from the original figure image and
  saved in `teramove_eval/results_short/fig1_sinr.json`. The content of the plot is
  unchanged.
- **Fig. 2** (six panels `fig2a`-`fig2f`): x/y ticks every 2 m (the y axis previously
  showed 2.5, 7.5, 12.5, ...); x tick labels rotated 90 degrees so they do not overlap;
  every panel now has the same axes size, so (a) and (e) no longer print larger.
- **Fig. 3** (`fig3_coverage_density.pdf`): larger fonts; legend label "HPSO (TeraMove)"
  -> "TeraMove"; shorter legend labels (two rows); x-axis label
  "Crowd level (number of clusters)".

### 1.2 Replace HPSO with TeraMove
All occurrences of "HPSO" replaced. Where HPSO was used as the algorithm's name or
definition, the sentence was adjusted:

| Line | Before | After |
|---|---|---|
| 52 | "a 4-tier HPSO framework adapts the network" | "a 4-tier cascade adapts the network" |
| 62 | "An HPSO algorithm for dynamic repositioning" | "A tier-constrained PSO algorithm for dynamic repositioning" |
| 147 | "adapt them with a 4-tier HPSO (Section IV-C)" | "adapt them with a 4-tier cascade (Section IV-C)" |
| 188 | "Dynamic AP Repositioning via HPSO" | "Dynamic AP Repositioning via TeraMove" |
| 194 | "We achieve this using a Hierarchical Particle Swarm Optimization (HPSO) algorithm" | "Each tier uses a Particle Swarm Optimization (PSO) algorithm" |
| 252 | "At each tier, the HPSO locks" | "At each tier, the PSO locks" |
| 403 | "a 4-tier HPSO escalates" | "a 4-tier cascade escalates" |

Plain word swaps HPSO -> TeraMove: lines 240, 256, 315, 362 (Fig. 2 panel e),
375, 377, 381, 383, 385, 397.

### 1.3 Section IV title
Line 145: "Proposed Work" -> "Proposed TeraMove Framework".

### 1.4 Explanation of TeraMove (Section IV-C)
Section III has no subsections, so this was taken to mean IV-C.
Line 194, new text at the start of the paragraph:

> TeraMove runs each time the human-density map is updated. If the coverage (8) of the
> current layout is below the 90% target, it runs Tiers 2 to 4 (Section IV-C1) in order
> and stops at the first tier that meets the target; after each tier, the Hungarian step
> (Section IV-C2) assigns the current APs to the new positions.

### 1.5 Bounds for each tier (Section IV-C1)
Values taken from `chsr_sim/config.py` and `chsr_sim/optimizer.py`.

- Tier 2 (line 241): azimuth and beamwidth "over the values of Table I".
- Tier 3 (line 245): "$z_a \in [2.0, 3.0]$ m", together with the beam parameters.
- Tier 4 (line 248): "$x_a \in [0.25, 31.75]$ m and $y_a \in [0.25, 19.75]$ m".

### 1.6 Why each tier moves to the next (Section IV-C1)
- Tier 1 (line 238): "When a crowd blocks the links, coverage falls below the target and
  Tier 2 starts."
- Tier 2 (line 241): "These electronic adjustments do not move any AP, so a link blocked
  by a person stays blocked; a wider beam also has less gain."
- Tier 3 (line 245): "A higher AP shortens the part of the link below head height, but
  people near the user still block it, and the 3 m ceiling limits the height."

## 2. Follow-up changes

### 2.1 Greedy comparison removed
- Fig. 3: the "Greedy seed alone" bars removed (the script still computes them, they
  are only not plotted).
- Line 381: removed "The crowd-aware greedy layout of Tier 4, used alone and matched to
  the current APs by the Hungarian step, reaches 98.6% with 107.2 m of movement ...".
- Line 383: "the unseeded baselines" -> "the PSO and GA baselines".
- Line 385: removed "In those runs (9 clusters) the TeraMove result equals its greedy
  seed in every step." and "The greedy seed therefore does most of the work: TeraMove
  returns it unchanged in 84.2% of these events; ...".
- Kept: the greedy layout as one starting particle of Tier 4 (line 249) and the
  "crowd-aware seed" in the abstract and conclusion, because it is part of the method
  that produced the results.

### 2.2 Swarm initialization stated explicitly (Tier 4, line 249)
"To limit displacement, one-third of the swarm starts within ±2 m of the current APs.
One particle starts from a crowd-aware greedy layout:" ->

> The $S$ particles are initialized as follows: one particle starts at the current
> configuration, one-third of the swarm starts within ±2 m of the current APs to limit
> displacement, one particle starts from a crowd-aware greedy layout, and the remaining
> particles start at random positions on the floor. In the greedy layout, ...

## 3. Changes made to stay within 6 pages

| Where | Change |
|---|---|
| Table I (lines 277-295) | Removed rows already given in the text: Main-Lobe Gain (Eq. 5), Static Cubicle/Desk Height (Sec. V-A), Molecular Absorption (Sec. III), Grid Cell / User Height (Sec. III) |
| Fig. 2 caption (line 366) | Shortened to "Adaptation sequence at $t_0$ for one run (Section V-C)."; Section V-C describes the same steps |
| Fig. 3 caption (line 390) | List of methods removed (now in the legend) |
| Sec. V-D (line 381) | "The unconstrained PSO serves as a baseline to isolate the benefits of hierarchical tier constraints; it optimizes the identical composite objective function (16) (including displacement penalty βM) but without tier-clamping, updating all 3D coordinates and beam parameters simultaneously." -> "Standard PSO optimizes the same fitness (16), including the displacement penalty βM, but updates all 3D coordinates and beam parameters at once, without tiers." |
| Discussion (end of second paragraph) | Removed "In our results the coverage target in a crowd is met only by moving APs close to the crowd: Tier 4 moves the APs by 83.5 m in total, against 1.4 m for Tiers 2 and 3." (repeats Sec. V-B) |
| Fig. 1, Fig. 3 | Figure heights reduced slightly |

## 4. Files changed

- `teramove_paper/main.tex`: text edits above.
- `teramove_paper/APSO_Results_ICC/`: new folder with the 8 regenerated figure PDFs.
- `teramove_eval/make_short_assets.py`: figure styling, Fig. 1 function, Fig. 3 without
  the greedy bars.
- `teramove_eval/results_short/fig1_sinr.json`: new, Fig. 1 data.
- `TeraHertz-short/figures/*.pdf`: regenerated. `TeraHertz-short/numbers.tex` and
  `tables/tiers.tex` were regenerated too and are unchanged.
- Not changed: `TeraHertz-short/paper.tex` and `TeraHertz-short/overleaf/` (still say
  HPSO and use the old figures).
