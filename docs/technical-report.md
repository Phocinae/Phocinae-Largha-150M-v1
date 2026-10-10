# Technical Report (short) — Phocinae-Largha-150M-v1

> Short-form technical report. This is the canonical technical report for the release; the project does not submit it to arXiv (2026-10-08 decision). All numbers: [BENCHMARKS.md](../BENCHMARKS.md).

## Contents

- [1. Motivation](#1-motivation) · [2. Model](#2-model) · [3. Training data & procedure](#3-training-data--procedure) · [4. Calibration](#4-calibration) · [5. Evaluation & methodology](#5-evaluation--methodology) · [6. Known limitations](#6-known-limitations) · [7. Reproduction](#7-reproduction) · [8. References](#8-references)

## 1. Motivation

Agents make many small, structured decisions per session — command approvals, tool picks, escalations, triage. Sending each one to an LLM costs a 500–4,000-token API call and 1.5 s+ of round-trip. Largha's bet: most such decisions are learnable by a **144.3M** encoder with a small decision head — one local forward pass, **21.0 ms (RTX 5090)** on GPU fp16 (or ~1.64 s per case on a single CPU thread), calibrated confidence, deterministic and auditable, zero data leaving the machine. With the τ=0.6 escalate gate, only the uncertain **45.0%** of decisions go onward (**−55.0% LLM calls (79.6% at τ=0.5)**) while combined accuracy improves **0.906 → 0.9936 (kept subset)**.

## 2. Model

| item | value |
|---|---|
| parameters | **144.3M** (public: "150M-class"); fp16 safetensors 288.6 MB |
| encoder | mmBERT-small: hidden **384** × **22** layers × **6** heads, vocab **256k**, RoPE (θ 160000) + sliding-window (128) + full attention, max positions **8192** |
| decision head | 2-layer transformer (self-attn + FFN, `head_layers: 2`, head context 192) over mean-pooled encoder output |
| sequence budget | **512** tokens (state + questions + options); head attention window **192** tokens (`rl_agent_config.json`: max_len 512 / head_max_len 192) |
| outputs | per typed question: noul → bool (threshold, default 0.5) · choice → 0-based index · score → int 2–10, plus calibrated confidence |

Inference is a single non-autoregressive forward pass — deterministic for a fixed batch shape on the same device (fp16 vs fp32 may differ in the last digit). Protocol: [protocol.md](./protocol.md).

## 3. Training data & procedure

- Base: `jhu-clsp/mmBERT-small` (upstream pre-training unchanged).
- Fine-tune data: `LocalLLaMA/typed-decisions` train split (1,200 cases; community mirror `LocalLLaMA/typed-decisions`) + flip-augmented option reorderings.
- **Evaluation-overlap disclosure** *(corrected 2026-10-10)*: the fine-tune mix also includes an error-correction pair pool (500 items; original question order + gold soft targets) mined from model predictions on the typed-decisions test rows — 82 of the 100 typed-decisions cases in the S1MB benchmark (151 of 500 decisions) fall inside it — plus sampled rows from a Jev-8 training pool (18 of 4,055 cleaned banking77-test items; 13 of ~5,500 clinc_oos plus-test items). JevBench (public-231) was held out of training. No other S1MB benchmark sources were used in training.
- zh: machine-translated English test cases for evaluation; the training mix also includes machine-translated Chinese (≈2,400 rows) and native Chinese (≈1,400 rows).

| recipe item | value (`rl_agent_config.json`) |
|---|---|
| loss | ce + brier |
| optimizer | adafactor |
| lr encoder / head | 2e-5 / 1e-4 |
| micro batch / grad accum | 8 / 4 |
| updates | 300 |
| wall time | ~0.044 h single GPU (tag `n13_r4`) |
| checkpoint | epoch 1/1, avg_loss 1.3689859 (v1.1 weights) |

## 4. Calibration

The shipped column has ECE **0.2519** (en). Calibration temperatures **0.8660205 / 0.8081192 / 0.6624661** ship in the model repo config and are applied at inference by phocinae-server. An optional calibration column ([`calib/`](./calib/)) ships with the release; with it, ECE reaches **0.0168** (en) / **0.0152** (zh).

## 5. Evaluation & methodology

Protocol: each case = a `state` + typed questions; every question is judged as an independent decision. en test = 400 cases × 5 = 2,000 decisions; zh = the same cases machine-translated.

| metric | value |
|---|---|
| typed-decisions en / zh | **0.906 / 0.848** (Laya 0.766 (self-measured, native interface) · JEV 0.727 · meraGPT 0.768, same protocol) |
| flip (CPU fp32, lower better): rev150 / rev400 / random-mean / any | **0.0200/0.0217 / 0.0144 / 0.0283** |
| latency | GPU fp16 p50 **21.0 ms (RTX 5090)** · CPU 1-thread p50 **1.64 s per case** · CPU 8-thread batch **8–20 dec/s** |
| JevBench public-231 | **0.5455 (126/231)** — gate 58.4% not passed (tool_selection 12/12) |
| E1 escalate (τ=0.6) | 0.906 → **0.9936 kept-subset**, **−55.0% LLM calls** (79.6% at τ=0.5; independent repro 45.0% escalate) |
| calibration ECE (shipped column / with bundled `calib/`) | **0.2519 / 0.0168** |

Methodology notes:

- The main flip table is CPU fp32, idle machine, **double-reproduced** (2026-10-09); GPU fp16 0.0200/0.0217 and 1k-row 0.0181/0.0150/0.0331 are note-only (different protocols). GPU/CPU differences of ≤2 decisions are fp16↔fp32 noise.
- Competitor figures (Laya, JEV, meraGPT) come from public leaderboards/papers on the same typed protocol.
- Charts live in `figures/`; full tables, disclosures, and evidence pointers: [BENCHMARKS.md](../BENCHMARKS.md) and [reproduce.md](./reproduce.md).

## 6. Known limitations

- Not a chat/generator; no long-document reasoning; MMLU-style world-knowledge probes are below par.
- JevBench acceptance gate **not passed** (0.5455 vs 58.4%) — published as measured; JevBench (public-231) rows were held out of training (see the evaluation-overlap disclosure in §3).
- Option-order robustness is imperfect: 0.0217 flip ≈ one changed answer per ~46 reorders — 1.5 pp better than Laya in-domain (3.7%), far from perfect invariance (Jev ~9%, Laya out-of-domain 19.4%).
- zh evaluation is on machine-translated cases; the training mix includes machine-translated and native Chinese rows (see §3).
- Context: the encoder supports 8192 positions; the shipped config uses a 512-token sequence budget with a 192-token head attention window (`rl_agent_config.json`); 16k/32k probes degrade (0.453 / 0.387; v1.0-baseline measurements; re-probe pending for v1.1).
- No demographic/fairness evaluation; the training domain (English business operations) carries language and domain biases.
- Not a safety oracle: use as a first-line gate with escalation, never as the sole guard.

## 7. Reproduction

1. Integrity: `sha256sum model.safetensors` → `b6472511eea30729985374f43968cf7f4b16bbe0827de6c6ca07cf92afbb778a`.
2. Serve: phocinae-server with `PHOC_MODEL_DIR` pointing at this repo; smoke-test `noul`/`choice`/`score` ([deployment.md](./deployment.md)).
3. Determinism: repeat the same request → bit-identical answers.
4. Protocols, published values, and evidence paths: [reproduce.md](./reproduce.md). Row sets, seeds, and the environment file ship in this repository; the frozen eval-harness scripts and raw dumps are published at github.com/Phocinae in a follow-up release.

## 8. References

- [BENCHMARKS.md](../BENCHMARKS.md) — the source of truth for all published numbers
- [MODEL_CARD.md](../MODEL_CARD.md) — architecture, training, bias & limitations
- [reproduce.md](./reproduce.md) · [protocol.md](./protocol.md) · [deployment.md](./deployment.md) · [cost-savings.md](./cost-savings.md)
