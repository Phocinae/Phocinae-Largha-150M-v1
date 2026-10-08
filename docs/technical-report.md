# Technical Report (short) — Phocinae-Largha-150M-v1

> Short-form technical report. The formal arXiv version is in preparation; once it lands, this file becomes a link page. All numbers: [BENCHMARKS.md](../BENCHMARKS.md).

## 1. Motivation

Agents make many small, structured decisions per session — command approvals, tool picks, escalations, triage. Sending each one to an LLM costs a 500–4,000-token API call and 1.5 s+ of round-trip. Largha's bet: most such decisions are learnable by a **144.3M** encoder with a small decision head — one local forward pass, **18.6 ms** on GPU fp16 (or ~1.51 s per case on a single CPU thread, ≈0.28 s per decision), calibrated confidence, deterministic and auditable, zero data leaving the machine. With the τ=0.6 escalate gate, only the uncertain **45.7%** of decisions go onward (**−54.4% LLM calls (82.8% at τ=0.5)**) while combined accuracy improves **0.797 → 0.886 (kept subset)**.

## 2. Model

| item | value |
|---|---|
| parameters | **144.3M** (public: "150M-class"); fp16 safetensors 288.6 MB |
| encoder | mmBERT-small: hidden **384** × **22** layers × **6** heads, vocab **256k**, RoPE (θ 160000) + sliding-window (128) + full attention, max positions **8192** |
| decision head | 2-layer transformer (self-attn + FFN, `head_layers: 2`, head context 192) over mean-pooled encoder output |
| head length | **512** tokens default (self-imposed training/inference default) |
| outputs | per typed question: noul → bool (threshold, default 0.5) · choice → 0-based index · score → int 2–10, plus calibrated confidence |

Inference is a single non-autoregressive forward pass — deterministic for a fixed batch shape on the same device (fp16 vs fp32 may differ in the last digit). Protocol: [protocol.md](./protocol.md).

## 3. Training data & procedure

- Base: `jhu-clsp/mmBERT-small` (upstream pre-training unchanged).
- Fine-tune data: `LocalLLaMA/typed-decisions` train split (1,200 cases; community mirror `LocalLLaMA/typed-decisions`) + flip-augmented option reorderings. **No eval rows were used**: typed-decisions test (400 cases / 2,000 decisions) and JevBench stayed out of training.
- zh: translated English test cases were used for evaluation only — **no native Chinese training rows**.

| recipe item | value (`rl_agent_config.json`) |
|---|---|
| loss | ce + brier |
| optimizer | adafactor |
| lr encoder / head | 2e-5 / 1e-4 |
| micro batch / grad accum | 8 / 4 |
| updates | 9228 |
| wall time | ~1.36 h single GPU (tag `cf4`) |
| checkpoint | epoch 1/1, avg_loss 0.9565 |

## 4. Calibration

The shipped column has ECE **0.1313** (en). Calibration temperatures **0.7698 / 0.7879 / 0.7560** ship in the model repo config and are applied at inference by phocinae-server. A development recalibration column reaching 0.0106 is **not shipped**.

## 5. Evaluation & methodology

Protocol: each case = a `state` + typed questions; every question is judged as an independent decision. en test = 400 cases × 5 = 2,000 decisions; zh = the same cases machine-translated.

| metric | value |
|---|---|
| typed-decisions en / zh | **0.797 / 0.789** (Laya 0.766 · JEV 0.727 · meraGPT 0.768, same protocol) |
| flip (CPU fp32, lower better): rev150 / rev400 / random-mean / any | **0.0300 / 0.0300 / 0.0233 / 0.0433** |
| latency | GPU fp16 p50 **18.6 ms** · CPU 1-thread p50 **1.51 s per case** (≈0.28 s per decision) · CPU 8-thread batch **8–21 dec/s** |
| JevBench public-231 | **0.5108 (118/231)** — gate 58.4% not passed (tool_selection 12/12) |
| E1 escalate (τ=0.6) | 0.797 → **0.886 kept-subset**, **−54.4% LLM calls** (82.8% at τ=0.5; independent repro 45.7% escalate) |
| calibration ECE (shipped) | **0.1313** (development recalibration 0.0106 not shipped) |

Methodology notes:

- The main flip table is CPU fp32, idle machine, **double-reproduced** (2026-10-07); GPU fp16 0.027/0.028 and 1k-row 0.0187/0.0205/0.0431 are note-only (different protocols). GPU/CPU differences of ≤2 decisions are fp16↔fp32 noise.
- Competitor figures (Laya, JEV, meraGPT) come from public leaderboards/papers on the same typed protocol.
- Charts live in `figures/`; full tables, disclosures, and evidence pointers: [BENCHMARKS.md](../BENCHMARKS.md) and [reproduce.md](./reproduce.md).

## 6. Known limitations

- Not a chat/generator; no long-document reasoning; MMLU-style world-knowledge probes are below par.
- JevBench acceptance gate **not passed** (0.5108 vs 58.4%) — disclosed honestly; never trained on eval rows.
- Option-order robustness is imperfect: 0.0300 flip ≈ one changed answer per ~33 reorders — 0.7 pp better than Laya in-domain (3.7%), far from perfect invariance (Jev ~9%, Laya out-of-domain 19.4%).
- zh is translated-only eval; no native zh training rows.
- Context: the encoder supports 8192 positions, but the head was trained at 512; 16k/32k probes degrade (0.453 / 0.387).
- No demographic/fairness evaluation; the training domain (English business operations) carries language and domain biases.
- Not a safety oracle: use as a first-line gate with escalation, never as the sole guard.

## 7. Reproduction

1. Integrity: `sha256sum model.safetensors` → `db79d5ee2f16597f34e564f5a4363bddb5b5bbd9827c01819725dabcc7802697`.
2. Serve: phocinae-server with `PHOC_MODEL_DIR` pointing at this repo; smoke-test `noul`/`choice`/`score` ([deployment.md](./deployment.md)).
3. Determinism: repeat the same request → bit-identical answers.
4. Protocols, published values, and evidence paths: [reproduce.md](./reproduce.md). The eval harness (scripts, configs, raw dumps) is published at github.com/Phocinae.

## 8. References

- [BENCHMARKS.md](../BENCHMARKS.md) — the source of truth for all published numbers
- [MODEL_CARD.md](../MODEL_CARD.md) — architecture, training, bias & limitations
- [reproduce.md](./reproduce.md) · [protocol.md](./protocol.md) · [deployment.md](./deployment.md) · [cost-savings.md](./cost-savings.md)
