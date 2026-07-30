# Detailed Prior Art Patent Analysis — CHSR THz Invention

## Overview

Analysis of 6 specific patents cited as prior art: 3 international/application-stage + 3 granted US equivalents. Each evaluated for relevance to your **CHSR (Cognitive-Hierarchical Swarm Routing) via Omni-Directionally Movable THz Routers using APSO** invention.

---

## PRIOR ART 1: Fixed THz Access Points (NYU)

### Application

| Field | Details |
|-------|---------|
| **Number** | US20230292199A1 |
| **Title** | *Handover with Low Latency in Response to Blockages in a Wireless Network* |
| **Assignee** | New York University (NYU) |
| **Inventors** | Shivendra S. Panwar, Athanasios Koutsaftis, Fraida Fund |
| **Filed** | 2023 |
| **Published** | September 14, 2023 |
| **Link** | [Google Patents](https://patents.google.com/patent/US20230292199A1) |

### Granted Equivalent

| Field | Details |
|-------|---------|
| **Number** | US12,389,292 B2 |
| **Title** | *Handover with Low Latency in Response to Blockages in a Wireless Network* |
| **Assignee** | New York University (NYU) |
| **Grant Date** | August 12, 2025 |
| **Link** | [Google Patents](https://patents.google.com/patent/US12389292B2) |

### Technical Summary

- Addresses frequent handovers (0.1–1 per second) in mmWave/THz networks due to blockage
- Uses **Fast Wireless Backhaul (FWB)** with multi-connectivity
- UE maintains control-plane connections with **multiple fixed base stations** simultaneously
- Primary/secondary BS roles. When primary blocked, near-instant switch to secondary
- Heartbeat signals keep secondary links alive

### Relevance to Your CHSR Invention

| Aspect | NYU Patent | Your Invention | Overlap? |
|--------|-----------|----------------|----------|
| Problem | Blockage causes handover latency | Blockage causes coverage gaps | Same problem space |
| Solution approach | Keep UE connected to multiple **fixed** BSs, switch when blocked | **Physically move** router to bypass blockage | **Fundamentally different** |
| AP mobility | ❌ None. All APs fixed | ✅ Core feature. Routers move XYZ | No overlap |
| Optimization | None. Rule-based switching | APSO swarm optimization | No overlap |
| THz specific | Mentioned but not THz-specific physics | 300 GHz with absorption, FSPL, material attenuation | Minimal overlap |
| Human density | ❌ Not considered | ✅ D_h(x,y,t) core input | No overlap |

> **Verdict:** Good background prior art showing limitations of fixed-AP approach. Your invention directly solves what this patent cannot — when ALL fixed APs are blocked, handover fails. Your routers move to restore LoS. **No claim conflict.**

---

## PRIOR ART 2: Electronic Beamforming (Samsung)

### Application (WIPO)

| Field | Details |
|-------|---------|
| **Number** | WO2024096638A1 |
| **Title** | *Methods and Apparatus for AI/ML-based Beam Management* |
| **Assignee** | Samsung Electronics Co., Ltd. |
| **Published** | May 10, 2024 |
| **Link** | [Google Patents](https://patents.google.com/patent/WO2024096638A1) |

### Granted US Equivalent (Beamforming category)

| Field | Details |
|-------|---------|
| **Number** | US11,366,195 B1 |
| **Title** | *Dual Function Edge Device and Method for Accelerating UE-Specific Beamforming* |
| **Assignee** | Peltbeam Inc. |
| **Filed** | January 14, 2022 |
| **Grant Date** | June 21, 2022 |
| **Link** | [Google Patents](https://patents.google.com/patent/US11366195B1) |

### Technical Summary

**Samsung WO2024096638A1:**
- AI/ML model prioritizes communication beams in multi-beam systems
- Distributed computation: heavy tasks offloaded to network edge, latency-sensitive processed locally
- Speeds up beam management, reduces beam failure
- Electronic-only beam steering, no physical movement

**Peltbeam US11,366,195:**
- Edge device with antenna array + sensing function
- Tracks moving UE position, steers beam toward it
- Dual function: sensing environment + directing RF beam
- All electronic, fixed device position

### Relevance to Your CHSR Invention

| Aspect | Samsung/Peltbeam | Your Invention | Overlap? |
|--------|-----------------|----------------|----------|
| Beam steering | ✅ AI/ML-driven electronic beam management | ✅ Tier 1-2: beamwidth α + azimuth φ tuning | **Partial overlap in Tier 1-2 only** |
| Physical movement | ❌ None. Fixed infrastructure | ✅ Tier 3-4: Z-height + XY repositioning | No overlap |
| Optimization method | AI/ML neural networks | APSO swarm intelligence | Different algorithm |
| Hierarchy | Single-tier beam management | 4-tier escalation cascade | No overlap |
| When beamforming fails | No fallback mechanism | Escalates to physical movement (Tier 3, 4) | **Your key differentiator** |

> **Verdict:** These patents represent what your Tier 1-2 does electronically. Your novelty is: when electronic beamforming FAILS (which Samsung/Peltbeam have no answer for), you escalate to physical movement. **Cite as "what prior art tries but cannot fully solve."**

---

## PRIOR ART 3: Mobile Relays / UAVs (DJI)

### Application (WIPO)

| Field | Details |
|-------|---------|
| **Number** | WO2018071453A1 |
| **Title** | *Method, Apparatus and System of Providing Communication Coverage to an Unmanned Aerial Vehicle* |
| **Assignee** | SZ DJI Technology Co., Ltd. |
| **Published** | April 19, 2018 |
| **Link** | [Google Patents](https://patents.google.com/patent/WO2018071453A1) |

### Granted US Equivalent

| Field | Details |
|-------|---------|
| **Number** | US11,394,457 B2 |
| **Title** | *Method, Apparatus and System of Providing Communication Coverage to an Unmanned Aerial Vehicle* |
| **Assignee** | SZ DJI Technology Co., Ltd. |
| **Grant Date** | July 19, 2022 |
| **Link** | [Google Patents](https://patents.google.com/patent/US11394457B2) |

### Technical Summary

- Provides communication coverage TO UAVs (not FROM UAVs to users)
- When UAV cannot communicate with primary network, mobile relays bridge gap
- Checks signal quality against predetermined threshold
- Coordinates relay placement to extend operating region
- Outdoor, macro-scale, generic cellular frequencies

### Relevance to Your CHSR Invention

| Aspect | DJI Patent | Your Invention | Overlap? |
|--------|-----------|----------------|----------|
| Mobile nodes | ✅ UAVs as mobile relays | ✅ Ground routers on XY platform | Conceptual similarity only |
| Environment | Outdoor, airborne | Indoor, ground-based, room-scale | **Different domain** |
| Frequency | Generic cellular | THz 300 GHz with absorption model | No overlap |
| Optimization | Threshold-based relay coordination | APSO with composite fitness function | Different algorithm |
| Movement control | UAV flight path planning | Rail/wheel-based XYZ mechanical actuators | Different mechanism |
| Blockage modeling | ❌ No wall/material attenuation | ✅ Concrete 30dB, Wood 20dB, Glass 15dB | No overlap |
| Swarm behavior | ❌ Individual relay decisions | ✅ Coordinated swarm with anti-clustering | No overlap |
| Human density | ❌ Not considered | ✅ D_h(x,y,t) drives optimization | No overlap |
| Hierarchy | ❌ Single-tier | ✅ 4-tier escalation | No overlap |

> **Verdict:** DJI patent is about providing coverage TO drones, not FROM movable APs to indoor users. Different direction, different domain, different optimization. Your indoor ground-based movable THz routers with APSO are distinct. **Cite as general mobile relay concept, but clearly differentiate.**

---

## Master Differentiation Matrix

| Feature | NYU (PA1) | Samsung/Peltbeam (PA2) | DJI (PA3) | **Your CHSR** |
|---------|-----------|----------------------|-----------|---------------|
| Physical router movement | ❌ | ❌ | ⚠️ UAV only | ✅ Ground XYZ |
| THz 300 GHz physics | ⚠️ Mentioned | ❌ | ❌ | ✅ Full model |
| Electronic beam tuning | ❌ | ✅ | ❌ | ✅ Tier 1-2 |
| Z-height adjustment | ❌ | ❌ | ❌ | ✅ Tier 3 |
| XY repositioning | ❌ | ❌ | ⚠️ UAV flight | ✅ Tier 4 |
| 4-tier hierarchy | ❌ | ❌ | ❌ | ✅ Novel |
| APSO optimization | ❌ | ❌ | ❌ | ✅ Novel |
| Hungarian assignment | ❌ | ❌ | ❌ | ✅ Novel |
| Human density D_h(x,y,t) | ❌ | ❌ | ❌ | ✅ Novel |
| Anti-clustering penalty | ❌ | ❌ | ❌ | ✅ Novel |
| Material-aware walls | ❌ | ❌ | ❌ | ✅ Novel |
| Indoor room-scale | ⚠️ Possible | ⚠️ Edge device | ❌ Outdoor | ✅ Core |

---

## Conclusion

> [!IMPORTANT]
> **None of these 3 prior art categories (6 patents) anticipate your invention's core claims.**
>
> - **PA1 (NYU)** solves blockage by switching between fixed APs. Fails when all APs blocked.
> - **PA2 (Samsung/Peltbeam)** solves blockage by electronic beam steering. Fails when no viable LoS exists from fixed position.
> - **PA3 (DJI)** uses mobile relays but: outdoor, UAV-based, no THz, no swarm optimization, no hierarchy.
>
> **Your invention fills the gap:** When electronic tuning (PA2) fails AND fixed handover (PA1) fails AND indoor constraints prevent UAVs (PA3), your physically movable ground routers with 4-tier APSO hierarchy provide coverage.

### Recommended Citation Strategy for Patent Application

Use these 3 prior art categories in your **Background of Invention** section as:

1. **PA1 (NYU):** "Fixed THz APs require dense deployment and still fail under full blockage scenarios..."
2. **PA2 (Samsung/Peltbeam):** "Electronic beamforming cannot overcome complete structural blockages when no viable LoS path exists from fixed position..."
3. **PA3 (DJI):** "UAV-based mobile relays address outdoor macro coverage but lack fine-grained indoor THz optimization under dynamic human density..."
4. **Your invention:** "The present invention addresses all three limitations simultaneously through..."
