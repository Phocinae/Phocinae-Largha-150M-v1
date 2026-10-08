# MODEL CARD — Phocinae-Largha-150M-v1

## Model details

| item | value |
|---|---|
| name | Phocinae-Largha-150M-v1 |
| nickname | 斑海豹 (Largha, the spotted seal) |
| series | 海豹系列 / Phocinae |
| type | encoder-based **decision model** (not a chat/decoder model) |
| parameters | **144.3M** (public: "150M-class") |
| languages | en; zh via translated eval cases (no native zh training rows) |
| license | Apache-2.0 (weights; see LICENSE) |
| base encoder | jhu-clsp/mmBERT-small (JHU CLSP) |
| storage | fp16 safetensors, 288.6 MB |
| sha256 | `db79d5ee2f16597f34e564f5a4363bddb5b5bbd9827c01819725dabcc7802697` |

## Overview

Largha makes one structured decision per forward pass: given a `state` and a list of typed questions (`noul` yes/no, `choice` pick-one, `score` 2–10), it returns calibrated answers with confidence, and is explicitly trained to be robust to option reordering. It is designed as a local decision layer for agents — approval gates, tool routing, escalation, triage — not as a general language model.

## Architecture

- Encoder: mmBERT-small — hidden **384**, **22** layers, **6** heads, vocab **256k**, RoPE (theta 160000), sliding-window (128) + full attention mix, max position **8192**.
- Decision head: 2-layer MLP head (`head_layers: 2`, head context 192), reading mean-pooled encoder output.
- Inference: single forward pass, deterministic for a fixed batch shape (no sampling).

## Training

- Base: `jhu-clsp/mmBERT-small` (upstream pre-training unchanged).
- Fine-tune data: `LocalLLaMA/typed-decisions` train split + flip-augmented option reorderings.
- Recipe (`rl_agent_config.json`): loss `ce+brier`, optimizer `adafactor`, lr_encoder 2e-5 / lr_head 1e-4, micro_batch 8, grad_accum 4, updates 9228, ~1.36 h (local, tag `cf4`); `checkpoint_meta.json`: epoch 1/1, avg_loss 0.9565.
- **No eval rows were used in training** (typed-decisions test split, JevBench held out).

## Inputs & outputs

`POST /v1/systemone`-style protocol (phocinae-server):

- input: `model` ("Phocinae-Largha-150M-v1"), `state` (string), `questions` (list ≤64; each: `id`, `type` ∈ {noul, choice, score}, `options` for choice ≤255, `threshold` for noul ∈ [0,1]).
- output: `answers` = {qid: bool | 0-based option index | int 2–10}; extensions `answer_confidence` (temperature-calibrated top probability), `action`, `option_scores`, `routing`.

Full contract: [docs/protocol.md](./docs/protocol.md).

## Evaluation

| benchmark | result |
|---|---|
| typed-decisions en (400 cases / 2000 decisions) | **0.797** (Laya 0.766 · JEV 0.727 · meraGPT 0.768) |
| typed-decisions zh (translated cases) | **0.789** |
| flip (CPU fp32): flip150 / flip400 / random-mean / any | **0.0300 / 0.0300 / 0.0233 / 0.0433** |
| JevBench public-231 | **0.5108 (118/231)**, gate 58.4% not passed |
| E1 escalate (τ=0.6) | acc 0.789 → 0.7948, **−82% LLM calls** |
| latency | GPU fp16 p50 18.6 ms; CPU 1-thread p50 1.51 s; CPU 8-thread batch 8–21 dec/s |

Full tables, charts and methodology: [BENCHMARKS.md](./BENCHMARKS.md). Full technical report: [docs/technical-report.md](./docs/technical-report.md).

## Calibration

The shipped column has **ECE 0.1313** (en). Calibration temperatures (0.7698 / 0.7879 / 0.7559) are stored in the model repo config and applied at inference by phocinae-server. A recommended recalibration column reaching ECE 0.0106 was measured during development but is **not shipped** — do not claim it for the released weights.

## Bias, risks & limitations (honest disclosure)

- **JevBench gate not passed**: 0.5108 (118/231) vs the 58.4% acceptance gate. Published as measured; we never trained on the eval rows.
- **Option-order robustness is imperfect**: a 3.0% flip rate means about one answer change per ~33 reorders. It is *better* than Jev (~9%) and Laya out-of-domain (19.4%), but only a 0.7 pp gap vs Laya in-domain (3.7%). Never rely on order-invariance alone.
- **Not a safety oracle**: use it as a first-line gate with escalation (or a deterministic L0 rule layer such as phocinae-guard), never as the sole guard for destructive or safety-critical commands.
- **Chinese is translated-only**: zh evaluation runs on translated English cases; the model has no native Chinese training rows.
- **Context constraint**: the base encoder supports 8192 positions, but the decision head was trained with a 512-token default; long inputs degrade (16k/32k probes: 0.453 / 0.387).
- **Not for** open-ended chat/generation, long-document reasoning, or world-knowledge QA (MMLU-style probes below par).
- **No demographic/fairness evaluation** has been run; training data is English business-operations text (typed-decisions) and will carry its domain and language biases. Treat outputs as domain-specific signals, not general judgments.
- **Quantization**: int8 (NNCF weights-only) keeps accuracy but raises CPU latency +49–164% — not recommended; not shipped.
- **Determinism**: deterministic at a fixed batch shape on the same device; values can differ slightly between fp16/fp32 and across batching shapes.

## Out-of-scope uses

Safety-critical decisions without human review, compliance/legal judgments, medical/financial advice, identity-sensitive classification, and any use as a standalone guard for high-impact actions.

## Environmental impact

~1.4 h single-GPU fine-tune; ~144M-param forward (≈0.74 TFLOP per case) — negligible relative to LLM inference.

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
