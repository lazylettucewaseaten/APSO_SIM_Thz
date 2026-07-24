# INVENTION DISCLOSURE FORM (IDF)
**Date:** 24 July 2026
**Client:** IIT BHILAI [IITBH]

## 1. Title of the Invention
6G Cognitive-Hierarchical Swarm Routing (CHSR) via Omni-Directionally Movable and Adaptable Terahertz (THz) Routers using APSO

## 2. Technology Domain of the Invention
6G Wireless Telecommunications, Terahertz (THz) Networking, Cognitive Routing, Swarm Robotics, and Dynamic Mobility Control.

## 3. Background of the Invention
**Problems the invention tries to solve:**
The Terahertz (THz) band (e.g., 300 GHz) is crucial for next-generation 6G networks as it provides extreme data rates. However, it suffers from severe propagation losses (Free-Space Path Loss and molecular absorption) and is highly susceptible to both static physical blockages (walls, furniture) and dynamic blockages (human crowds, mobile obstacles). Traditional networking relies on fixed-position Access Points (APs) or routers; in the THz band, any blockage drastically degrades the Signal-to-Interference-plus-Noise Ratio (SINR). When the environment changes (e.g., varying human density), static routers fail to maintain reliable coverage and QoS. 

**Existing Prior Art / Limitations:**
1. *Fixed THz Access Points*: High deployment density is required to maintain coverage, leading to immense cost and interference, but they still fail when dense dynamic blockages occur.
2. *Electronic Beamforming in 5G/6G*: Adjusts signal direction electronically but cannot overcome full structural blockages or severe human crowding when there is no viable line-of-sight path from the fixed router position.
3. *Mobile Relays/UAVs*: Generally used for macro outdoor coverage, lacking fine-grained, instantaneous indoor translation constrained by latency and mechanical overhead.

## 4. Invention Description
**Briefly summarize how the aforementioned problem is solved by the invention:**
The invention solves this problem through a Cognitive-Hierarchical Swarm Routing (CHSR) system that employs physically movable routers. These routers can move in any spatial direction (X, Y, and Z dimensions) and adjust transmission parameters to maintain line-of-sight paths. Instead of blindly moving, the routers are driven by an Adaptive Particle Swarm Optimization (APSO) algorithm that dynamically evaluates human crowd density and static blockages. The hierarchical approach first tries tuning electronic parameters, and only physically relocates the routers (vertically or omni-directionally) if coverage falls below a pre-set threshold, thereby minimizing mechanical actuation latency and maximizing SINR coverage.

**Briefly summarize the “unique” or “novel” or “inventive” aspects of your invention:**
The core novelty lies in the 4-Tier Hierarchical APSO workflow for movable routers, optimizing the balance between electronic adaptation and mechanical translation to minimize latency:
- **Tier 1 & 2**: Electronic tuning of beamwidth ($\alpha$) and azimuth orientation ($\phi$).
- **Tier 3**: Vertical mechanical translation (Z-axis height adjustments) if electronic tuning is insufficient to bypass blockages.
- **Tier 4**: Full spatial translation (X, Y-axis relocation) if Tier 3 still yields sub-optimal coverage.
Furthermore, the swarm optimization model actively integrates a dynamically shifting human crowd probability density matrix $D_h(x,y,t)$ and static infrastructure material penalties (solid/wood/glass) into the continuous fitness evaluation stringency, resulting in real-time, blockage-aware adaptive placement.

## 5. Advantages of the Invention
- **Sustained Ultra-High-Speed Coverage**: Maintains $>85\%$ continuous coverage threshold for THz networks despite dynamic human mobility and line-of-sight obstruction.
- **Low Mechanical Latency**: By structuring the optimization hierarchically, physical movement is treated as a last resort, drastically reducing mechanical actuation latency and operational wear.
- **Autonomous Swarm Management**: Routers adapt and act together via APSO, finding global optimal states for the entire network coverage map without complex manual surveys.
- **Resource Efficiency**: Needs fewer access points compared to dense static AP deployment because the existing units physically optimize their spatial position to serve active density zones.

## 6. Testing 
**Has the invention been tested experimentally or prototypes?**
Yes, the invention has been heavily tested via robust simulation models.
- **Simulation Environment**: A 3D discrete grid of $32\text{m} \times 20\text{m} \times 3\text{m}$ room layout with varying material attenuation (Concrete: 30dB, Wood: 20dB, Glass: 15dB). 
- **Setup**: Evaluated at 300 GHz frequency, 20 dBm transmit power, dynamically checking beamwidth selections ($30^\circ$ to $120^\circ$) and Z-axis candidate heights from 2.0m to 3.0m in shifting human density scenarios (20 dB blockage penalty per human).
- **Results**: The 4-Tier APSO efficiently sustains the required coverage (SINR $> 0.85$ proportion stringency) as density shifts over time ($t_0, t_1, t_2$), proving that physically adjusting Z, X, and Y positions alongside beamwidth yields a superior coverage map (evident in before/after SINR heatmaps).

## 7. Commercial Potential
**7.1 Application Areas/Products:**
- 6G Indoor Network Infrastructure for smart factories, automated warehouses, and large stadia.
- AR/VR gaming arenas and dense office enterprise environments requiring high-bandwidth, ultra-low latency uninterrupted feeds.
- Robotic, self-optimizing IoT base stations.

**7.2 Probable Users:**
Telecom Network Operators (Verizon, AT&T, Jio), Infrastructure Equipment Vendors (Ericsson, Nokia, Samsung, Huawei), Smart Building Integrators, and automated Industry 4.0 entities.

## 8. Prior Self Publication
- **Disclosure Type**: Detailed in custom simulation reports (e.g., "6G Cognitive-Hierarchical Swarm Routing (CHSR) Optimization under Dynamic Blockages - Simulation Report").
- **Date**: July 2026

## 9. Application Countries
India, United States, European Union, Japan, South Korea, China.
