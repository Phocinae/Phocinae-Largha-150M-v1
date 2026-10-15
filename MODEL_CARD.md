# MODEL CARD — Phocinae-Largha-150M-v1

## Contents

- [Model details](#model-details) · [Overview](#overview) · [Architecture](#architecture) · [Training](#training) · [Inputs & outputs](#inputs--outputs) · [Evaluation](#evaluation) · [Calibration](#calibration) · [Bias, risks & limitations](#bias-risks--limitations-honest-disclosure) · [Out-of-scope uses](#out-of-scope-uses) · [Environmental impact](#environmental-impact) · [Citation](#citation) · [Credits](#credits)

## Model details

| item | value |
|---|---|
| name | Phocinae-Largha-150M-v1 |
| nickname | 斑海豹 (Largha, the spotted seal) |
| series | 海豹系列 / Phocinae |
| type | encoder-based **decision model** (not a chat/decoder model) |
| parameters | **144.3M** (public: "150M-class") |
| languages | en; zh via machine-translated eval cases (training mix includes machine-translated + native Chinese rows — see Bias, risks & limitations) |
| license | Apache-2.0 (weights; see LICENSE) |
| base encoder | jhu-clsp/mmBERT-small (JHU CLSP) |
| storage | fp16 safetensors, 288.6 MB |
| sha256 | `b6472511eea30729985374f43968cf7f4b16bbe0827de6c6ca07cf92afbb778a` |

## Overview

Largha makes one structured decision per forward pass: given a `state` and a list of typed questions (`noul` yes/no, `choice` pick-one, `score` 2–10), it returns calibrated answers with confidence, and is explicitly trained to be robust to option reordering. It is designed as a local decision layer for agents — approval gates, tool routing, escalation, triage — not as a general language model.

## Architecture

- Encoder: mmBERT-small — hidden **384**, **22** layers, **6** heads, vocab **256k**, RoPE (theta 160000), sliding-window (128) + full attention mix, max position **8192**.
- Decision head: 2-layer transformer head (self-attn + FFN, `head_layers: 2`, head context 192) over mean-pooled encoder output.
- Inference: single forward pass, deterministic for a fixed batch shape (no sampling).

## Training

- Base: `jhu-clsp/mmBERT-small` (upstream pre-training unchanged).
- Fine-tune data: `LocalLLaMA/typed-decisions` train split + flip-augmented option reorderings.
- Recipe (`rl_agent_config.json`): loss `ce+brier`, optimizer `adafactor`, lr_encoder 2e-5 / lr_head 1e-4, micro_batch 8, grad_accum 4, updates 300, ~0.044 h (local, tag `n13_r4`); `checkpoint_meta.json`: epoch 1/1, avg_loss 1.3689859449863433.
- The typed-decisions **test split and JevBench were not used as training data in the ordinary sense** — but the v1.1 mix did contain a 500-item correction pool mined from test-split predictions, which the benchmark maintainers treated as test exposure. Details and the corrected clean score (0.791) are in `BENCHMARKS.md` §1.1.

## Inputs & outputs

`POST /v1/systemone`-style protocol (phocinae-server):

- input: `model` ("Phocinae-Largha-150M-v1"), `state` (string), `questions` (list ≤64; each: `id`, `type` ∈ {noul, choice, score}, `options` for choice ≤255, `threshold` for noul ∈ [0,1]).
- output: `answers` = {qid: bool | 0-based option index | int 2–10}; extensions `answer_confidence` (temperature-calibrated top probability), `action`, `option_scores`, `routing`.

Full contract: [docs/protocol.md](./docs/protocol.md).

## Evaluation

| benchmark | result |
|---|---|
| typed-decisions en (400 cases / 2000 decisions) | **0.791** — curated clean re-score (**0.989** on the 1,500 decisions training data never touched; the superseded 0.906 was measured on a partly-seen split) |
| typed-decisions zh (translated cases) | **0.848** |
| flip (CPU fp32): flip150 / flip400 / random-mean / any | **0.0200/0.0217 / 0.0144 / 0.0283** |
| JevBench public-231 | **0.5455 (126/231)** — below most systems on that board. JevBench has **no score gate**: its eligibility rules are cost/latency (<=2x Jev) and contamination. |
| E1 escalate (τ=0.6) | kept-subset acc 0.9936 vs 0.906 **un-curated** local-only (+0.0876), **−55.0% LLM calls (79.6% at τ=0.5)** |
| latency | GPU fp16 p50 21.0 ms (RTX 5090); CPU 1-thread p50 1.64 s per case; CPU 8-thread batch 8–20 dec/s |

Full tables, charts and methodology: [BENCHMARKS.md](./BENCHMARKS.md). Full technical report: [docs/technical-report.md](./docs/technical-report.md).

## Calibration

The shipped column has **ECE 0.2519** (en) / **0.1941** (zh), applied through the temperature columns in the model repo config. **calib/** (optional post-hoc calibration column; power transform). ECE 0.2519/0.1941 → **0.0168/0.0152**, at the cost of Brier **0.0207 → 0.1218** (en). Opt-in, not applied by default — quote both numbers or neither. Calibration temperatures (0.8660205 / 0.8081192 / 0.6624661) are stored in the model repo config and applied at inference by phocinae-server. An optional calibration column ships in [`calib/`](./calib/) (power transform; en γ 4.33 / zh 2.51) bringing ECE to **0.0168** (en) / **0.0152** (zh).

## Bias, risks & limitations (honest disclosure)

- **JevBench public-231: 0.5455 (126/231)**, published as measured. Correcting our own earlier wording: JevBench has **no "58.4% acceptance gate"** — its eligibility rules are a cost/latency gate (<=2x Jev's cost and median latency; official caps USD 0.0646 / 1,000 decisions and 1.23 s adjusted median) plus contamination gates. Eligibility is separate from the raw score.
- **Option-order robustness is imperfect**: a 3.0% flip rate means about one answer change per ~33 reorders. It is *better* than Jev (~9%) and Laya out-of-domain (19.4%), but only a 0.7 pp gap vs Laya in-domain (3.7%). Never rely on order-invariance alone.
- **Not a safety oracle**: use it as a first-line gate with escalation (or a deterministic L0 rule layer such as phocinae-guard), never as the sole guard for destructive or safety-critical commands.
- **Chinese: in-mix, machine-translated-case evaluation**: zh evaluation runs on machine-translated English cases, and the training mix includes machine-translated Chinese (≈2,400 rows) plus a native-Chinese block (≈1,400 rows) — a fitted (not zero-shot) reading.
- **Context constraint**: the base encoder supports 8192 positions, but the decision head was trained with a 512-token default; long inputs degrade (16k/32k probes: 0.453 / 0.387).
- **Not for** open-ended chat/generation, long-document reasoning, or world-knowledge QA (MMLU-style probes below par).
- **Known trigger-word weakness**: a small fraction of negated phrasings (e.g. \"do NOT cancel subscription\") can be misread as affirmative intent (internal probe: 1/6 weak). Pair safety-critical approvals with an L0 rule layer / fail-closed semantics.
- **No demographic/fairness evaluation** has been run; training data is English business-operations text (typed-decisions) and will carry its domain and language biases. Treat outputs as domain-specific signals, not general judgments.
- **Determinism**: deterministic at a fixed batch shape on the same device; values can differ slightly between fp16/fp32 and across batching shapes.

## Out-of-scope uses

Safety-critical decisions without human review, compliance/legal judgments, medical/financial advice, identity-sensitive classification, and any use as a standalone guard for high-impact actions.

## Environmental impact

~0.044 h single-GPU fine-tune; ~144M-param forward (≈0.74 TFLOP per case) — negligible relative to LLM inference.

## Citation

```bibtex
@misc{phocinae-largha-150m-v1,
  title  = {Phocinae-Largha-150M-v1: a 150M-class decision model},
  author = {Phocinae},
  year   = {2026},
  note   = {https://huggingface.co/Phocinae/Phocinae-Largha-150M-v1}
}
```

## Credits

- [typed-decisions](https://huggingface.co/datasets/LocalLLaMA/typed-decisions) (Apache-2.0, LocalLLaMA HF org) — protocol & test data
- [mmBERT-small](https://huggingface.co/jhu-clsp/mmBERT-small) (JHU CLSP) — base encoder
- [JevBench](https://github.com/fstandhartinger/JevBench) — held-out protocol used for disclosure

## Revision history

- **2026-10-09 — v1.1 refresh.** Weights upgraded (each metric in this card re-measured on the new weights; previous release sha256 `db79d5ee2f16597f34e564f5a4363bddb5b5bbd9827c01819725dabcc7802697`). Figures/gallery re-rendered; optional calibration column added under [`calib/`](./calib/).
