# TeraMove-H — Work Report

This report covers what was implemented, tested, run and written for the TeraMove-H
extension. It also lists every problem found in the earlier material and every point
where the work departs from `docs/PLAN.md`.

All numbers in Sections 7–8 are copied from `paper/numbers.tex`. That file is generated
by `plots/make_paper_assets.py` from the raw results in `results/*.json`.

---

## 1. Summary

* **What it is.** A new package, `teramove_h/` (about 1,450 lines; experiments, plots and tests add about 1,180 more). It has a corrected
  physical model, a hybrid THz + Wi-Fi network, airtime-aware user association (a
  maximum generalised assignment problem, solved greedily and checked against an exact
  solver), minimum-power control (Yates' framework), and an escalation that goes
  re-associate → power → beams → mechanical. Every baseline and ablation lives in one
  pipeline.
* **Tests.** 42 pytest tests (37 for TeraMove-H, 5 for the corrected legacy simulator).
  All pass.
* **Experiments.** Six experiments with 30 seeds each, run with common random numbers
  and reported with 95 % confidence intervals and Wilcoxon tests.
  Raw outputs are in `results/`.
* **Paper.** An IEEE conference paper, `paper/main.pdf`, built with IEEEtran.
  Every number, table and figure in it is generated from `results/`.
* **MILP.** The placement MILP was **not** re-run. Its Fig. 1 layout (14 APs) is used as
  given.

## 2. Material reused

| Material | How it was used |
|---|---|
| `MILP.pdf` Fig. 1 | The 14 AP coordinates, heights and azimuths, hard-coded in `teramove_h/geometry.py::MILP_LAYOUT`. They match `main.py` exactly. |
| `chsr_sim/environment.py::gen_walls` | Floor plan, imported unchanged. |
| `chsr_sim/optimizer.py` | PSO update rule, tier locking, velocity limits, fitness structure, anti-clustering penalty and Hungarian step, re-implemented in `teramove_h/optimizer.py`. |
| `THZ_Placement-2.pdf` (TeraMove) | Cascade idea, fitness weights of configuration D (beta = 0.25, gamma = 0.3), 5 dB SINR threshold, P_max = 20 dBm. |
| `com.txt` (earlier review) | Defects 2, 3 and 8 of that review are fixed here; see Section 3. |

## 3. Problems found in the earlier code and papers

| # | Problem | Evidence | Status |
|---|---|---|---|
| D1 | **Azimuth convention.** The MILP gives azimuths "from North" (compass). The simulator uses `atan2` from +x. The Fig. 1 APs at 135° therefore point *out of the building*. | Legacy simulator, empty floor: 43.9 % coverage (as implemented) vs 60.8 % (correct compass reading). See `results/legacy.json`. | Fixed: compass everywhere, unit-tested. |
| D2 | The main-lobe gain was 30 dBi for every beamwidth from 30° to 120°, which violates energy conservation. | `chsr_sim/physics.py:96` | Fixed: exact flat-top normalisation. A test integrates the pattern over the sphere and gets 4π. |
| D3 | Molecular absorption k = 0.05 m⁻¹ (217 dB/km), about 33× too high. | ITU-R P.676 via ITU-Rpy: 6.68 dB/km at 300 GHz, 23 °C, 10 g/m³. | Fixed. |
| D4 | Noise floor is −94 dBm in the TeraMove paper but −64 dBm in the code. | Paper Table II vs `config.py` | Fixed: N0 = −174 + 10 log10(10 GHz) + 10 dB = −64 dBm, used consistently. |
| D5 | Users sit at integer grid corners, i.e. on top of the walls at y = 10, y = 12 and x = 0. | `range(LENGTH)` loops | Fixed: users are people; the coverage grid uses cell centres. |
| D6 | Blockage is fractional density × 20 dB, summed over coarsely sampled cells, with no cap and averaged in dB. | `physics.py:66-77` | Fixed: discrete cylinder bodies with an exact chord test, capped at 40 dB. Monte Carlo over crowds gives the expectation in the correct domain. |
| D7 | **The PSO/GA comparison figures (TeraMove Figs. 5–6) are hard-coded numbers.** The repo has no PSO or GA baseline implementation. The "30 Monte Carlo runs" claim is unsupported. | `generate_comparison_plots.py:26-58`, `generate_paper_figures.py:326-333` | Real flat-PSO and flat-GA baselines added. Real runs show the GA is *better* than PSO on this problem (Section 7). |
| D8 | Swarm size in the paper (S = 50, T = 20) differs from the code (200 × 200). | `config.py` | One parameter set (40 × 40), printed from code. |
| D9 | The Tier-4 cache is keyed by continuous positions and grows without bound (about 5.6 GB at 200 × 200). | `physics.py:180` | Fixed: positions on a 0.25 m rail grid, bounded LRU cache. |
| D10 | APs may move through walls. | `decode_routers` | Fixed: each AP stays in its room (per-room ceiling rail); Hungarian matching runs per room. |
| D11 | The 1 m cubicles never block anything. Rays from a ceiling AP to a 1.0 m device never go below 1.0 m, so the MILP claim of "routing over cubicles" holds trivially. | Geometry | Documented in the paper. |
| D12 | `reviewer_response/reviewer_defense.md` claims configuration D collapses to 78.4 % in dynamic tracking. The submitted paper instead *adopts* configuration D at 95.2 %. | File vs paper Table IV | Not used. Flagged for the team. |
| D13 | No MILP code in the repository. | grep | MILP not needed; layout taken from Fig. 1. |
| D14 | The PSO in TeraMove is called "Adaptive"/"Hierarchical", but its update rule is the standard linear-inertia rule (Shi & Eberhart). | `optimizer.py` | The new paper calls it PSO with tiers. |

**Consequence for the PerCom paper.** D1 means the TeraMove initial layout was
mis-oriented, so its 63.6 % / 16.6 % starting coverages come from that error. D7 means its
Figs. 5–6 must be regenerated from simulation or removed. The new code can produce real
versions of both.

## 4. Model decisions (all in `teramove_h/config.py`)

| Element | Choice | Source |
|---|---|---|
| THz band | 300 GHz, B = 10 GHz, NF 10 dB, N0 = −64 dBm, P_max 20 dBm | TeraMove; kT B NF |
| Absorption | 6.677 dB/km (k = 1.54e-3 m⁻¹) | ITU-R P.676, computed with ITU-Rpy 0.4.0 |
| Walls | 30 / 20 / 15 dB (concrete / wood / glass) | MILP Table II |
| Bodies | cylinders r = 0.2 m, h = 1.6 m; 20 dB each, capped at 40 dB | MILP h_human and L_h |
| Self-blocking | 3GPP TR 38.901 §7.6.4.1 portrait mode, 30 dB | 3GPP |
| AP antenna | flat-top sector over the lower half-space, G_m(α) = (4π − g_s(4π − α))/α, g_s = −10 dBi | energy conservation (exact) |
| UE antenna | 20 dBi pencil beam steered to the serving AP; half-angle 10.9° from the same normalisation | Rappaport et al. 2019 (array sizes) |
| Rate | B·min(log2(1 + SINR), 6); usable iff SINR ≥ 5 dB | TeraMove threshold, 64-QAM cap |
| Wi-Fi | 6 GHz, 160 MHz, 2 spatial streams, 802.11ax MCS sensitivity table + 9 dB, MAC efficiency 0.7, 3GPP InH-Office LOS/NLOS | IEEE 802.11ax, 3GPP 38.901 |
| Crowd | 80 % in 6 Gaussian clusters (σ = 1 m) + 20 % uniform background; hard-core 0.4 m; 0.25 m wall clearance; 50 % of people are active users | Thomas-type clusters (Haenggi) |
| Service | per-AP airtime sharing, demand R_min per user | — |

**Assumptions that are not from a cited source** (each is stated in the paper):
* MAC efficiency 0.7.
* Wi-Fi AP positions at the room centres.
* Rail speed 0.2 m/s (affects the latency figure only).
* 40 dB cap on body loss.
* Users' facing direction is known to the optimiser.
* Interference assumes every AP that is switched on transmits continuously.
* Line of sight only (no reflections).

## 5. Implementation

See `docs/TERAMOVE_H_README.md` for the file map and reproduction commands. Main points:

* **Inner problem** (`evaluator.py`):
  1. Greedy GAP at P_max.
  2. Switch off idle APs and re-associate, for at most 3 rounds, each kept only if S does
     not drop.
  3. Yates minimum-power iteration, with a run-time re-check that every served user still
     gets R_min and every airtime budget still holds. The code raises an error otherwise;
     this never fired across all runs.
* **Search** (`optimizer.py`): PSO tiers, plus a GA that can search all dimensions (flat)
  or only one tier's dimensions. The current configuration is always seeded into the
  population, so a stage never returns a worse fitness. Hungarian matching runs per room.
* **Escalation** (`cascade.py`):
  * T0: re-associate.
  * T1: switch off idle APs, re-associate, minimum power.
  * T2: GA over beams only, 1 budget unit.
  * M: GA over all dimensions, 3 budget units.
  * A stage's result is kept only if S does not drop.
  * One budget unit is 40 × 40 = 1,600 evaluations. The flat baselines get the same
    worst case of 4 units.
* **Commissioning** (`experiments/common.py`): the MILP layout's beams and heights are
  re-tuned for the empty building under the corrected model, with positions unchanged.
  This takes empty-floor coverage from 66.2 % to 100 %.

## 6. Experiments

| ID | Experiment | Size | Wall time (22 workers) | File |
|---|---|---|---|---|
| E1 | Legacy simulator: both azimuth readings; corrected model before and after commissioning | 4 rows | 2 s | `results/legacy.json` |
| E2 | Main comparison: 11 methods, 120 people, R_min = 1 Gb/s | 30 seeds × 11 | 328 s | `results/main.json` |
| E3 | Regime map: R_min ∈ {0.1, 0.25, 0.5, 1, 2} Gb/s × {60, 120, 180, 240} people; 4 methods | 2,400 runs | 2,291 s | `results/regime.json` |
| E4 | Temporal: 6 epochs of drifting crowds; 4 methods | 30 seeds × 4 × 6 | 965 s | `results/temporal.json` |
| E5 | Association: greedy vs exact ILP (HiGHS) | 450 instances | 4 s | `results/assoc.json` |
| E6 | Sensing error σ ∈ {0, 0.25, 0.5, 1} m | 30 seeds × 4 | 118 s | `results/sensing.json` |

Statistics:
* Every method sees the same crowd per seed and uses the same optimiser random stream
  (common random numbers), so comparisons are paired.
* Means are reported with Student-t 95 % confidence intervals.
* Paired differences are tested with the Wilcoxon signed-rank test.

Reproducibility: three runs from E2 were repeated from scratch and matched the stored
results bit-for-bit.

## 7. Results

Main comparison (E2), from `paper/tables/main.tex`:

| Method | S (%) | Displacement (m) | THz power (W) | APs off | Evaluations |
|---|---|---|---|---|---|
| Static | 44.8 ± 3.1 | 0.0 | 1.40 | 0.0 | 0 |
| Wi-Fi only | 6.8 ± 0.2 | 0.0 | 0.00 | 14.0 | 0 |
| TeraMove (published method, corrected physics) | 50.9 ± 2.5 | 11.8 | 1.40 | 0.0 | 4800 |
| THz-only cascade | 77.2 ± 2.5 | 25.8 | 0.55 | 4.2 | 6400 |
| Threshold offload | 83.0 ± 2.8 | 23.3 | 0.51 | 4.3 | 6400 |
| Flat PSO | 78.3 ± 2.5 | 22.4 | 0.45 | 4.4 | 6400 |
| Flat GA | 87.2 ± 2.6 | 30.3 | 0.61 | 4.0 | 6400 |
| TeraMove-H with HPSO tiers | 75.0 ± 2.5 | 13.5 | 0.43 | 4.5 | 6400 |
| TeraMove-H without power control | 84.4 ± 2.6 | 24.6 | 1.40 | 0.0 | 6400 |
| TeraMove-H without movement | 58.9 ± 2.6 | 0.0 | 0.36 | 4.9 | 1600 |
| **TeraMove-H** | **84.4 ± 2.6** | **24.6** | **0.53** | **4.1** | 6400 |

Main comparison, interpreted:
* **Against the starting points.** TeraMove-H beats the static network by 39.6 pp and the
  original TeraMove by 33.5 pp.
* **Wi-Fi.** The Wi-Fi layer adds 7.2 pp over the THz-only cascade.
* **Power control.** It cuts THz power by 62.1 % and leaves satisfaction and displacement
  exactly unchanged. This is what Proposition 2 predicts, and the common random numbers
  make it visible.
* **Flat GA (honest finding).** The flat GA satisfies 2.8 pp more users (p = 0.02) but
  moves APs 18.8 % more (p = 0.007). Neither dominates: it is a Pareto trade-off.
* **PSO vs GA.** Under equal budgets the GA beats PSO (78.3 % flat PSO, 75.0 % with HPSO
  tiers). This contradicts the hard-coded TeraMove figure (defect D7).

Regime map (E3):
* At 0.1 Gb/s, re-association alone serves 93.2 % of users, and 78 % of snapshots reach
  η = 0.9 without any movement.
* At 2 Gb/s, re-association serves 41.7 %, and no snapshot is resolved without movement.
* GAP minus threshold offload: +1.5 / 1.9 / 1.3 / 0.8 / 0.0 pp across the five demands.
* Without Wi-Fi, satisfaction is flat in demand up to 1 Gb/s. A THz AP's capacity far
  exceeds its users' demand, so coverage alone limits service.
* Over the whole grid, TeraMove-H moves APs 24.2 % less than the flat GA.

Temporal (E4):

| Method | S (%) | Cumulative displacement (m) |
|---|---|---|
| TeraMove-H | 87.9 | 77.2 |
| Flat GA | 90.3 | 98.0 |
| TeraMove | 53.9 | 61.7 |
| Static | 43.0 | — |

Under TeraMove-H, 32.0 % of users served in consecutive epochs change their serving AP,
and 10.4 % switch between THz and Wi-Fi.

Association (E5): the greedy is optimal in 90.9 % of instances. Its worst case is 92.4 % of
the optimum (5 users short). It takes 0.29 ms against 32.9 ms for the exact ILP.

Sensing (E6):

| σ (m) | 0 | 0.25 | 0.5 | 1 |
|---|---|---|---|---|
| S (%) | 84.4 | 68.0 | 63.7 | 62.7 |

**This sensitivity is high, and the paper says so.** The method needs decimetre-level
position context, or a robust search (future work).

Exposure: the maximum THz EIRP is 33.4 dBm. That gives 0.69 W/m² at 0.5 m, below the
ICNIRP 2020 general-public whole-body level of 10 W/m².

## 8. Deviations from `docs/PLAN.md`

| Plan | What was done | Why |
|---|---|---|
| Swarm search inside each tier is HPSO (TeraMove) | GA inside each search stage; HPSO kept as an ablation | With equal fitness and budget, the GA was consistently better (pilot on 12 seeds, then confirmed in E2). |
| Tiers T2 → T3 → T4 | T2 (beams, 1 unit) → M (all dimensions, 3 units) | Splitting the budget across restricted tiers lost 4–9 pp of satisfaction against a flat search with the same budget. The merged mechanical stage keeps the "electronic first" logic. |
| Exposure caps in power control | Exposure checked only | With the energy-conserving antenna, the worst-case power density is about 15× below the ICNIRP level, so a cap never binds. The reviewer's earlier exposure concern came from the unphysical 30 dBi sector. |
| 13 rooms | 12 rooms | Counting error in the plan. |
| MILP layout used as-is | MILP positions kept; beams and heights commissioned for the empty floor (66.2 % → 100 % coverage) | The MILP's antenna/channel model differs from the corrected one. |
| Method-specific random streams | Common random numbers | Paired comparisons. Without them, the no-power-control ablation differed only through the random stream. |
| Regime methods: proposed, GA, THz-only | Threshold offload added | To test association at low demand. |

## 9. Paper verification

* Every number in the text comes from a macro in `paper/numbers.tex`.
  Every table is generated from the results (`paper/tables/*.tex`).
  Every figure is generated from `results/*.json`. No number is typed by hand.
* Derived differences (pp gains, percentage reductions) are computed from the rounded
  values printed in the tables. A reader who recomputes them gets the same digits.
* Each paper statement about the method was checked against the code:
  * stage order;
  * budgets (1 + 3 units; flat 4 units; TeraMove 3 × 1 unit);
  * the flat baselines also run T0/T1;
  * GA parameters;
  * sleep rounds (at most 3);
  * the 1e-6 numerical margin;
  * Hungarian matching per room;
  * Wi-Fi AP positions.
* Proposition 1 is a reduction from PARTITION. Proposition 2's proof uses Yates' standard
  interference function. The power cap never binds because the iterates are
  non-increasing from p⁰ ≤ P_max.
* The paper compiles without errors or overfull boxes. The only warnings are the XeTeX
  `TU/ptm` font-substitution notices from the IEEEtran class; the body text is Times
  (TeX Gyre Termes).
* Seven pages including references.

## 10. Open items for the team (cannot be done by code)

1. **Authorship.** The author block uses placeholders (Author 1–3, IIT Bhilai, as in the
   MILP paper). The MILP and TeraMove papers are cited as the team's own B.Tech. project
   manuscripts. Replace the placeholders with your names.
2. **TeraMove project paper.** Done. The corrected version is
   `teramove_paper/main.pdf`, built from the corrected simulator and real runs. See
   Section 12 and `teramove_paper/CHANGES.md`.
3. **Bibliographic details.** For three references the author list is shortened to
   "et al." because I could not verify every co-author. Please verify:
   * the 802.11ax sensitivity table (MCS0–9 from 802.11-2020 Table 21-25; MCS10/11
     −54/−52 dBm);
   * the 3GPP self-blocking parameters;
   * the ICNIRP 10 W/m² level.
4. **Venue.** Not applicable for now (project only). If the team submits later, check that venue's page limit and review rules. The paper is 7 pages.
5. **Weakest points a reviewer will attack:**
   * sensitivity to sensing error;
   * line of sight only;
   * Wi-Fi without shadow fading;
   * the flat GA attaining higher satisfaction;
   * the full-buffer interference assumption.
   All are stated in Sec. VI of the paper.

## 11. Reproduce

See `docs/TERAMOVE_H_README.md`. In short:

* `pytest -q` (37 tests).
* `python -m experiments.run_experiments --exp all` (about 62 min on 22 cores).
* `python plots/make_paper_assets.py`.
* `tectonic paper/main.tex`.

## 12. Correction of the TeraMove paper

* **Simulator fixes (`chsr_sim/`).**
  * Compass azimuths (D1).
  * ITU-R absorption (D3).
  * Heights capped at 3.0 m. `CANDIDATE_Z` contained 3.2 m.
  * Positions bounded by the walls. Clipping to [0, 31] × [0, 19] had moved y = 19.5 m APs
    even in Tier 2.
  * The incumbent configuration is seeded into every swarm, so a tier never worsens its
    input.
  * Bounded cache (D9).
  * S = 50, T = 20, as the paper states.
  * **Content-keyed cache.** The cache was invalidated by `id(human_density)`. CPython
    reuses freed addresses, so a new crowd map could inherit stale path losses, which made
    results irreproducible. This bug affected the original runs too.
  * The old behaviour can be reproduced with `AZIMUTH_COMPASS = False` and `K_F_LEGACY`.
* **Real baselines.** Standard PSO and GA, with the same fitness and budget
  (`chsr_sim/baselines.py`).
* **Experiments** (`teramove_eval/run.py`, 30 seeds each, about 15 min on 22 cores):
  * commissioning;
  * forced tier analysis;
  * t0–t2 sequence;
  * crowd-density sweep;
  * convergence;
  * Table IV sensitivity.
  Stored runs reproduce bit-for-bit.
* **Paper source** (`teramove_paper/main.tex`):
  * Sections I–IV come from `main.tex`, which stopped there. Sections V–VII and the
    references were rebuilt from `THZ_Placement-2.pdf`.
  * All numbers come from `numbers.tex`.
  * Fixed: noise floor, crowd-model description, fitness weights, broken equation
    sentence, "Alameh" → Liu et al., garbled references [2]/[4], Fig. 1.
* **Main changes in the conclusions:**
  * The 16.6 % crowd collapse was largely an artefact of the azimuth bug.
  * HPSO does not converge faster than a standard PSO, and the PSO reaches higher coverage
    on single events.
  * HPSO's strength is far lower movement, and it meets the target most reliably over the
    sequence.
* **Not re-verified:** the MILP counts quoted in Sec. V-A (MILP not re-run).
* **TeraMove-H is unaffected.** It uses only the floor plan from `chsr_sim`. Its legacy
  experiment E1 was re-run after the fixes and is identical.
* **Tests.** 42 pass, including `tests/test_legacy_fixes.py`.
