# Reproducing the reported numbers

All published numbers were measured on the shipped weights (`model.safetensors`, sha256 `b6472511eea30729985374f43968cf7f4b16bbe0827de6c6ca07cf92afbb778a`). The eval harness (scripts + configs) is published at [github.com/Phocinae](https://github.com/Phocinae) — this document states the protocols and published values so any third party can verify independently.

## Contents

- [Data sources](#data-sources) · [Protocols & published values](#protocols--published-values) · [Quick verification steps](#quick-verification-steps) · [Status / known gaps](#status--known-gaps)

## Data sources

| source | use |
|---|---|
| [LocalLLaMA/typed-decisions](https://huggingface.co/datasets/LocalLLaMA/typed-decisions) (Apache-2.0, HF revision f7a2487e) | main benchmark; train split (with flip-augmented reorderings) for training, test split for eval |
| [JevBench](https://github.com/fstandhartinger/JevBench) | held-out public protocol (public-231); **never used in training** |
\| zh cases \| English test cases machine-translated to Chinese, for evaluation; the training mix includes machine-translated + native Chinese rows (see [BENCHMARKS §7](../BENCHMARKS.md#7-chinese-translated-protocol)) \|

## Protocols & published values

### typed-decisions
- en: 400 cases × 5 questions = 2000 decisions; each judged independently (state + typed question).
- Frozen: en accuracy **0.906**, zh (translated) **0.848**.

### Option-order flip
- Reorder the options of a decision; a flip = the answer changed.
- flip150: 150 rows × 2 orders = 300 items → **0.0200** (6 flips); flip400: 400 rows → 600 items → **0.0217** (13 flips). CPU fp32, idle machine, double-reproduced (2026-10-09).
- random-mean: mean over 3 random reorder seeds → **0.0144**; any-of-3: any of 3 reorders flips → **0.0283**.
- Reference-only (different protocols): GPU fp16 idle 0.0200/0.0217; 1k-row 4-perm (train-first-1000 rows) 0.0181/0.0150/0.0331.

### Latency
- GPU fp16 single-decision p50 **21.0 ms (RTX 5090)** (release value).
- CPU single-thread p50 **1.64 s per case** (n=40, idle machine; 1 case = 1 state + 5 decisions, end-to-end incl. tokenize + forward + answer assembly).
- CPU 8-thread batch **8–20 decisions/s** (b=1 → 21.0, b=32 → 8.7); 2000-row mega-batch 7–9 decisions/s.

### JevBench public-231
- micro **0.5455 = 126/231**; acceptance gate 58.4% (not passed, disclosed); tiers easy 0.9167 (44/48) / original 0.5000 (36/72) / hard 0.4144 (46/111); family-macro 0.5226; tool_selection k≤10 **12/12**.

### Escalate routing (E1, τ=0.6)
- Local acc **0.906** → kept-subset **0.9936** (+0.0876) with 45.0% of decisions escalated to an external LLM (**−55.0% LLM calls; 79.6% at τ=0.5**). Independent reproductions: local **0.9055** (en) / **0.848** (zh) — CPU fp32 re-runs — vs official 0.906 / 0.848; shown side by side, disagreements stated.

### Calibration
- Shipped column ECE **0.2519** (en) / **0.1941** (zh). Calibration temperatures in the model repo config: **0.8660 / 0.8081 / 0.6625** (choice/score/noul).
- A bundled recalibration column (`calib/`, recommended γ 4.33 en / 2.51 zh) reaches **0.0168** (en) / **0.0152** (zh); apply it as a post-hoc transform on the reported probabilities.

## Environment

- Python 3.10+; the row-level scripts in `datasets/` use only the standard library.
- Inference engine: `pip install phocinae-server` (serves the shipped `model.safetensors`).
- Optional (token-level rebuilds of the flipaug training mix): `pip install torch transformers`.

## Quick verification steps

1. Integrity: `sha256sum model.safetensors` → `b6472511eea30729985374f43968cf7f4b16bbe0827de6c6ca07cf92afbb778a`.
2. Load smoke: run phocinae-server with `PHOC_MODEL_DIR` pointed here and post a `noul`/`choice`/`score` request (see [protocol.md](./protocol.md)) — answers must be bool/index/2–10 respectively.
3. Determinism: repeat the same request twice → bit-identical answers.

## Status / known gaps

- The eval four-piece (row sets, seeds, scripts, environment) ships with the repository (`datasets/` + this document); raw training evidence dumps (per-decision prediction JSONs, exact commit hashes) follow in a second release.
- GPU numbers are fp16; local CPU re-runs may differ by a flip or two (fp16↔fp32 noise) — the published main table is the CPU fp32 double-reproduced set.
- zh is a translated protocol; treat zh numbers as cross-lingual transfer evidence, not native-language eval.
