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
need a fast algorithm: the simple greedy (baseline) and **PACE** (proposed).

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

### 4.5 Where the greedy goes wrong

The greedy looks only at airtime. A user who has **other options** can take the last
airtime of an AP that another user **cannot do without**.

| User | AP A | AP B |
|---|---|---|
| u1 | $\tau$ = 0.4 | $\tau$ = 0.5 |
| u2 | $\tau$ = 0.7 | blocked |

* Greedy: (u1, A) is cheapest, so u1 takes A (load 0.4). u2 needs 0.7 more on A, and
  0.4 + 0.7 > 1, so u2 is lost. **1 user served.**
* Optimum: u1 on B, u2 on A. **2 users served.**

This is the "corner case" in its smallest form. In real instances it happens on crowded
Wi-Fi APs and on THz APs that serve the edge of a crowd.

### 4.6 PACE: the proposed association algorithm

**PACE** = **P**rice-guided **A**ssociation with **C**ertified **E**jection chains
(`gap_pace` in `teramove_h/association.py`). It has four parts.

#### (a) Slot cuts: how many users can an AP hold at most?

Sort AP $a$'s airtimes from small to large. $K_a$ is the largest $n$ with

$$
\tau_{(1),a} + \tau_{(2),a} + \dots + \tau_{(n),a} \le 1 .
$$

Then every feasible association satisfies

$$
\sum_u x_{u,a} \le K_a \qquad \forall a .
$$

> **Why:** any $n$ users on AP $a$ need at least the $n$ smallest airtimes. If those
> already exceed 1, $n$ users cannot fit.
>
> **Why it helps:** the fractional (LP) version of the problem ignores this. At 1 Gb/s a
> Wi-Fi AP ($\le$ 1.68 Gb/s, so $\tau \ge 0.6$) holds **one** user, but the fractional
> budget "holds" 1.68 users. The cut removes that fake capacity, so the upper bound in (b)
> becomes tight.

#### (b) Airtime prices and an upper bound (Lagrangian dual)

Give each AP an **airtime price** $\lambda_a \ge 0$ and a **slot price** $\nu_a \ge 0$.
For any prices,

$$
L(\boldsymbol\lambda,\boldsymbol\nu)=\sum_a\big(\lambda_a+K_a\nu_a\big)
+\sum_u \max\Big(0,\ \max_a\big(1-\lambda_a\tau_{u,a}-\nu_a\big)\Big).
$$

> **Meaning:** each user "buys" the AP with the lowest price $\lambda_a\tau_{u,a}+\nu_a$
> and joins only if that price is below 1 (its value). A crowded AP gets a high price,
> so flexible users are pushed away from it.

**Proposition 3 (upper bound).** For **any** prices, no association serves more than
$\lfloor L(\boldsymbol\lambda,\boldsymbol\nu)\rfloor$ users.

> **Why (3 lines):** take any feasible $\mathbf{x}$. Add the non-negative leftovers
> $\lambda_a(1-\sum_u\tau_{u,a}x_{u,a})$ and $\nu_a(K_a-\sum_u x_{u,a})$ to the count
> $\sum x_{u,a}$; it can only grow. Rearranged, every user contributes at most its best
> "value minus price", which is the max term in $L$. The count is an integer, so take the
> floor.

**Certificate.** If PACE serves $n$ users and finds prices with $L < n+1$, then
$n$ is **provably optimal**. No exact solver is needed.

> **Why it is strong:** the user constraints ($\sum_a x_{u,a}\le1$) form an integral
> polytope, so the best $L$ equals the LP relaxation **with slot cuts** (Geoffrion 1974).
> On the 1,800 test instances, the rounded-down plain LP equals the optimum in only
> 35.7 % of cases, but with slot cuts in 94.8 % (never more than
> 2 users above the optimum). That is why the certificate fires so often.

The prices are improved by **subgradient steps** (Held, Wolfe and Crowder 1974):

$$
g^{\lambda}_a = 1-\sum_{u\to a}\tau_{u,a},\qquad
g^{\nu}_a = K_a-\big|\{u\to a\}\big|,
$$

$$
(\boldsymbol\lambda,\boldsymbol\nu) \leftarrow
\max\!\Big(0,\ (\boldsymbol\lambda,\boldsymbol\nu)-\vartheta\,\frac{L-(n+\tfrac12)}{\lVert\mathbf g\rVert^2}\,\mathbf g\Big),
$$

