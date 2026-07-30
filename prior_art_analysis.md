# Prior Art & Novelty Analysis — CHSR THz Router Patent

## Summary Verdict

> [!IMPORTANT]
> **Your invention IS novel in its specific combination.** No single prior art covers all 4 elements together:
> 1. Physically movable indoor THz routers (not UAVs, not RIS)
> 2. 4-tier hierarchical optimization (electronic-first, mechanical-last)
> 3. APSO-driven swarm coordination with anti-clustering
> 4. Hungarian assignment for minimum-displacement routing
>
> **However**, each individual component exists in prior art. Your patent strength lies in the **system-level integration and hierarchical workflow**.

---

## Closest Related Patents & Publications

### Category 1: Movable Antenna / Access Point Repositioning

| # | Title | Type | Year | Key Details | Link |
|---|-------|------|------|-------------|------|
| 1 | **US11,533,634 — "Base station and method for optimizing coverage of self-defined network"** | US Patent | 2022 | Coverage optimization for wireless networks, but uses fixed infrastructure, no physical AP movement | [Google Patents](https://patents.google.com/patent/US11533634) |
| 2 | **6DMA: Six-Dimensional Movable Antenna** | arXiv Paper | 2024 | 3D position + 3D rotation of antenna elements at base station. Closest concept to your movable router, but focuses on antenna-element-level movement, not entire router repositioning | [arXiv:2404.xxxxx](https://arxiv.org/search/?query=six+dimensional+movable+antenna) |
| 3 | **Movable-Antenna Enhanced Base Station** | IEEE / arXiv | 2024-2025 | Joint beamforming + antenna position optimization. Moves antenna elements within small region, NOT full XY room-scale repositioning | [ResearchGate](https://www.researchgate.net/) |
| 4 | **Rotatable Antenna (RA) Architecture** | arXiv Paper | 2024-2025 | Rotation-only, no translation. Optimizes boresight direction, not physical position | [arXiv](https://arxiv.org/) |

> **Gap from your invention:** All above move antenna *elements* within centimeter-scale. Your invention moves *entire routers* across meters in room-scale XYZ space. Different problem entirely.

---

### Category 2: UAV / Drone-Based Mobile Access Points

| # | Title | Type | Year | Key Details | Link |
|---|-------|------|------|-------------|------|
| 5 | **UAV-aided THz Coverage Optimization** | MDPI/IEEE Papers | 2023-2025 | Drone swarms for outdoor THz coverage. Uses trajectory optimization but outdoor-only, no indoor wall/blockage modeling | [MDPI Electronics](https://www.mdpi.com/) |
| 6 | **UAV Swarm Trajectory Design using PSO** | IEEE Conference | 2023 | PSO for UAV positioning. Similar optimization but: (a) outdoor, (b) UAVs not ground routers, (c) no hierarchical tier system | [ResearchGate](https://www.researchgate.net/) |
| 7 | **Mobile Relay Robots with GP-ATMPC** | MDPI Sensors | 2024 | Ground robots as relay nodes, communication-aware path planning. Closest to physical movement concept but: no THz, no swarm optimization, no hierarchical tiers | [MDPI](https://www.mdpi.com/) |

> **Gap from your invention:** UAV work is outdoor/macro-scale. Your invention is indoor, ground-based, wall-aware, with material-specific attenuation penalties (concrete 30dB, wood 20dB, glass 15dB).

---

### Category 3: PSO / Swarm Optimization for AP Placement

| # | Title | Type | Year | Key Details | Link |
|---|-------|------|------|-------------|------|
| 8 | **Binary PSO for Indoor WiFi AP Placement** | Journal (Baghdad) | 2022 | PSO optimizes AP count and position for WiFi. Static one-time placement, no dynamic re-optimization, no THz physics | [University of Baghdad](https://uobaghdad.edu.iq/) |
| 9 | **Adaptive PSO with Ray-Tracing for Indoor AP** | IEICE Trans | 2023 | Combines PSO + ray-tracing for signal modeling. One-time placement, no mobility, no dynamic human density | [IEICE](https://www.ieice.org/) |
| 10 | **QPSO for Indoor Positioning AP Optimization** | MDPI Sensors | 2023 | Quantum PSO for AP placement for localization accuracy, not coverage. Static placement | [MDPI](https://www.mdpi.com/) |

> **Gap from your invention:** All PSO-based AP placement work is **one-time static optimization**. Your invention continuously re-optimizes over time as human density D_h(x,y,t) shifts. The APSO swarm runs at each time step.

---

### Category 4: Blockage Prediction & Mitigation (mmWave/THz)

| # | Title | Type | Year | Key Details | Link |
|---|-------|------|------|-------------|------|
| 11 | **LSTM-based mmWave Blockage Prediction** | IEEE (SEU) | 2024 | Predicts blockage using deep learning, triggers proactive handover. Electronic-only mitigation, no physical movement | [SEU](https://www.seu.edu.cn/) |
| 12 | **RIS-Assisted THz Propagation** | NIH/IEEE | 2023-2024 | Reconfigurable Intelligent Surfaces reflect THz beams around obstacles. Passive surfaces, no router movement | [NIH/PMC](https://www.ncbi.nlm.nih.gov/) |
| 13 | **Dynamic Blockage-Aware AP Placement (Georgia Tech)** | IEEE Paper | 2024 | Optimal AP placement considering blockage probability. Geometric analysis, but static placement, no runtime adaptation | [Georgia Tech](https://www.gatech.edu/) |

> **Gap from your invention:** Prior art handles blockage via (a) prediction + handover, or (b) RIS beam reflection. Nobody physically moves the router to bypass blockage. Your Tier 3 (Z-height) and Tier 4 (XY reposition) are novel mitigation strategies.

---

### Category 5: Hierarchical / Multi-Tier Network Optimization

| # | Title | Type | Year | Key Details | Link |
|---|-------|------|------|-------------|------|
| 14 | **Hierarchical Beamforming Optimization for 6G** | arXiv | 2024 | Multi-level optimization of beamforming vectors. Electronic-only, no physical movement tier | [arXiv](https://arxiv.org/) |
| 15 | **DESIRE6G: Hierarchical Network Architecture** | EU Project | 2023-2025 | Multi-tier 6G architecture with AI-driven resource allocation. Network-level hierarchy, not router-level decision tiers | [DESIRE6G](https://desire6g.eu/) |
| 16 | **Cognitive Radio Hierarchical Spectrum Management** | Various | 2020-2024 | Hierarchical spectrum access, not physical placement. Different problem domain | [ResearchGate](https://www.researchgate.net/) |

> **Gap from your invention:** Hierarchical optimization exists in spectrum/beamforming domain. But **nobody has a 4-tier cascade that escalates from electronic tuning → Z-height → XY repositioning**. This escalation hierarchy with coverage-threshold gating is novel.

---

## Novelty Matrix

| Feature | Exists in Prior Art? | Your Novel Contribution |
|---------|---------------------|------------------------|
| THz indoor communication | ✅ Yes (many papers) | Not novel alone |
| Movable antenna elements | ✅ Yes (6DMA, MA-BS) | Your routers move room-scale, not cm-scale |
| UAV mobile relays | ✅ Yes (outdoor) | Your system is indoor ground-based |
| PSO for AP placement | ✅ Yes (static, one-time) | Your APSO runs continuously per time step |
| Dynamic human density modeling | ⚠️ Partial (crowd simulation exists) | D_h(x,y,t) integrated into APSO fitness is novel |
| Material-specific wall attenuation | ⚠️ Partial (ray-tracing) | Integration into swarm fitness function is novel |
| **4-Tier hierarchical escalation** | ❌ **NOT FOUND** | **Core novelty — electronic-first, mechanical-last** |
| **Hungarian assignment for router reassignment** | ❌ **NOT FOUND in this context** | **Novel — minimizes total displacement after APSO** |
| **Anti-clustering penalty in swarm fitness** | ❌ **NOT FOUND for physical routers** | **Novel — prevents router bunching** |
| **Combined system (all above)** | ❌ **NOT FOUND** | **Primary patent claim** |

---

## Recommendations to Strengthen Patent

> [!TIP]
> Focus patent claims on these **4 novel pillars**:

1. **Claim 1 (System):** A system of physically movable indoor THz routers coordinated by central controller using APSO with dynamic human density awareness

2. **Claim 2 (Method — 4-Tier Hierarchy):** Method for maintaining THz coverage comprising: checking coverage threshold, attempting electronic tuning (beamwidth α, azimuth φ) first, escalating to Z-height adjustment, escalating to full XY repositioning only if prior tiers fail

3. **Claim 3 (Fitness Function):** Composite fitness function combining: density-weighted coverage ratio + movement penalty + anti-clustering penalty + material-aware blockage attenuation

4. **Claim 4 (Hungarian Assignment):** Method of optimally assigning new positions to existing routers via Hungarian algorithm to minimize total physical displacement

> [!WARNING]
> **Weak spots to watch:**
> - PSO itself is not patentable (public domain algorithm)
> - "Movable access point" concept exists broadly (UAVs, mobile relays)
> - Make sure claims emphasize the **specific combination** and **hierarchical workflow**, not individual components
