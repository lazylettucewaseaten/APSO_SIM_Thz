# TeraMove-H — Implementation Plan

This plan was written before any code. It fixes every modelling decision, its source,
and the order of work. `docs/REPORT.md` records what was actually done and every
deviation from this plan.

## 0. Inputs reused

| Input | Use |
|---|---|
| `MILP.pdf` Fig. 1 | Initial 14-AP layout (x, y, z, azimuth). The MILP is **not re-run**. |
| `chsr_sim/environment.py::gen_walls` | Floor plan (32 m x 20 m, walls, doors, glass, 1 m cubicles). Reused verbatim. |
| `chsr_sim/optimizer.py` | PSO update rule, tier locking, composite fitness, Hungarian matching. Logic reused and generalised. |
| `THZ_Placement-2.pdf` (TeraMove) | Cascade design, fitness weights (configuration D: wc=0.4, wd=0.6, beta=0.25, gamma=0.3), swarm rule (w 0.9->0.4, c1=c2=1.5). |

## 1. Defects found in the legacy code/papers (to be fixed in the new package)

| # | Defect | Evidence | Fix |
|---|---|---|---|
| D1 | Azimuth convention mismatch. MILP Table II: azimuth "from North"; `physics.py` uses `atan2` from +x (East, CCW). APs at 135 deg in Fig. 1 point *out of the building* in the simulator. | Compass interpretation raises empty-room coverage of the Fig. 1 layout from 43.9% to 60.8% (legacy physics, 60 deg). | Compass bearing (0 = +y, clockwise) everywhere; one conversion function, unit-tested. |
| D2 | Main-lobe gain independent of beamwidth (30 dBi for 30-120 deg). Violates energy conservation. | `physics.py:96` | Exact flat-top normalisation (Sec. 2.2). |
| D3 | Molecular absorption `K_F = 0.05 m^-1` (217 dB/km). | ITU-R P.676 (computed with ITU-Rpy 0.4.0): 6.68 dB/km at 300 GHz, 23 C, 10 g/m^3. | k = 1.538e-3 m^-1. |
| D4 | Noise floor −64 dBm in code but −94 dBm in TeraMove paper. | config vs. paper Table II | N0 derived from bandwidth and NF; reported consistently. |
| D5 | Users evaluated at integer cell corners (on top of walls at y = 10, 12, x = 0 ...). | `range(length)` grid | Cell centres (x + 0.5, y + 0.5). |
| D6 | Human blockage: fractional density x 20 dB summed per sampled cell, unbounded, averaged in dB; coarse cell sampling (`int(d)` steps). | `physics.py:66-77` | Discrete people as cylinders; exact segment-cylinder test; per-body loss with cap. Monte-Carlo over crowd realisations gives the expectation in the right domain. |
| D7 | PSO/GA comparison figures in the TeraMove paper are hard-coded numbers. | `generate_comparison_plots.py:26-58`, `generate_paper_figures.py:326-333` | Real flat-PSO and GA baselines, same fitness, same evaluation budget, 30 seeds. |
| D8 | Swarm size: paper S = 50, T = 20; code 200 x 200. | `config.py` | One set of parameters, printed into the paper from the code. |
| D9 | Tier-4 static cache keyed by continuous (x, y, z) grows without bound (~5.6 GB at 200 x 200). | `physics.py:180` | Positions snapped to a 0.25 m rail grid + bounded LRU cache. |
| D10 | APs may move through walls (positions anywhere in [0, 32] x [0, 20]). | `decode_routers` | Each AP is confined to its room (ceiling rail per room); Hungarian matching only inside a room. |

## 2. System model (frozen)

### 2.1 Geometry
* Floor 32 m x 20 m x 3 m, walls from `gen_walls`. Rooms = 13 axis-aligned rectangles derived from the walls (`geometry.ROOMS`).
* THz APs: initial positions/heights/azimuths from MILP Fig. 1. Heights z in {2.0, 2.2, ..., 3.0} m. Azimuth in 45 deg steps (compass). Sector width alpha in {30, 45, 60, 75, 90, 120} deg.
* Wi-Fi APs: 4 fixed ceiling APs (z = 3.0 m) at the centres of the four large rooms.

