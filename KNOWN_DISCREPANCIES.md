# Known Discrepancies (arXiv v1 ↔ this repository)

This file records places where the text of **arXiv:2605.11205 v1** describes something that
this repository does differently, or does not contain at all.

It is a record, not a correction. The paper is frozen as submitted and no `.tex` or `.pdf`
file in `paper/` has been edited to accommodate these entries. Each item cites the paper
section and the exact code lines so a reader can check both sides directly.

Verified against commit `1e3091e` on 2026-08-05.

| ID | Paper | Repository | Nature |
|----|-------|------------|--------|
| [D-1](#d-1--estimation-objective) | §3.3, Eq. (5) | `src/grid_sweep_final.py:102-118` | Described estimator ≠ implemented estimator |
| [D-2](#d-2--standard-errors) | §3.3, "Standard errors" | `src/grid_sweep_final.py:118` | Described procedure absent from code |
| [D-3](#d-3--scope-of-the-released-code) | Reproducibility Statement | `src/` | Released code narrower than stated |
| [D-4](#d-4--declared-dependencies-low) | Reproducibility Statement | `requirements.txt` | Dependency list understated (LOW) |
| [D-5](#d-5--scope-of-the-irt-robustness-figure) | Abstract, §1, §5.3, Fig. 1 caption, §7, Reproducibility | `outputs/grid_summary.csv`, `outputs/grid_raw_runs.csv`, `src/grid_sweep_final.py:157-161` | IRT robustness figure stated without scope; runtime wording |

---

## D-1 — Estimation objective

**Paper.** §3.3 (2PL Item Response Theory), "Estimation" paragraph — `paper/main.tex:112-116`:

> Parameters are estimated by maximizing the marginal log-likelihood

followed by Eq. (5), a sum over systems, observed items, and trials, and by the sentence
"We optimize using L-BFGS-B with regularization priors θ_j ~ N(0,1), b_i ~ N(0,2),
log a_i ~ N(0,0.5)."

**Repository.** `fit_irt()` in `src/grid_sweep_final.py:102-118` maximizes a **penalized joint
likelihood**, not a marginal one:

- θ (J parameters), b (I parameters) and log a (I parameters) are optimized *simultaneously*
  in one L-BFGS-B call over the concatenated vector — `src/grid_sweep_final.py:114-117`.
  Nothing is integrated out, so no marginalization takes place.
- The Gaussian priors enter as an additive quadratic penalty on the objective —
  `src/grid_sweep_final.py:107` — which makes the result a penalized-ML (MAP) estimate rather
  than a maximizer of a marginal likelihood.

**Nature of the discrepancy.** Naming, not arithmetic. The reported numbers were produced by
the code as written, and Eq. (5) plus the prior sentence in fact describe the implemented
penalized joint objective. The specific phrase "marginal log-likelihood" is what does not
match: marginal ML would integrate θ out against a population distribution and would in
general yield different estimates. Joint estimation of θ with a fixed number of items is also
known to be inconsistent as J grows with I fixed, which marginal ML is designed to avoid — so
the two are not interchangeable labels for one procedure.

---

## D-2 — Standard errors

**Paper.** §3.3, "Standard errors" paragraph — `paper/main.tex:120`:

> We compute standard errors from the diagonal of the inverse observed Fisher information
> matrix, approximated via finite-difference Hessian evaluation at the MLE.

**Repository.** No such computation exists. `fit_irt()` returns point estimates only
(`src/grid_sweep_final.py:118`), and there is no Hessian, Fisher-information, or
standard-error code anywhere under `src/`.

The dispersion actually reported in `outputs/grid_summary.csv` comes from a different source:
across-seed standard deviations and Monte-Carlo standard errors over `N_SEEDS = 15`, computed
at `src/grid_sweep_final.py:186-194`. Those are sampling-variability statistics over
replications, not asymptotic standard errors of the IRT parameters.

**Nature of the discrepancy.** A described procedure that the released code does not perform.
No number in the paper or in `outputs/` depends on IRT parameter standard errors, so nothing
downstream changes — but a reader looking for the Fisher-information code will not find it.

---

## D-3 — Scope of the released code

**Paper.** Reproducibility Statement — `paper/main.tex:354`:

> The complete Python implementation---including data generation, IRT estimation, grid sweep,
> and evaluation---is available at [...]

and

> complete subject ability parameters are included in the code repository.

**Repository.** Only the grid sweep is released.

- `src/grid_sweep_final.py` implements data generation, IRT estimation, evaluation and
  regression **for the 150-condition grid sweep only** (§5.3 and Figure 1).
- The four-domain experiments — §4.1–4.4, and the results in §5.1–5.2 — have **no code in this
  repository**.
- Ground-truth *item* parameters (b*, a*) for all four domains are given in the paper's
  Appendix A (`paper/main.tex:426-511`). Ground-truth *subject/system ability* parameters (θ*)
  for the four domains appear neither in the paper nor here. The only θ* present is the grid
  sweep's own `THETA_TRUE = np.linspace(-2.0, 2.0, J)` (J = 10) at
  `src/grid_sweep_final.py:21`.

**Nature of the discrepancy.** Coverage. What is reproducible from this repository today:
Figure 1, `outputs/grid_summary.csv`, `outputs/grid_raw_runs.csv`, and
`outputs/regression_report.txt` — the numeric artifacts regenerate byte-identically from
`python src/grid_sweep_final.py`. What is not reproducible from this repository: the
four-domain tables in §5.1–5.2.

---

## D-4 — Declared dependencies (LOW)

**Severity: LOW.** This is an imprecision, not a factual error.

**Paper.** Reproducibility Statement — `paper/main.tex:354`:

> The codebase requires only NumPy and SciPy (no deep learning frameworks).

**Repository.** `requirements.txt` lists three packages: `numpy`, `scipy`, **and
`matplotlib`**.

The claim is accurate about the *computation*: every numeric path — mask generation, response
simulation, IRT fitting, Spearman correlation, the interaction regression and the power-law
fit — uses NumPy and SciPy only, and all three numeric artifacts are written to `outputs/`
before matplotlib is touched. matplotlib is imported late, inside `run()`, at
`src/grid_sweep_final.py:216` — after the CSV writes at `src/grid_sweep_final.py:209-213` —
and is used solely to render the three PNGs.

**Where a reader actually hits this.** Someone who reads only the paper and installs
`numpy scipy` will see the sweep run to completion and the CSVs land correctly, then hit
`ModuleNotFoundError: No module named 'matplotlib'` at the figure stage. Installing from
`requirements.txt` avoids this.

---

## D-5 — Scope of the IRT robustness figure

Added 2026-09-29. Numbers below were recomputed from the committed CSVs at commit `4724bd0`
(pandas over `outputs/grid_summary.csv` and `outputs/grid_raw_runs.csv`).

**Paper.** "IRT maintains $\rho \geq 0.993$ across all conditions" or equivalent appears at
`paper/main.tex:28` (abstract), `:55`, `:225`, `:234`, `:239` (Figure 1 caption) and `:343`.
`outputs/regression_report.txt:29-30` prints the same line, generated by
`src/grid_sweep_final.py:362-363`.

**Repository.** What the committed data actually support:

- The 0.993 is the **minimum cell mean** of `rho_irt_biased_mean` over the 150 cells, and it is
  a **rounded** value: the minimum is 0.9927, reached at two cells (S = 0.70, D = 2.5 and
  S = 0.70, D = 4.0). Read literally, "ρ ≥ 0.993" is false for those two cells.
- Per seed, the minimum IRT ρ is **0.9515** (S = 0.70, D = 2.0, seed 7), and **73 of 2,250** IRT
  runs fall below 0.993.
- IRT is fitted **only under difficulty-biased missingness**. The MCAR arm runs simple
  averaging only, so "all conditions" does not include any MCAR IRT fit.
- The 10 cells with S = 0 do not fit IRT: ρ = 1.0 is assigned directly
  (`src/grid_sweep_final.py:157-161`). IRT is actually fitted in 140 cells (2,100 runs).
- All of this is one synthetic 2PL setting (J = 10, I = 10, K = 100).

The four-domain figure "$\rho \geq 0.996$ across all conditions" (`paper/main.tex:28`) cannot be
checked here because the four-domain code is not released (D-3).

**Scoped reading.** On the synthetic 2PL grid under difficulty-biased missingness, the
minimum cell-mean IRT ρ is 0.993 (rounded from 0.9927); individual seeds go as low as 0.9515.

**Runtime wording.** `paper/main.tex:354` says each experiment runs "in under 60 seconds" and
the grid sweep "in approximately 3 minutes". The measured grid-sweep runtime in the README is
78.5 s end-to-end on an Apple M1 Max. The "under 60 seconds" clause refers to the four-domain
experiments, which are not in this repository (D-3), so it cannot be checked here; it is not a
runtime figure for the grid sweep.

**Nature of the discrepancy.** Scope and rounding, not a changed result. The paper text is left
as submitted; the README states the scoped form.
