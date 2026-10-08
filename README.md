---
language:
- en
- zh
license: apache-2.0
library_name: transformers
pipeline_tag: text-classification
tags:
- decision-making
- typed-decisions
- text-classification
- small-model
- bilingual
- calibration
- option-order-invariance
- systemone
- zero-output-tokens
- on-premise
base_model: jhu-clsp/mmBERT-small
datasets:
- LocalLLaMA/typed-decisions
thumbnail: figures/C1_typed_acc_comparison.png
widget:
- text: "State: The system processed 3 invoices without errors.\nQuestion: Which action should be taken next?\nOptions: A) Approve batch  B) Retry the batch  C) Flag for human review"
  example_title: "choice — pick one of three"
  output:
  - label: "A) Approve batch"
    score: 0.62
  - label: "B) Retry the batch"
    score: 0.24
  - label: "C) Flag for human review"
    score: 0.14
- text: "State: The user asks the agent to delete the production database and purge all backups.\nQuestion: Should this action be allowed?\nAnswer: yes or no."
  example_title: "noul — allow/deny gate"
  output:
  - label: "no"
    score: 0.93
  - label: "yes"
    score: 0.07
- text: "State: The candidate's resume shows 5 years of backend engineering experience.\nQuestion: Rate how well the candidate matches criterion 'experience'.\nAnswer: 1 (worst) to 7 (best)."
  example_title: "score — 1..7 rating"
  output:
  - label: "6"
    score: 0.72
---

<p align="center">
  <img alt="License" src="https://img.shields.io/badge/License-Apache%202.0-blue?style=flat-square">
  <img alt="Params" src="https://img.shields.io/badge/Params-144.3M-orange?style=flat-square">
  <img alt="Typed ACC" src="https://img.shields.io/badge/Typed%20ACC-en%200.797%20%2F%20zh%200.789-brightgreen?style=flat-square">
  <img alt="Latency" src="https://img.shields.io/badge/Latency-18.6ms%20GPU%20fp16-9cf?style=flat-square">
  <a href="https://github.com/Phocinae/Phocinae-Largha-150M-v1"><img alt="GitHub Stars" src="https://img.shields.io/github/stars/Phocinae/Phocinae-Largha-150M-v1?style=flat-square&logo=github"></a>
  <a href="https://phocinae.github.io/Phocinae-Largha-150M-v1/"><img alt="Site" src="https://img.shields.io/badge/Site-live-brightgreen?style=flat-square"></a>
  <img alt="HF Downloads" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fhuggingface.co%2Fapi%2Fmodels%2FPhocinae%2FPhocinae-Largha-150M-v1&query=%24.downloads&label=HF%20Downloads&color=orange&style=flat-square">
</p>

<div align="center">
  <img src="figures/logo_phocinae.png" width="180" alt="斑海豹 Phocinae logo">
  <h1>斑海豹 · Phocinae-Largha-150M-v1</h1>
  <p><strong>小海豹，大决断。</strong> / <em>Tiny model. Big decisions.</em></p>
  <p><em>一斑见全豹，一点定全局。</em> / <em>Spotted seal. Spot-on calls.</em></p>
</div>