### 2.2 THz link (300 GHz)
* Path loss: FSPL(d3D) + 4.343 k d3D + static wall penalties (30/20/15 dB solid/wood/glass, 1 m cubicles 20 dB; MILP Table II) + human body loss.
* Human bodies: vertical cylinders, radius 0.2 m, height 1.6 m (MILP h_human). A link is blocked by a body if its 2-D projection passes within the radius and the ray height there is <= 1.6 m. Loss 20 dB per body (MILP L_h), capped at 40 dB.
* Self-blockage: 3GPP TR 38.901 Sec. 7.6.4.1 portrait mode (phi_sb = 260, x_sb = 120, theta_sb = 100, y_sb = 80 deg, 30 dB), user facing direction uniform.
* AP antenna: flat-top sector covering the lower half-space (all elevations below the AP) over azimuth width alpha; side-lobe level g_s = −10 dBi. Energy conservation: G_m(alpha) = (4 pi − g_s (4 pi − alpha)) / alpha (alpha in rad; solid angle of the sector = alpha sr).
* UE antenna: steerable pencil beam, G_r = 20 dBi, side lobe −10 dBi, main-lobe cone half-angle psi_r from the same normalisation (10.9 deg). The UE points its beam at its serving AP.
* Noise: B = 10 GHz, NF = 10 dB, N0 = −174 + 100 + 10 = −64 dBm.
* SINR uses interference from all *awake* THz APs (full buffer; same 10 GHz channel). Rate c = B min(log2(1 + SINR), 6); link usable iff SINR >= 5 dB (TeraMove).
* P_max = 20 dBm per AP (TeraMove).

### 2.3 Wi-Fi link (6 GHz, 802.11ax)
* 3GPP TR 38.901 InH-Office path loss: LOS if the ray crosses no full-height wall and no body, else NLOS (PL_NLOS = max(PL_LOS, PL'_NLOS)). fc = 6 GHz.
* 20 dBm + 3 dBi AP, 0 dBi UE, 160 MHz, 2 spatial streams, orthogonal channels (no co-channel interference).
* Rate: highest MCS whose minimum input sensitivity (802.11 Table 21-25 / 802.11ax, 20 MHz values + 9 dB for 160 MHz) is met, PHY rate x MAC efficiency 0.7.

### 2.4 Users, crowd, demand
* N_p people: 80% in 6 Gaussian clusters (sigma = 1 m) with uniform centres, 20% uniform. People are rejected if within 0.25 m of a wall/cubicle segment.
* Each person is an active user with probability rho = 0.5; device at 1.0 m; facing uniform.
* Demand R_min per user (default 1 Gbps). AP serves its users by time sharing; user u needs airtime tau_ua = R_min / c_ua; per-AP budget sum tau <= 1.
* Temporal model: clusters drift 1.5 m/epoch in a random direction (reflecting at the boundary); people keep identity/offset with 0.3 m jitter; facing jitter 30 deg.
* Context density map (paper Eq. 12): D(c) = min(1, n(c)/n_max), n_max = 4 people per 1 m cell — used by the legacy TeraMove fitness and figures.

## 3. Optimisation

* Primary metric: satisfaction S = fraction of active users receiving >= R_min.
* Association = maximum generalised assignment problem with unit profits (airtime budgets). Greedy: sort feasible (u, a) pairs by airtime, assign if user free and budget fits. Exact ILP with `scipy.optimize.milp` only to measure the greedy gap (small instances; this is **not** the placement MILP).
* Power: Yates fixed point with per-user SINR targets that use the spare airtime; idle APs sleep (p = 0). Starting from P_max (feasible) the iteration is monotone and converges to the minimal power vector (Yates 1995), so S never drops.
* Cascade (TeraMove-H): T0 re-associate (THz + Wi-Fi) -> T1 sleep + re-associate + power trim -> T2 HPSO beams (phi, alpha) -> T3 + height -> T4 + (x, y) within room + Hungarian. Stop when S >= eta = 0.9. Final power trim always.
* Fitness: F = 0.6 S + 0.4 Q + 0.5 1[S >= eta] − beta M − gamma C_p, Q = mean_u min(1, c_u^best / R_min) (smooth link-quality term). beta = 0.25, gamma = 0.3, d_min = 3 m.

## 4. Baselines and experiments

Methods: B0 static; B1 TeraMove (legacy fitness, THz only, max-SINR association, corrected physics); B2 THz-only TeraMove-H; B3 hybrid naive offload + TeraMove cascade; B4 Wi-Fi only; B5 flat PSO; B6 GA; Proposed. Ablation: no power control, no movement (T0-T2).

Experiments (30 seeds unless stated): E1 static layout check; E2 main comparison; E3 regime map (R_min x N_p); E4 temporal (6 epochs) with handovers, displacement, power; E5 association greedy vs exact; E6 sensing error; E7 convergence (real curves).

## 5. Work order
1. Package skeleton, config, geometry (rooms, MILP layout), crowd. Tests.
2. THz + Wi-Fi channels (numba), antenna normalisation. Tests (energy integral, FSPL, noise, wall/cylinder intersection, convention).
3. Association, power, evaluator. Tests (feasibility, optimality on brute force, Yates monotonicity).
4. Optimiser (HPSO tiers, flat PSO, GA), Hungarian per room, cascade, baselines. Tests.
5. Experiments -> CSV in `results/`. Figures from CSV only. Numbers -> `paper/numbers.tex` macros.
6. Paper (`paper/main.tex`, IEEEtran) + `docs/REPORT.md`.
7. Final audit: every number in the paper traced to a CSV, re-compile, re-run tests.
