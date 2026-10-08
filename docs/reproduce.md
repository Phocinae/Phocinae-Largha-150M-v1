# Reproducing the reported numbers

All published numbers were measured on the shipped weights (`model.safetensors`, sha256 `db79d5ee2f16597f34e564f5a4363bddb5b5bbd9827c01819725dabcc7802697`). The eval harness (scripts + configs) is published at [github.com/Phocinae](https://github.com/Phocinae) — this document states the protocols and published values so any third party can verify independently.

## Contents

- [Data sources](#data-sources) · [Protocols & published values](#protocols--published-values) · [Quick verification steps](#quick-verification-steps) · [Status / known gaps](#status--known-gaps)

## Data sources

| source | use |
|---|---|
| [LocalLLaMA/typed-decisions](https://huggingface.co/datasets/LocalLLaMA/typed-decisions) (Apache-2.0, HF revision f7a2487e) | main benchmark; train split (with flip-augmented reorderings) for training, test split for eval |
| [JevBench](https://github.com/fstandhartinger/JevBench) | held-out public protocol (public-231); **never used in training** |
| zh cases | English test cases machine-translated to Chinese; **no native zh training rows** |

## Protocols & published values

### typed-decisions
- en: 400 cases × 5 questions = 2000 decisions; each judged independently (state + typed question).
- Frozen: en accuracy **0.797**, zh (translated) **0.789**.

### Option-order flip
- Reorder the options of a decision; a flip = the answer changed.
- flip150: 150 rows × 2 orders = 300 items → **0.0300** (9 flips); flip400: 400 rows → 600 items → **0.0300** (18 flips). CPU fp32, idle machine, double-reproduced (2026-10-07).
- random-mean: mean over 3 random reorder seeds → **0.0233**; any-of-3: any of 3 reorders flips → **0.0433**.
- Reference-only (different protocols): GPU fp16 idle 0.027/0.028; 1k-row 4-perm (train-first-1000 rows) 0.0187/0.0205/0.0431.

### Latency
- GPU fp16 single-decision p50 **18.6 ms** (release value).
- CPU single-thread p50 **1.51 s per case** (n=40, idle machine; 1 case = 1 state + 5 decisions, end-to-end incl. tokenize + forward + answer assembly; ≈0.28 s per decision).
- CPU 8-thread batch **8–21 decisions/s** (b=1 → 21.0, b=32 → 8.7); 2000-row mega-batch 7–9 decisions/s.

### JevBench public-231
- micro **0.5108 = 118/231**; acceptance gate 58.4% (not passed, disclosed); tiers easy 0.8958 (43) / original 0.4167 (30) / hard 0.4054 (45); family-macro 0.4829; tool_selection k≤10 **12/12**.

### Escalate routing (E1, τ=0.6)
- Local acc **0.797** → kept-subset **0.886** (+0.089) with 45.7% of decisions escalated to an external LLM (**−54.4% LLM calls; 82.8% at τ=0.5**). Independent reproductions: local 0.7825 (en) / 0.7820 (zh) vs official 0.797 / 0.789 — shown side by side, disagreements stated.

### Calibration
- Shipped column ECE **0.1313** (en). Calibration temperatures in the model repo config: **0.7698 / 0.7879 / 0.7560**.
- A recommended recalibration column (A1) reached 0.0106 during development — **not shipped**; any published ECE below 0.1313 for these weights refers to a non-shipped recalibration.

## Quick verification steps

1. Integrity: `sha256sum model.safetensors` → `db79d5ee2f16597f34e564f5a4363bddb5b5bbd9827c01819725dabcc7802697`.
2. Load smoke: run phocinae-server with `PHOC_MODEL_DIR` pointed here and post a `noul`/`choice`/`score` request (see [protocol.md](./protocol.md)) — answers must be bool/index/2–10 respectively.
3. Determinism: repeat the same request twice → bit-identical answers.

## Status / known gaps

- The eval harness (scripts, raw evidence JSON dumps, exact commit hashes) is published at github.com/Phocinae.
- GPU numbers are fp16; local CPU re-runs may differ by a flip or two (fp16↔fp32 noise) — the published main table is the CPU fp32 double-reproduced set.
- zh is a translated protocol; treat zh numbers as cross-lingual transfer evidence, not native-language eval.