斑海豹 **Largha**, the spotted seal: a **144.3M bilingual decision model** (150M-class) for structured decisions — one forward pass per decision, on your own hardware. Not a chat model: it takes a `state` plus a list of typed questions (`noul` yes/no · `choice` pick-one · `score` 2–10) and returns calibrated answers with confidence, robust to option reordering. Downloads: [Hugging Face](https://huggingface.co/Phocinae/Phocinae-Largha-150M-v1) · [GitHub](https://github.com/Phocinae/Phocinae-Largha-150M-v1) · [ModelScope 魔搭](https://modelscope.cn/models/PerryLink/Phocinae-Largha-150M-v1) · [官网 / Landing page](https://phocinae.github.io/Phocinae-Largha-150M-v1/) · 中文: [FAQ 中文版](docs/faq.zh.md) · [场景演示画廊](docs/gallery/README_cn.md).

## TL;DR

| TL;DR | value |
|---|---|
| parameters | **144.3M** (mmBERT-small base: hidden 384 × 22 layers × 6 heads, 256k-vocab tokenizer, RoPE + sliding-window + full attention; base context 8192, default head 512) |
| typed-decisions en (400 cases / 2000 decisions) | **0.797** — Laya 0.766 · JEV 0.727 · meraGPT 0.768 (same protocol) |
| typed-decisions zh (translated cases, no zh training rows) | **0.789** |
| option-order flip robustness (lower is better) | CPU fp32: flip150 **0.0300** · flip400 **0.0300** · random-mean **0.0233** · any **0.0433** (GPU fp16 0.027/0.028, note only) |
| inference latency | GPU fp16 p50 **18.6 ms** · CPU single-thread p50 **1.51 s per case** (1 case = 1 state + 5 questions, single forward pass; ≈0.28 s per decision) · CPU 8-thread batch **8–21 decisions/s** |
| JevBench public-231 | **0.5108** (118/231) — below the 58.4% gate, disclosed honestly; tool_selection 12/12 |
| escalate routing (E1 gate, τ=0.6) | **+0.089 kept-subset acc** (0.797→0.886 (kept subset)) while **−54.4% LLM cost (82.8% at τ=0.5)** (45.7% escalate to LLM) |
| calibration | shipped column ECE **0.1313**; calibration temperatures 0.7698/0.7879/0.7560 (applied at inference) |

Full numbers, methodology, and evidence: **[BENCHMARKS.md](./BENCHMARKS.md)**.

## See it in action

<div align="center">
  <img src="figures/C1_typed_acc_comparison.png" width="600" alt="typed accuracy comparison"/>
  <p><em>图 1 · typed-decisions accuracy: 0.797 (en) / 0.789 (zh) — Laya 0.766 · JEV 0.727 · meraGPT 0.768</em></p>
  <img src="figures/C7_routing_savings.png" width="600" alt="routing savings"/>
  <p><em>图 2 · escalate routing (τ=0.6): accuracy 0.797→0.886 (kept subset), LLM calls −54.4% (82.8% at τ=0.5)</em></p>
  <img src="docs/gallery/G25_race_local_vs_api.gif" width="600" alt="local vs API race"/>
  <p><em>图 3 · 同一决策：本地 18.6 ms vs API 往返 1.51 s（81×）</em></p>
  <img src="docs/gallery/S01_rmrf_gate.gif" width="600" alt="command gate"/>
  <p><em>图 4 · 命令审批门：rm -rf 在 18.6 ms 内拦截，p(deny)=0.96</em></p>
</div>

**📽️ 全部 27 个场景演示 → [docs/gallery/](./docs/gallery/)**（审批安全 · 路由省费 · 实时分级 · 办公文档 · 流程工程 · 对照与可靠性；中文版 [gallery/README_cn.md](./docs/gallery/README_cn.md)）

## Why Phocinae: slash agent costs

**54.4% fewer LLM calls, 18.6 ms per decision.** Phocinae-Largha-150M (144.3M params) routes the repetitive decisions inside agent sessions — command approvals, tool selection (12/12 on JevBench tool_selection, k≤10), step checks, output screening — to a local single-forward-pass engine (8192-token base context, 512-token default head) instead of a 500–4,000-token API call. The τ=0.6 confidence gate cuts LLM traffic 54.4% while combined accuracy edges up 0.797 → 0.886 (kept subset); deterministic inference means auditable, replayable decisions with zero data leaving your machine — at 18.6 ms GPU p50 vs 1.5 s+ API round-trips. ≈11.4M LLM tokens ≈ **$326/yr** saved per 10k routed decisions/month (Claude Sonnet 5 list prices, Oct 2026). Full cost model: [docs/cost-savings.md](./docs/cost-savings.md).

<div align="center">
  <img src="figures/C2_latency_comparison.png" width="600" alt="latency comparison"/>
  <p><em>图 5 · per-decision latency: GPU fp16 18.6 ms · CPU single-thread 1.51 s/case · CPU 8-thread batch 8–21 decisions/s</em></p>
  <img src="figures/C8_params_vs_latency.png" width="600" alt="params vs latency"/>
  <p><em>图 6 · 144.3M 参数、288.6 MB 权重、1.6 GB 推理峰值显存 — 一张普通显卡即可本地运行</em></p>
  <img src="figures/C6_bilingual.png" width="600" alt="bilingual"/>
  <p><em>图 7 · 双语决策：同一判定中英并排 en 0.797 / zh 0.789</em></p>
</div>

## Quick start — phocinae-server

The official runtime is **[phocinae-server](https://github.com/Phocinae/phocinae-server)**: a local FastAPI service (127.0.0.1 only) that loads these weights with a pure PyTorch forward (no extra runtime needed). Full spec: [docs/protocol.md](./docs/protocol.md). Hardware tiers: [docs/deployment.md](./docs/deployment.md).
```bash
pip install phocinae-server
PHOC_MODEL_DIR=/path/to/Phocinae-Largha-150M-v1 python -m phocinae.main   # http://127.0.0.1:8155
```

One decision:
```bash
curl -s http://127.0.0.1:8155/v1/systemone -H 'Content-Type: application/json' -d '{
  "model": "Phocinae-Largha-150M-v1",
  "state": "The agent restarted nginx after checking the logs and the health endpoint is green.",
  "questions": [
    {"id": "ok",   "type": "noul",   "threshold": 0.65},
    {"id": "act",  "type": "choice", "options": ["allow", "ask", "deny"]},
    {"id": "risk", "type": "score"}
  ]
}'
```

```json
{
  "model": "Phocinae-Largha-150M-v1",
  "answers": {"ok": true, "act": 0, "risk": 2},
  "usage": {"input_tokens": 24, "output_tokens": 0},
  "answer_confidence": {"ok": 0.91, "act": 0.72, "risk": 0.18},
  "action": {"act": {"act_probability": 0.72}},
  "routing": {"model": "Phocinae-Largha-150M-v1", "device": "cpu", "perm": "none", "backend": "phocinae-pure-torch"}
}
```

`answers` values: `noul` = bool · `choice` = 0-based option index · `score` = integer 2–10. Errors: **422** (unknown model/type, >64 questions, choice without options, score with options, threshold outside [0,1]) · **413** (>2 MiB body) · **401** (bearer token). Extension keys `answer_confidence` / `action` / `routing` can be disabled with `PHOC_EXTENSIONS=0`.

## Documentation

- **[BENCHMARKS.md](./BENCHMARKS.md)** — full comparison tables, charts, methodology, honest disclosures
- **[MODEL_CARD.md](./MODEL_CARD.md)** — detailed model card: architecture, training, evaluation, bias & limitations
- **[docs/deployment.md](./docs/deployment.md)** — serve, guard, MCP integration; hardware tiers; security notes
- **[docs/protocol.md](./docs/protocol.md)** — the `/v1/systemone` decision protocol
- **[docs/reproduce.md](./docs/reproduce.md)** — evaluation protocols, published numbers, evidence paths
- **[docs/cost-savings.md](./docs/cost-savings.md)** — LLM-cost model for the escalate gate
- **[docs/gallery/](./docs/gallery/)** — 27 application scenarios with animated demos (中文: [gallery/README_cn.md](./docs/gallery/README_cn.md))
- **[docs/faq.md](./docs/faq.md)** — common questions (中文: [faq.zh.md](./docs/faq.zh.md)) · **[docs/technical-report.md](./docs/technical-report.md)** — short technical report

## What it is / what it is not

- **For**: structured decisions — approval gates, tool routing, escalation, document triage, step checks, output screening; anywhere you want a fast, cheap, local decision layer instead of a large model.
- **Not for**: open-ended chat / generation, long-document reasoning, or world-knowledge QA (MMLU-style probes are below par; see MODEL_CARD). Not a safety oracle: use as a first-line gate with escalation, never as the sole guard.

## Honest disclosures

- **JevBench public-231: 0.5108 (118/231) vs a 58.4% acceptance gate — not passed.** We publish the number as measured, and we never train on the eval rows.
- zh results are on translated cases (no native Chinese training rows).
- Flip numbers are measured per option-reorder protocol (lower is better): CPU fp32 0.0300/0.0300 (flip150/400 reversed) · random-mean 0.0233 · any 0.0433. GPU fp16 0.027/0.028 and 1k-row 0.0187/0.0205/0.0431 are note-only values from different protocols.
- Calibration: the shipped column has ECE **0.1313** (en). Calibration temperatures (0.7698/0.7879/0.7560) are stored in the model repo config and applied at inference by phocinae-server. A recommended recalibration column reaching 0.0106 is *not* shipped.

## Weights & license

- `model.safetensors` sha256 `db79d5ee2f16597f34e564f5a4363bddb5b5bbd9827c01819725dabcc7802697` (fp16 storage, 144.3M params); trained from `jhu-clsp/mmBERT-small` on `LocalLLaMA/typed-decisions` (train split + flip-augmented reorderings), recipe in `rl_agent_config.json`.
- **Apache-2.0** (see LICENSE); base encoder `jhu-clsp/mmBERT-small` is MIT (see NOTICE). · Repo layout: `model.safetensors` · `encoder/` · `tokenizer/` · `rl_agent_config.json` · `checkpoint_meta.json` · `figures/` · `docs/`.

## Credits

- [typed-decisions](https://huggingface.co/datasets/LocalLLaMA/typed-decisions) (Apache-2.0, LocalLLaMA HF org) — protocol & test data
- [mmBERT-small](https://huggingface.co/jhu-clsp/mmBERT-small) (JHU CLSP) — base encoder
- [JevBench](https://github.com/fstandhartinger/JevBench) — held-out protocol used for disclosure

## Version & machine-readable sources

- **This release**: `v1.0.0` — pinned tag on the model repository (resolves to commit `9ea45b46`), for reproducible citation.
- **Machine-readable facts** (same numbers as this card, for AI systems and retrieval pipelines): [llms.txt](./llms.txt)
- **Citation metadata**: [CITATION.cff](./CITATION.cff)
- **Landing page** (mirrors this card, with structured data): https://phocinae.github.io/Phocinae-Largha-150M-v1/

## Citation

Machine-readable: [CITATION.cff](./CITATION.cff). BibTeX:

```bibtex
@misc{phocinae2026largha,
  title  = {Phocinae-Largha-150M-v1: A 144M-parameter bilingual typed decision model},
  author = {Phocinae Project},
  year   = {2026},
  url    = {https://huggingface.co/Phocinae/Phocinae-Largha-150M-v1},
  license = {Apache-2.0}
}
```
