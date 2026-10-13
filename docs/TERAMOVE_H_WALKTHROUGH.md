# TeraMove-H — Walkthrough

This is a short, plain-language guide to the TeraMove-H paper (`paper/main.pdf`), with
every formula it uses. The main focus is **user association**: deciding which AP serves
which user.

Formulas use GitHub/Markdown math. They render on GitHub, in VS Code's Markdown preview,
in Obsidian and in Typora.

---

## Contents

1. [The idea](#1-the-idea)
2. [Setup](#2-setup)
3. [Link model](#3-link-model)
4. [User association (the core)](#4-user-association-the-core)
5. [Power control](#5-power-control)
6. [Escalation and search](#6-escalation-and-search)
7. [Main results](#7-main-results)
8. [Where it lives in the code](#8-where-it-lives-in-the-code)

---

## 1. The idea

THz access points (APs) need line of sight, and the people they serve are also what
blocks them. TeraMove fixed blockage by **moving APs**.

TeraMove-H tries two cheaper fixes first:

1. A **Wi-Fi layer** together with smarter **user association**.
2. **Power control**: idle APs are switched off, and busy APs use less power.

APs move only if these electronic fixes are not enough.

---

## 2. Setup

| Item | Value |
|---|---|
| Building | $32 \times 20 \times 3$ m floor, 12 rooms |
| THz APs | 14 APs from the MILP (Fig. 1); state $\theta_a = (x_a, y_a, z_a, \phi_a, \alpha_a)$ |
| AP height | $z_a \in \{2.0, 2.2, \dots, 3.0\}$ m |
| AP azimuth | $\phi_a$ in $45^\circ$ steps, compass bearing (0° = North, clockwise) |
| Beam width | $\alpha_a \in \{30, 45, 60, 75, 90, 120\}^\circ$ |
| AP movement | along a ceiling rail inside its own room only |
| Wi-Fi APs | 4 fixed ceiling APs, 6 GHz, 160 MHz each, separate channels (no mutual interference) |
| People | 80 % in 6 Gaussian clusters ($\sigma = 1$ m), 20 % uniform; bodies never overlap |
| Body model | cylinder, radius 0.2 m, height 1.6 m |
| Users | each person is an active user with probability 0.5; device at 1.0 m, random facing direction |
| Demand | every user needs at least $R_{\min}$ (default 1 Gb/s) |

---

## 3. Link model

### 3.1 THz path loss (dB)

$$
L_{a,u} = \underbrace{20\log_{10}\!\frac{4\pi f d}{c}}_{\text{free space}}
\;+\; \underbrace{4.343\,k(f)\,d}_{\text{absorption}}
\;+\; \underbrace{L^{\text{st}}_{a,u}}_{\text{walls}}
\;+\; \underbrace{\min\!\big(n_{a,u} L_h,\; L_h^{\max}\big)}_{\text{bodies}}
\;+\; \underbrace{L_{\text{sb}}\,\mathbf{1}^{\text{sb}}_{a,u}}_{\text{own body}}
$$

| Symbol | Meaning | Value |
|---|---|---|
| $f$ | carrier frequency | 300 GHz |
| $d$ | 3-D AP–user distance | — |
| $c$ | speed of light | — |
| $k(f)$ | molecular absorption (ITU-R P.676) | $1.54\times10^{-3}\ \text{m}^{-1}$ (6.68 dB/km) |
| $L^{\text{st}}$ | wall penalty per wall crossed | concrete 30, wood 20, glass 15 dB |
| $n_{a,u}$ | bodies whose circle the ray crosses at height $\le 1.6$ m | — |
| $L_h,\ L_h^{\max}$ | body loss, cap | 20 dB, 40 dB |
| $\mathbf{1}^{\text{sb}}$ | AP lies behind the user's own body (3GPP self-blocking region) | 0 or 1 |
| $L_{\text{sb}}$ | self-blocking loss | 30 dB |

Linear path gain:

$$
\ell_{a,u} = 10^{-L_{a,u}/10}
$$

### 3.2 AP antenna gain (energy conserving)

The main lobe covers the lower half-space within $\pm\alpha/2$ of $\phi_a$. Its solid angle
is $\alpha$ steradians, so

$$
G_m(\alpha) = \frac{4\pi - g_s\,(4\pi - \alpha)}{\alpha},
\qquad g_s = -10\ \text{dBi}\ (\text{side lobe}),\ \alpha \text{ in radians}.
$$

A wider beam gives less gain: **13.4 / 10.4 / 7.4 dBi** for $\alpha$ = 30° / 60° / 120°.

AP gain towards user $u$:

$$
G^{t}_{a,u} =
\begin{cases}
G_m(\alpha_a), & \Delta\phi_{a,u} \le \alpha_a/2\\[2pt]
g_s, & \text{otherwise}
\end{cases}
$$

### 3.3 User device antenna

The device points a $G_r = 20$ dBi pencil beam at its serving AP. The same energy rule fixes
the main-lobe cone, with half-angle $\psi$:

$$
\Omega_r = \frac{4\pi\,(1 - g_r)}{G_r - g_r},
\qquad
\psi = \arccos\!\Big(1 - \frac{\Omega_r}{2\pi}\Big) = 10.9^\circ .
$$

$G^{r}_{u,a,b}$ is the device gain towards AP $b$ when the beam points at AP $a$. It equals
$G_r$ if $b$ lies within $\psi$ of the direction to $a$, and $g_r = -10$ dBi otherwise.

### 3.4 SINR and capacity

Write $h_{b,u} = G^{t}_{b,u}\,\ell_{b,u}$ for the channel gain. Then

$$
\mathrm{SINR}_{u,a} =
\frac{p_a\, h_{a,u}\, G_r}
{N_0 + \displaystyle\sum_{b \ne a} p_b\, h_{b,u}\, G^{r}_{u,a,b}}
$$

$$
N_0 = -174 + 10\log_{10}B + \mathrm{NF} = -174 + 100 + 10 = -64\ \text{dBm}
$$

$$
c_{u,a} =
\begin{cases}
B\,\min\!\big(\log_2(1 + \mathrm{SINR}_{u,a}),\; 6\big), & \mathrm{SINR}_{u,a} \ge \gamma_{\text{th}} = 5\ \text{dB}\\[2pt]
0, & \text{otherwise}
\end{cases}
\qquad B = 10\ \text{GHz}
$$

### 3.5 Wi-Fi link

3GPP InH-Office path loss, with $f_c = 6$ GHz:

$$
\mathrm{PL}_{\text{LOS}} = 32.4 + 17.3\log_{10} d + 20\log_{10} f_c
$$

$$
\mathrm{PL}_{\text{NLOS}} = \max\!\big(\mathrm{PL}_{\text{LOS}},\; 17.3 + 38.3\log_{10} d + 24.9\log_{10} f_c\big)
$$

A link is LOS only if no full-height wall and no body is in the way.

The rate is the 2-stream 160 MHz PHY rate of the highest 802.11ax MCS whose sensitivity is
met, times a MAC efficiency of 0.7. The maximum Wi-Fi rate is about **1.68 Gb/s**.

---

## 4. User association (the core)

### 4.1 Airtime

Every AP time-shares its channel. If user $u$ is served by AP $a$, it needs this share of
the AP's time:

$$
\tau_{u,a} = \frac{R_{\min}}{c_{u,a}}
$$

Each AP can give out at most **1** unit of time in total.

| Link | Capacity | Airtime needed at 1 Gb/s |
|---|---|---|
| Good THz | 40 Gb/s | 0.025 |
| Good Wi-Fi | 1.5 Gb/s | 0.67 (two-thirds of the whole AP) |

### 4.2 Optimisation problem

Let $x_{u,a} = 1$ if user $u$ is served by AP $a$, and 0 otherwise.

$$
\begin{aligned}
\max_{\mathbf{x}}\quad & \sum_{u}\sum_{a} x_{u,a} \\
\text{s.t.}\quad & \sum_{a} x_{u,a} \le 1 && \forall u \quad\text{(at most one AP per user)}\\
& \sum_{u} \tau_{u,a}\, x_{u,a} \le 1 && \forall a \quad\text{(airtime budget)}\\
& x_{u,a} = 0 \ \text{ if } c_{u,a} < R_{\min} && \text{(link too weak)}\\
& x_{u,a} \in \{0,1\}
\end{aligned}
$$

**Satisfaction** is the fraction of users who get at least $R_{\min}$:

$$
S = \frac{1}{|\mathcal{U}|}\sum_{u}\sum_{a} x_{u,a}
$$

This is a **maximum Generalised Assignment Problem (GAP)** in which every user has the same
value. Think of packing items (users) into bins (APs), where an item's size depends on the
bin it goes into.

### 4.3 Why it is hard (Proposition 1)

Deciding whether **all** users can be served is NP-complete. It contains the PARTITION
problem: given integers $s_1,\dots,s_k$ with $\sum_i s_i = 2T$, can they be split into two
halves of equal sum?

Use two APs and choose the capacities so that

$$
c_{u,1} = c_{u,2} = \frac{R_{\min}\,T}{s_u}
\;\;\Rightarrow\;\;
\tau_{u,a} = \frac{s_u}{T}.
$$

Both airtime budgets hold with everyone served **if and only if** the integers split into
two halves that each sum to $T$. So an exact solver is too slow for every evaluation, and we
use a greedy algorithm.

### 4.4 Greedy algorithm (`gap_greedy`)

1. List every usable (user, AP) pair, THz and Wi-Fi together.
2. Sort the pairs by airtime $\tau_{u,a}$, smallest first.
3. Walk down the list. Assign a pair only if the user is still free **and** the AP still
   has enough time left.
4. Users left over are unserved.

The cost is $O(KM\log KM)$ for $K$ users and $M$ APs. Cheapest pairs first leaves room
for the most users. With a single AP this rule is exactly optimal.

#### Worked example ($R_{\min}$ = 1 Gb/s)

| User | THz-A | Wi-Fi |
|---|---|---|
| u1 | 20 Gb/s → $\tau$ = 0.05 | 1.6 Gb/s → $\tau$ = 0.63 |
| u2 | 4 Gb/s → $\tau$ = 0.25 | 1.2 Gb/s → $\tau$ = 0.83 |
| u3 | blocked | 1.5 Gb/s → $\tau$ = 0.67 |

Sorted pairs: (u1,A) 0.05 → (u2,A) 0.25 → (u1,W) 0.63 → (u3,W) 0.67 → (u2,W) 0.83

| Step | Pair | Action | Load A | Load W |
|---|---|---|---|---|
| 1 | (u1, A) | assign | 0.05 | 0 |
| 2 | (u2, A) | assign | 0.30 | 0 |
| 3 | (u1, W) | skip (u1 already served) | 0.30 | 0 |
| 4 | (u3, W) | assign | 0.30 | 0.67 |
| 5 | (u2, W) | skip (u2 already served) | 0.30 | 0.67 |

All 3 users are served, and Wi-Fi is spent only on the blocked user.

### 4.5 Baselines

| Rule | How it decides | Weakness |
|---|---|---|
| **Max-SINR** (old TeraMove) | strongest THz AP; no Wi-Fi | blocked users are lost; ignores load |
| **Threshold offload** | strongest THz AP if $\mathrm{SINR} \ge 5$ dB, else best Wi-Fi | ignores load; cannot pick a second-best THz AP |
| **Greedy GAP** (TeraMove-H) | cheapest airtime first, over all APs | not always optimal (see 4.6) |

### 4.6 How good is the greedy?

It was compared with the exact integer program, solved by HiGHS (`scipy.optimize.milp`),
on **450** instances:

| Check | Result |
|---|---|
| Greedy equals the optimum | **90.9 %** of instances |
| Worst case | 92.4 % of the optimum (5 users short) |
| Median time: greedy vs exact | **0.29 ms** vs 32.9 ms |

### 4.7 When association matters

Gain of the greedy GAP over threshold offload, in satisfaction:

| $R_{\min}$ (Gb/s) | 0.1 | 0.25 | 0.5 | 1 | 2 |
|---|---|---|---|---|---|
| GAP − offload (pp) | +1.5 | +1.9 | +1.3 | +0.8 | 0.0 |

* **Low demand.** Each Wi-Fi AP can carry many users, so sharing its time wisely pays off.
  At 0.1 Gb/s, re-association alone serves **93.2 %** of users, and **78 %** of crowd
  snapshots need no AP movement at all.
* **High demand.** One Wi-Fi AP tops out at 1.68 Gb/s, so it carries about one user at
  1 Gb/s. There is little left to allocate, and the rule barely matters.

---

## 5. Power control

### 5.1 Sleep

Any THz AP with no users is switched off ($p_a = 0$), and users are re-associated. This
repeats for up to 3 rounds. A round is kept only if $S$ does not drop.

### 5.2 Turn spare airtime into lower power

AP $a$'s airtime load is

$$
L_a = \sum_{u \in \mathcal{U}_a} \tau_{u,a} \le 1 .
$$

If every user's time is stretched by $1/L_a$, the user still gets $R_{\min}$ with a lower
capacity:

$$
c^\star_u = c_{u,a}\,L_a
\qquad\Rightarrow\qquad
\gamma_u = \max\!\big(\gamma_{\text{th}},\; 2^{\,c^\star_u / B} - 1\big)
\quad\text{(target SINR)}
$$

### 5.3 Yates minimum-power iteration

$$
I_a(\mathbf{p}) = \max_{u \in \mathcal{U}_a}
\frac{\gamma_u\Big(N_0 + \sum_{b \ne a} p_b\, h_{b,u}\, G^{r}_{u,a,b}\Big)}{G_r\, h_{a,u}}
$$

$$
\mathbf{p} \;\leftarrow\; \min\!\big(\mathbf{I}(\mathbf{p}),\; P_{\max}\big),
\qquad P_{\max} = 20\ \text{dBm}
$$

**Proposition 2.** $\mathbf{I}$ is a *standard interference function*:

| Property | Holds because |
|---|---|
| Positive | $N_0 > 0$ |
| Monotone | all coupling terms are $\ge 0$ |
| Scalable: $\mu\,\mathbf{I}(\mathbf{p}) > \mathbf{I}(\mu\mathbf{p})$ for $\mu > 1$ | the $N_0$ term does not scale with $\mu$ |

At the current powers $\mathbf{p}^0$, every served user already meets its target, so
$\mathbf{I}(\mathbf{p}^0) \le \mathbf{p}^0$. Starting from there, the iteration only goes
**down** and converges to the minimum power vector $\mathbf{p}^\star$.

At $\mathbf{p}^\star$, every served user keeps $R_{\min}$ and no AP exceeds its airtime
budget:

$$
c_u \ge c^\star_u
\;\Rightarrow\;
\frac{R_{\min}}{c_u} \le \frac{\tau_{u,a}}{L_a}
\;\Rightarrow\;
\sum_{u} \frac{R_{\min}}{c_u} \le 1 .
$$

**Result:** THz power drops from **1.40 W to 0.53 W (−62.1 %)**, with about 4 of the 14 APs
switched off. Satisfaction is unchanged.

---

## 6. Escalation and search

The stages run in order and stop at the first one that reaches $S \ge \eta = 0.9$:

| Stage | What it does | Physical cost |
|---|---|---|
| **T0** | greedy GAP over THz + Wi-Fi at full power | none |
| **T1** | sleep + re-associate + minimum power | none |
| **T2** | genetic algorithm (GA) over azimuth $\phi$ and width $\alpha$ (1 budget unit) | none |
| **M** | GA over height, position within the room and beams (3 units), then Hungarian matching per room | movement |

One budget unit is $40 \times 40 = 1600$ fitness evaluations. Final power control always
runs at the end.

### Fitness used by the search

$$
F = 0.6\,S + 0.4\,Q + 0.5\cdot\mathbf{1}[S \ge \eta] - \beta M - \gamma C_p
$$

$$
Q = \frac{1}{|\mathcal{U}|}\sum_u \min\!\Big(1,\; \frac{\max_a c_{u,a}}{R_{\min}}\Big)
\qquad\text{(smooth link quality)}
$$

$$
M = \frac{\sum_a \big\lVert (x_a, y_a, z_a) - (x^0_a, y^0_a, z^0_a) \big\rVert}{|\mathcal{T}| \cdot \text{building diagonal}}
$$

$$
C_p = \frac{1}{\binom{n}{2}} \sum_{i<j} \max\!\Big(0,\; 1 - \frac{d_{ij}}{d_{\min}}\Big),
\qquad d_{\min} = 3\ \text{m}
$$

with $\beta = 0.25$ and $\gamma = 0.3$ (TeraMove configuration D).

### Hungarian matching

New AP states are matched to physical APs inside each room so that total movement is
minimal:

$$
\sigma^\star = \arg\min_{\sigma} \sum_i C_{i,\sigma(i)},
\qquad
C_{ij} = \big\lVert \mathbf{r}_i - \mathbf{r}'_j \big\rVert
$$

### Commissioning

The MILP layout's beams and heights were re-tuned once for the empty floor; the positions
did not change. Empty-floor coverage rose from **66.2 % to 100 %**.

---

## 7. Main results

30 seeds, $R_{\min}$ = 1 Gb/s, 120 people.

| Method | Users satisfied $S$ | AP movement |
|---|---|---|
| Static (no adaptation) | 44.8 % | 0 m |
| Old TeraMove | 50.9 % | 11.8 m |
| Re-association only (T0) | 51.6 % | 0 m |
| T0–T2 (no movement) | 58.9 % | 0 m |
| THz only (no Wi-Fi) | 77.2 % | 25.8 m |
| Threshold offload | 83.0 % | 23.3 m |
| **TeraMove-H** | **84.4 %** | **24.6 m** |
| Flat GA (all dimensions at once) | 87.2 % | 30.3 m |

The flat GA satisfies 2.8 pp more users but moves APs about 23 % more. That is a
trade-off, not a win for either method.

---

## 8. Where it lives in the code

| File | What is in it |
|---|---|
| `teramove_h/association.py` | `gap_greedy`, `gap_exact`, `max_sinr_pref`, `naive_offload_pref` |
| `teramove_h/evaluator.py` | association → sleep → power control pipeline |
| `teramove_h/power.py` | SINR targets $\gamma_u$ and the Yates iteration |
| `teramove_h/network.py` | SINR and capacity for every (user, AP) pair |
| `teramove_h/antenna.py` | energy-conserving gains $G_m(\alpha)$ and $\psi$ |
| `teramove_h/channel.py` | ray geometry, walls, bodies, self-blocking, Wi-Fi rates |
| `teramove_h/cascade.py` | escalation stages T0 → T1 → T2 → M, and every baseline |
| `paper/main.tex` | Sec. III (model), Sec. IV-B (association), Sec. V (results) |