where $u\to a$ are the users whose cheapest AP is $a$.

> **Why:** if an AP is over-booked ($g<0$), its price goes **up**; if it has spare
> time ($g>0$), its price goes **down**. It is supply and demand. $\vartheta$ starts at 1
> and halves after 20 steps without progress.

#### (c) Price-guided restarts

Every 5 price steps, PACE re-runs the greedy, but sorts the pairs by **priced cost**
$\lambda_a\tau_{u,a}+\nu_a$ instead of raw airtime (ties by airtime). With all prices at 0,
this is exactly the old greedy.

> **Why:** the prices encode which APs are scarce, which the greedy cannot see. Each
> price vector gives a different, smarter order, and PACE keeps the best result.

#### (d) Ejection chains

An unserved user $u$ gets in by pushing someone along:

* **depth 1:** $u$ enters AP $a$ by displacing $v$; $v$ moves to an AP $b$ that has room;
* **depth 2:** $v$ instead displaces $w$ at $b$, and $w$ moves to a third AP $c$.

> **Why:** each chain serves **one more** user and drops nobody. It is the GAP version of
> an augmenting path in matching (Yagiura, Ibaraki and Glover 2004). In the example in 4.5,
> one depth-1 chain fixes the greedy: u2 enters A, u1 moves to B.

#### The full algorithm

1. Run the greedy and depth-1 chains. This serves $n$ users.
2. Repeat up to 200 times:
   * compute $L$ at the current prices;
   * **stop** if the best $L < n+1$ (optimal, certified);
   * every 5 steps, run a price-guided restart; keep it if it serves more users;
   * take one subgradient step on the prices.
3. If no certificate was found, apply depth-2 chains.
4. Move served users to an AP with smaller airtime when it fits. The count stays the same,
   and less airtime is used.

**Guarantees:**

* **Never worse than greedy.** PACE starts from the greedy solution and keeps a new one
  only if it serves strictly more users.
* **Always feasible.** Every move checks the airtime budget with the same tolerance as the
  greedy.
* **Honest bound.** Even without a certificate, $\lfloor L\rfloor$ is a valid upper bound,
  so the remaining gap is known.

**Can it guarantee that every user is served?** No algorithm can, when capacity is
short. PACE instead **proves** when it is impossible: if $\lfloor L\rfloor < k$, no
association can serve all $k$ users. TeraMove-H uses this at T0. When the bound shows that
the target $\eta$ is unreachable at the current geometry, moving APs is necessary, not a
failure of the association algorithm.

### 4.7 Baselines

| Rule | How it decides | Weakness |
|---|---|---|
| **Max-SINR** (old TeraMove) | strongest THz AP; no Wi-Fi | blocked users are lost; ignores load |
| **Threshold offload** | strongest THz AP if $\mathrm{SINR} \ge 5$ dB, else best Wi-Fi | ignores load; cannot pick a second-best THz AP |
| **Greedy GAP** (ablation) | cheapest airtime first, over all APs | blind to scarcity (see 4.5) |
| **PACE** (TeraMove-H) | prices + restarts + ejection chains, from the greedy start | slower (below 1 ms median) |

### 4.8 How good are greedy and PACE?

Both were compared with the exact integer program (HiGHS, `scipy.optimize.milp`) on
**1800** instances: 4 crowd sizes × 5 demands × 3 AP configurations × 30 seeds.

| Check | Greedy | PACE |
|---|---|---|
| Equals the exact optimum | 84.1 % | **99.4 %** |
| Users short of the optimum (all instances) | 483 | **12** |
| Worst instance | 7 users short (87.0 % of optimum) | 2 users short (96.6 % of optimum) |
| Optimality proved by its own bound | — | 82.3 % (never wrong) |
| Median time | 0.27 ms | 0.62 ms (exact ILP: 34.0 ms) |

PACE serves more users than the greedy in 282 instances and fewer in none.

Per demand:

| $R_{\min}$ (Gb/s) | 0.1 | 0.25 | 0.5 | 1 | 2 |
|---|---|---|---|---|---|
| Greedy optimal (%) | 56.7 | 74.7 | 89.2 | 100 | 100 |
| PACE optimal (%) | 97.2 | 99.7 | 100 | 100 | 100 |
| PACE certified (%) | 56.4 | 70.6 | 84.7 | 100 | 100 |
| Users short, greedy | 320 | 123 | 40 | 0 | 0 |
| Users short, PACE | 11 | 1 | 0 | 0 | 0 |

