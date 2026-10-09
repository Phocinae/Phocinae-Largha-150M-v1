# Bundled calibration column (Phocinae-Largha-150M-v1)

Optional post-hoc calibration for the probabilities exported by `phocinae-server`
(`probabilities` / `answer_confidence` fields). No retraining, no weight changes — a
per-decision power transform, applied AFTER inference, monotone (argmax and the
noul 0.5-threshold are unchanged, so **all accuracies stay identical**).

## Mechanism

For every decision, transform all option probabilities element-wise:

    q ∝ p ** gamma        (normalize after the power; apply per decision)

- `gamma = 1` → raw probabilities (as shipped).
- `gamma > 1` → sharpened; `gamma < 1` → softened.

## Recommended columns (fitted 2026-10-08; re-measured on the v1.1 weights)

| face | raw ECE (shipped column) | recommended γ | calibrated ECE | Brier (raw → calibrated) |
|---|---|---|---|---|
| en   | 0.2519 | **4.33** | **0.0168** | 0.0207 → 0.1218 |
| zh   | 0.1941 | **2.51** | **0.0152** | 0.0333 → 0.0961 |

- Fitting: 25% held-out cases (seed 20261008) with a shrinkage rule toward the
  full-grid ECE argmin; NLL guardrail (calibrated NLL ≤ raw + 0.01) satisfied.
- Cost: Brier rises (sharpened columns are more confident) — ECE vs Brier is an
  explicit trade-off. Accuracy is invariant (see above).
- The shipped inference temperature column (`rl_agent_config.json`) is what the
  `*.json` metrics in BENCHMARKS.md use ("shipped column"). This folder is an
  OPTIONAL extra layer; it is not applied by default.

## Usage

```python
from calibrate import apply_gamma
q_cal = apply_gamma({"a": 0.61, "b": 0.39}, gamma=4.33)
```

## Provenance

`exp/calib_n13_20261008/` (fit scripts + full tables, reproducible) in the release
workspace; this folder is the user-facing extract.
