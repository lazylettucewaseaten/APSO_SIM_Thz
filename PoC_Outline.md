# Proof of Concept (PoC)
## Adaptive THz Access Point Placement Using APSO with 4-Tier Hierarchical Escalation

---

## 1. Problem Statement
- THz (300 GHz) signals suffer from severe path loss, molecular absorption, and blockage
- Fixed access points cannot adapt to changing user/crowd distributions
- Electronic beamforming alone fails when all line-of-sight paths are blocked by walls or human bodies
- Baseline coverage drops to 60–75% in dynamic indoor environments — far below the 95% target

## 2. Proposed Solution
- 7 THz routers mounted on motorized ceiling rails for physical repositioning
- APSO (Adaptive Particle Swarm Optimization) computes optimal router positions in real-time
- 4-Tier Escalation Hierarchy to minimize unnecessary mechanical movement:
  - Tier 1–2: Electronic adaptation (beam azimuth φ, beamwidth α)
  - Tier 3: Vertical height adjustment (Z-axis, 2.0m–3.0m)
  - Tier 4: Full 3D spatial repositioning (X, Y, Z)
- Hungarian Algorithm for minimum-displacement router-to-target assignment

## 3. Simulation Setup
- Room: 32m × 20m × 3m with realistic wall layout (concrete, wood, glass)
- Routers: 7 THz APs at 300 GHz, 20 dBm Tx power, 30 dBi antenna gain
- Channel Model: FSPL + molecular absorption (k_f = 0.05) + 3D ray-wall intersection + human body blockage (20 dB)
- Material Losses: Concrete 30 dB, Wood 20 dB, Glass 15 dB
- APSO Config: 20 particles, 35 dimensions (7 routers × 5 params), 20 iterations, adaptive inertia (0.9 → 0.4)
- Fitness Function: Density-weighted coverage (0.6) + cell coverage (0.4) + target bonus − movement penalty − anti-clustering penalty
- Time Steps: 3 dynamic crowd scenarios (t₀, t₁, t₂) with shifting Gaussian user distributions

## 4. Results & Evidence
- Coverage Improvement:
  - Before APSO: ~60–75%
  - After APSO: ≥95% (target met across all 3 time steps)
- Optimization Speed: <2.5 seconds per cycle (real-time feasible)
- Total Router Displacement: <5–12 meters combined across all 7 routers
- Reachability Gain: +15–35% coverage increase per meter of movement
- Dead Zone Reduction: ~90% elimination of poor-SINR areas
- SINR Heatmaps: Clear visual improvement — dead zones before → uniform coverage after
- Coverage maintained consistently across all dynamic crowd shifts


## 6. Working Demo
- Interactive Web Dashboard (React + Vite + FastAPI): tune parameters, run optimization, see SINR heatmap update live
- CHSR Hierarchy Visualizer: animated 4-tier communication flow
- Python Simulation: generates all plots (SINR heatmaps, AP placement, density maps, coverage charts) in seconds
- Numba JIT-compiled physics for real-time performance on commodity hardware

## 7. Conclusion
- The concept is validated through simulation with quantitative and visual evidence
- Coverage target of ≥95% is consistently achieved across dynamic scenarios
- Optimization is real-time feasible (<2.5s) with minimal physical movement
- Solution is technically feasible — ceiling rails, THz hardware, and APSO all exist today
- IP protected — patent disclosure filed at IIT Bhilai
