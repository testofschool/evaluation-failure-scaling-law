# The Scaling Law of Evaluation Failure

**Why Simple Averaging Collapses Under Data Sparsity and Item Difficulty Gaps, and How Item Response Theory Recovers Ground Truth Across Domains**

Jung Min Kang · Independent Researcher · Seoul, South Korea

[![arXiv](https://img.shields.io/badge/arXiv-2605.11205-b31b1b.svg)](https://arxiv.org/abs/2605.11205)
[![Try Calculator](https://img.shields.io/badge/Try_Calculator-Online-059669.svg)](https://testofschool.github.io/evaluation-failure-scaling-law)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

> **Before you reproduce:** this repository releases the grid sweep only, two estimation
> details are described differently in the paper than they are implemented here, and the
> declared dependency list is incomplete. All four differences are documented in
> **[KNOWN_DISCREPANCIES.md](KNOWN_DISCREPANCIES.md)**.

---

## What This Paper Does

We show that **simple averaging** — the default method for ranking systems on benchmarks — **fails predictably** when two conditions co-occur:

1. The evaluation matrix is **sparse** (not every system is tested on every item)
2. Items vary substantially in **difficulty**

Through controlled simulations across four domains (NLP, clinical trials, autonomous vehicle safety, cybersecurity) and a **150-condition grid sweep**, we map the **Evaluation Failure Surface**: ranking error increases as a function of Sparsity × Difficulty Gap, while **IRT-based estimation remains robust** (ρ ≥ 0.993 across all conditions).

<p align="center">
  <img src="figures/figure2_composite.png" width="800" alt="Evaluation Failure Surface"/>
</p>

## What This Paper Does NOT Claim

- ❌ We do not claim IRT is new to AI evaluation — [Rodriguez et al. (2021)](https://aclanthology.org/2021.acl-long.346/) and [py-irt](https://github.com/nd-ball/py-irt) preceded this work.
- ❌ We do not claim real-world Physical AI data obeys 2PL IRT assumptions.
- ❌ We do not claim a precisely fitted closed-form scaling law — the power-law approximation explains only part of the variance (R² = 0.587). We describe an empirical failure surface.
- ❌ We do not provide a completed Physical AI benchmark.

## Key Results

| Metric | Value |
|--------|-------|
| Worst ρ (simple avg, biased missingness) | 0.242 |
| Worst ρ (simple avg, MCAR) | 0.770 |
| Min ρ (IRT, all conditions) | **0.993** |
| S×D interaction coefficient | γ₃ = +0.199, t = 13.05 |
| Interaction model R² | 0.777 |
| Grid conditions tested | 150 (15 S × 10 D) |

## Reproduction

This repository reproduces the **150-condition grid sweep** (§5.3 and Figure 1). The
four-domain experiments in §5.1–5.2 are not included here — see
[KNOWN_DISCREPANCIES.md](KNOWN_DISCREPANCIES.md), D-3.

### Requirements

`requirements.txt` is the canonical dependency list — install from it rather than naming
packages by hand:

```bash
pip install -r requirements.txt
```

### Run the Grid Sweep

```bash
python src/grid_sweep_final.py
```

**Measured runtime: 78.5 s end-to-end** (median of 3 consecutive runs; 78.0 s / 78.5 s /
78.6 s), of which 75.7 s is the 150-cell × 15-seed sweep and the remainder is figure
rendering and the regression report. Measurement environment: high-end laptop CPU
(Apple M1 Max), macOS 26.5.2, Python 3.10.11, NumPy 2.2.6, SciPy 1.15.3, matplotlib 3.10.8.
The paper quotes ≈3 minutes for this sweep on a standard laptop CPU; the machine above is the
same class of hardware at a higher specification, so the two figures are consistent.

All six generated files are written to `outputs/`:

| File | Contents |
|------|----------|
| `outputs/grid_summary.csv` | Per-cell mean / std / MCSE over seeds (150 rows) |
| `outputs/grid_raw_runs.csv` | Per-seed raw ρ and top-1 misrank flags |
| `outputs/regression_report.txt` | Interaction regression + power-law fit |
| `outputs/figure2_composite.png` | **paper Figure 1** — clean 4-panel composite |
| `outputs/figure2_composite_annotated.png` | Same four panels with per-cell values printed |
| `outputs/scaling_fit.png` | S×D vs. ranking error scatter with power-law fit |

The filename `figure2_composite.png` is historical: it is the file `paper/main.tex` includes,
so it is **not** renamed even though the figure is numbered 1 in the paper. The committed
copies live at `figures/figure2_composite.png` and `paper/figures/figure2_composite.png`.

### Seed Count

`N_SEEDS = 15` in `src/grid_sweep_final.py` is the exact setting used in the paper —
150 cells × 15 seeds = 2,250 replications per missingness condition. Leave it unchanged to
reproduce the published numbers: with it, `grid_summary.csv`, `grid_raw_runs.csv` and
`regression_report.txt` regenerate byte-identically to the committed copies (verified
2026-08-05 on the environment above). Changing `N_SEEDS` changes the Monte-Carlo standard
errors and will not reproduce the reported values.

## Repository Structure

```
evaluation-failure-scaling-law/
├── README.md
├── KNOWN_DISCREPANCIES.md      # arXiv v1 ↔ this repository
├── LICENSE
├── CITATION.cff
├── requirements.txt
├── paper/
│   ├── Kang_2026_EFSL_FINAL.pdf
│   ├── main.tex
│   └── figures/
│       └── figure2_composite.png
├── src/
│   ├── grid_sweep_final.py     # 150-condition grid sweep (§5.3, Figure 1)
│   └── EvalFailureLab.jsx      # interactive calculator component
├── docs/
│   └── index.html              # GitHub Pages calculator
├── figures/
│   └── figure2_composite.png   # committed copy of paper Figure 1
└── outputs/
    ├── grid_summary.csv
    ├── grid_raw_runs.csv
    └── regression_report.txt
```

Running the sweep additionally writes `figure2_composite.png`,
`figure2_composite_annotated.png` and `scaling_fit.png` into `outputs/`; those three are
regenerated artifacts and are not committed.

## Citation

```bibtex
@article{kang2026evaluation,
  title={The Scaling Law of Evaluation Failure: Why Simple Averaging Collapses Under Data Sparsity and Item Difficulty Gaps, and How Item Response Theory Recovers Ground Truth Across Domains},
  author={Kang, Jung Min},
  journal={arXiv preprint arXiv:2605.11205},
  year={2026},
  url={https://arxiv.org/abs/2605.11205}
}
```

## Related Work

- [py-irt](https://github.com/nd-ball/py-irt) — Bayesian IRT library for Python
- [Rodriguez et al. (2021)](https://aclanthology.org/2021.acl-long.346/) — IRT-based NLP leaderboards
- [Zhou et al. (2026)](https://arxiv.org/abs/2505.15055) — PSN-IRT for LLM benchmarks
- [Ndzomga (2026)](https://arxiv.org/abs/2603.23749) — Efficient agent benchmarking via IRT-motivated task selection

## Interactive Calculator

Try the Evaluation Failure Calculator in your browser — no installation required:

**[→ Launch Calculator](https://testofschool.github.io/evaluation-failure-scaling-law)**

Paste your own benchmark matrix to compare simple-average vs IRT rankings.
All computation runs locally in your browser. No data is collected.

## License

This work is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
