# TeraMove-H — code guide

TeraMove-H extends TeraMove (movable THz APs, tiered swarm reconfiguration) to a hybrid
THz / Wi-Fi network with airtime-aware user association and minimum-power control.

## Layout

```
APSO_SIM_Thz/
  chsr_sim/                 legacy TeraMove simulator (unchanged; floor plan reused)
  teramove_h/               new package
    config.py               every parameter, with its source
    geometry.py             floor plan, rooms, MILP Fig. 1 layout, compass convention
    crowd.py                clustered hard-core crowd, drift, density map, sensing noise
    antenna.py              energy-conserving flat-top AP sector and UE pencil beam
    channel.py              numba ray/wall/body geometry, THz loss, self-blocking, Wi-Fi rates
    network.py              AP configuration, scenario views, SINR / capacity, grid coverage
    association.py          PACE (proposed), greedy GAP, exact GAP and LP bounds (HiGHS), max-SINR / offload rules
    power.py                SINR targets from airtime slack, Yates minimum-power iteration
    evaluator.py            inner problem: association + sleep + power control
    optimizer.py            hierarchical PSO tiers, GA (flat or tier-restricted), Hungarian per room
    cascade.py              TeraMove-H escalation and every baseline / ablation
  experiments/
    common.py               commissioning, seeding, parallel map, statistics
    run_experiments.py      E1 legacy check, E2 main, E3 regime, E4 temporal, E5 association, E6 sensing
  plots/make_paper_assets.py  figures, LaTeX tables and number macros from results/*.json
  tests/                    pytest suite (physics, algorithms, end-to-end methods)
  results/                  raw JSON results + commissioned layout
  paper/                    IEEE paper (main.tex, refs.bib, numbers.tex, figures/, tables/)
  docs/                     PLAN.md, REPORT.md, this file
```

## Reproduce

```bash
cd APSO_SIM_Thz
uv venv .venv --python 3.13
uv pip install --python .venv/bin/python numpy scipy numba matplotlib pytest pandas
.venv/bin/python -m pytest -q                                   # 53 tests
PYTHONPATH=. .venv/bin/python -m experiments.run_experiments --exp all   # ~1.4 h on 22 cores
PYTHONPATH=. .venv/bin/python plots/make_paper_assets.py
cd paper && tectonic main.tex                                   # or pdflatex + bibtex
```

Environment variables: `TMH_SEEDS` (default 30), `TMH_RESULTS` (default `results/`).

The placement MILP of the earlier work is **not** re-run; its Fig. 1 layout is hard-coded in
`geometry.MILP_LAYOUT`. The only integer program solved here is the small association ILP
used to measure the optimality gap of the greedy and PACE (milliseconds per instance).
`results_v1_greedy/` holds the earlier run, made with greedy association.

## Conventions
* Azimuths are compass bearings (0 = North = +y, clockwise), as in the MILP paper.
* Powers are in watts inside the code, dBm in `config.py`.
* All randomness flows from `experiments.common.rng_for(seed, tag)`; every method uses the
  same optimiser stream for a seed (common random numbers).