The greedy fails only at low demand. There, each AP holds many users and the packing
gets tight. At 1 and 2 Gb/s, an AP holds only a few users, and greedy, PACE and the
optimum all coincide.

### 4.9 When association matters (in the full system)

Same seeds, same crowds, same search; only the association algorithm differs (PACE /
greedy):

| $R_{\min}$ (Gb/s) | 0.1 | 0.25 | 0.5 | 1 | 2 |
|---|---|---|---|---|---|
| T0 $S$ (%) | 94.2 / 93.2 | 73.2 / 72.8 | 60.8 / 60.3 | 48.7 / 48.7 | 41.7 / 41.7 |
| Final $S$ (%) | 98.3 / 98.0 | 92.5 / 92.4 | 86.1 / 85.9 | 80.4 / 80.3 | 75.1 / 75.2 |
| No movement (%) | 80 / 78 | 33 / 30 | 20 / 19 | 2 / 2 | 0 / 0 |
| Displacement (m) | 3.8 / 4.5 | 15.5 / 16.1 | 19.1 / 18.7 | 22.3 / 22.4 | 25.8 / 26.1 |

* **T0** uses the same AP positions for both, so its difference is purely the association
  algorithm: **+1.0 pp** at 0.1 Gb/s (+2.7 pp with 180 people).
* After T0 the GA moves APs and repairs most association mistakes, so the **final** gain is
  small: +0.3 pp at 0.1 Gb/s (p = 0.01, significant) and not significant at higher demand.
* The real benefit is **less movement**: at 0.1 Gb/s, 80 % instead of 78 % of snapshots
  need no movement, and displacement drops from 4.5 m to 3.8 m (about −16 %).
* **Cost:** about 2.5× longer per snapshot at 0.1 Gb/s, because PACE runs inside every
  fitness evaluation.
* **Certified escalation:** in 457 snapshots T0 fell short of η = 0.9. In **98.7 %** of
  them the PACE bound proves that no association at the starting geometry could reach η, so
  the movement was truly necessary.

Gain of PACE over threshold offload, in satisfaction:

| $R_{\min}$ (Gb/s) | 0.1 | 0.25 | 0.5 | 1 | 2 |
|---|---|---|---|---|---|
| PACE − offload (pp) | +1.8 | +2.0 | +1.5 | +0.9 | −0.1 (not significant) |

* **Low demand.** Each Wi-Fi AP can carry many users, so sharing its time wisely pays off.
  At 0.1 Gb/s, re-association alone serves **94.2 %** of users, and
  **80 %** of crowd snapshots need no AP movement at all.
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

**Proposition 4 (paper numbering).** $\mathbf{I}$ is a *standard interference function*:

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
| **T0** | PACE association over THz + Wi-Fi at full power | none |
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
| TeraMove-H with greedy association | 84.4 % | 24.6 m |
| **TeraMove-H (PACE)** | **84.4 %** | **24.7 m** |
| Flat GA (all dimensions at once) | 87.3 % | 30.4 m |

At 1 Gb/s greedy is already optimal, so PACE and greedy give the same satisfaction here;
PACE's gains appear at lower demand (Section 4). The flat GA satisfies 2.9 pp more users but
moves APs about 23 % more. That is a
trade-off, not a win for either method.

---

## 8. Where it lives in the code

| File | What is in it |
|---|---|
| `teramove_h/association.py` | `gap_pace` (proposed), `gap_greedy`, `gap_exact`, `slot_limits`, `gap_lp_bound`, `max_sinr_pref`, `naive_offload_pref` |
| `teramove_h/evaluator.py` | association → sleep → power control pipeline |
| `teramove_h/power.py` | SINR targets $\gamma_u$ and the Yates iteration |
| `teramove_h/network.py` | SINR and capacity for every (user, AP) pair |
| `teramove_h/antenna.py` | energy-conserving gains $G_m(\alpha)$ and $\psi$ |
| `teramove_h/channel.py` | ray geometry, walls, bodies, self-blocking, Wi-Fi rates |
| `teramove_h/cascade.py` | escalation stages T0 → T1 → T2 → M, and every baseline |
| `paper/main.tex` | Sec. III (model), Sec. IV-B (association), Sec. V (results) |
