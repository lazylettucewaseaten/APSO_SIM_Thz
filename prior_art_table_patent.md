# Prior Art / Existing Solution Table

---

### Prior Art No. 1

**Publication Details:**
- **Publication Number:** US11,533,634 B2 (United States)
- **Inventors:** Guan-Hsien Du, Tsun-Chieh Chiang
- **Current Assignee:** Industrial Technology Research Institute (ITRI)

**Brief Description of the Prior Art:**
This patent discloses a method for optimizing coverage of a self-defined wireless network, wherein base stations autonomously discover neighboring base stations through measurement reports and member tracking messages, and dynamically form self-organizing groups through merging and splitting operations. The system manages coverage by adjusting transmission power and controlling inter-group interference among fixed-position base stations.

**Relevance to the Present Invention:**

The prior art addresses network-level coverage optimization through logical grouping and power control of statically deployed base stations. Its key limitations and the differentiation of the present invention are as follows:

- The prior art relies entirely on fixed infrastructure and does not contemplate physical repositioning of access points to overcome line-of-sight obstructions caused by structural elements or dynamic obstacles.
- In contrast, the present invention introduces physically movable routers capable of autonomous spatial translation in three dimensions (X, Y, and Z axes), enabling the network to actively bypass obstructions rather than merely adjusting signal parameters around them.
- The present invention employs a population-based metaheuristic optimization process that collectively evaluates the positions of all access points simultaneously, considering real-time environmental conditions such as dynamic blockage patterns and time-varying user density distributions.
- Where the prior art adjusts only electronic transmission parameters of immovable base stations, the present invention provides a hierarchical optimization framework that progressively escalates from electronic parameter tuning to mechanical repositioning, invoking physical movement only when electronic adaptation alone is determined to be insufficient to meet coverage requirements.
- This hierarchical approach minimizes unnecessary mechanical actuation and associated latency, a consideration entirely absent from the prior art.

---

### Prior Art No. 2

**Publication Details:**
- **Publication Number:** US11,394,457 B2 (United States)
- **Inventors:** Ming Gong, Wei Fan
- **Current Assignee:** SZ DJI Technology Co., Ltd.

**Brief Description of the Prior Art:**
This patent discloses a method and system for providing communication coverage to unmanned aerial vehicles (UAVs) using mobile relay nodes. The system determines whether a UAV can maintain communication with a primary network at a predetermined quality threshold and, if not, coordinates mobile relays to extend coverage to the UAV's operating region.

**Relevance to the Present Invention:**

The prior art demonstrates the concept of mobile nodes providing supplemental wireless coverage. However, its scope and approach differ fundamentally from the present invention in the following respects:

- The prior art is directed to outdoor, airborne scenarios for maintaining connectivity to UAVs, rather than optimizing indoor network coverage for ground-level user equipment operating in high-frequency bands susceptible to severe indoor propagation losses.
- The prior art employs threshold-based relay coordination without consideration of indoor-specific propagation characteristics such as material-dependent wall attenuation, dynamic human crowd blockages, or molecular absorption effects inherent to terahertz-band operation.
- In contrast, the present invention employs ground-based movable access points within enclosed indoor environments, where signal propagation is governed by fundamentally different physical constraints including multi-material structural blockages and time-varying occupant distributions.
- The present invention coordinates access point repositioning through a multi-tier hierarchical optimization process that jointly considers electronic beam adaptation and physical repositioning, progressively escalating intervention only when lower tiers prove insufficient.
- The optimization in the present invention incorporates a composite evaluation criterion that simultaneously accounts for coverage maximization, physical movement minimization, and spatial distribution constraints to prevent clustering of access points — considerations entirely absent from the prior art's relay coordination approach.

---

### Prior Art No. 3

**Publication Details:**
- **Publication Number:** WO2024/096638 A1
- **Inventors:** Chadi Khirallah, Oluwatayo Yetunde Kolawole, Mythri Hunukumbure
- **Current Assignee:** Samsung Electronics Co., Ltd.

**Brief Description of the Prior Art:**
This international application discloses methods and apparatus for AI/ML-based beam management in wireless communication systems. The system employs machine learning models to prioritize and select communication beams in multi-beam environments, distributing computational tasks between network endpoints and local devices to reduce beam failure rates and accelerate beam alignment operations.

**Relevance to the Present Invention:**

The prior art addresses beam management through electronic beam steering and intelligent beam prioritization. Its relationship to the present invention is as follows:

- The prior art corresponds functionally to the electronic parameter tuning capabilities of the present invention — specifically, the optimization of beam directional parameters such as beamwidth and azimuth orientation from a fixed access point position.
- However, the prior art is limited to purely electronic adaptation and provides no mechanism to overcome coverage deficiencies that persist when no viable line-of-sight path exists from the fixed position, such as when dense physical obstructions or dynamic human crowds fully obstruct all achievable beam directions from that location.
- The present invention recognizes that electronic beam management, while effective for partial obstructions and moderate environmental changes, is fundamentally insufficient when the access point's physical position itself prevents any achievable beam configuration from reaching target coverage areas.
- To overcome this limitation, the present invention incorporates a hierarchical decision framework wherein electronic beam tuning is attempted first as a low-latency intervention, and physical repositioning of the access point — including vertical height adjustment and full spatial relocation — is invoked progressively only when electronic adaptation is determined to be insufficient to meet the required coverage threshold.
- This tiered approach ensures that mechanical actuation overhead and associated latency are incurred only when necessary, while guaranteeing sustained coverage under conditions that purely electronic systems cannot resolve.
- The present invention thus subsumes the electronic beam management capabilities described in the prior art as an integral first stage of a broader, multi-modal optimization process.

---

## Summary of Differentiation

| Feature | Prior Art 1 (ITRI) | Prior Art 2 (DJI) | Prior Art 3 (Samsung) | **Present Invention** |
|---------|--------------------|--------------------|----------------------|----------------------|
| Physical AP repositioning | ✗ | ✗ (UAV relay only) | ✗ | ✓ (3-axis ground movement) |
| Indoor environment modeling | ✗ | ✗ | ✗ | ✓ |
| THz-band operation | ✗ | ✗ | Partial | ✓ |
| Hierarchical optimization tiers | ✗ | ✗ | ✗ | ✓ |
| Swarm-based optimization | ✗ | ✗ | ✗ | ✓ |
| Dynamic user density awareness | ✗ | ✗ | ✗ | ✓ |
| Movement minimization | ✗ | ✗ | ✗ | ✓ |
| Material-specific blockage modeling | ✗ | ✗ | ✗ | ✓ |
