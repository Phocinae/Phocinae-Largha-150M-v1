# BENCHMARKS — Phocinae-Largha-150M-v1

All published numbers (evaluated 2026-10-08). Model: **Phocinae-Largha-150M-v1** (斑海豹 Largha, "150M-class", 144.3M params). Unless noted, all numbers are measured on the shipped weights (`model.safetensors`, sha256 `db79d5ee2f16597f34e564f5a4363bddb5b5bbd9827c01819725dabcc7802697`). Charts: `figures/`. **This file is the single source of truth for published numbers.**

## At-a-glance

| metric | value |
|---|---|
| typed-decisions en / zh | **0.797 / 0.789** |
| flip (CPU fp32, lower better) | 0.0300 (rev) · 0.0233 (random-mean) · 0.0433 (any) |
| latency | GPU fp16 **18.6 ms** · CPU 1-thread **1.51 s/case** · 8-thread batch **8–21 decisions/s** · CPU warm 20-thread **≈51 ms/call** |
| JevBench public-231 | **0.5108** (118/231) — gate 58.4% **not passed** |
| E1 escalate (τ=0.6) | kept-subset **0.886** · **−54.4%** LLM calls (82.8% at τ=0.5) |
| calibration ECE (shipped) | **0.1313** |
| parameters / storage | 144.3M · 288.6 MB fp16 |

## Contents

- [1. typed-decisions (main benchmark)](#1-typed-decisions-main-benchmark)
- [2. Latency & throughput](#2-latency--throughput)
- [3. Option-order flip robustness](#3-option-order-flip-robustness)
- [4. JevBench public-231](#4-jevbench-public-231-honest-disclosure)
- [5. Escalate routing (E1 gate)](#5-escalate-routing-e1-gate-τ06)
- [6. Calibration](#6-calibration)
- [7. Chinese (translated protocol)](#7-chinese-translated-protocol)
- [8. Context](#8-context)
- [9. Parameters & storage](#9-parameters--storage)
- [Methodology notes](#methodology-notes)

## 1. typed-decisions (main benchmark)

Protocol: a `state` plus a typed question (`noul` / `choice` / `score`), judged per decision. en: **400 cases × 5 decisions = 2000 decisions**. zh: translated cases only — **no native Chinese training rows** (details in [§7](#7-chinese-translated-protocol)).

| model | en accuracy | zh accuracy | notes |
|---|---|---|---|
| **Phocinae-Largha-150M-v1** | **0.797** | **0.789** | 144.3M params |
| Laya 421M | 0.766 | — | same typed protocol |
| JEV-27B | 0.727 | — | same typed protocol |
| meraGPT | 0.768 | — | same typed protocol |

![typed accuracy comparison](figures/C1_typed_acc_comparison.png)
![bilingual en/zh](figures/C6_bilingual.png)

## 2. Latency & throughput

| path | p50 | notes |
|---|---|---|
| GPU fp16, single decision | **18.6 ms** | release value |
| CPU single-thread, one case (5 decisions, single pass) | **1.51 s** | release value; end-to-end (tokenize + forward + answer assembly); ≈0.28 s per decision |
| CPU warm, 20-thread, no GPU (1 state + 3 questions) | **≈51 ms/call ≈17 ms/decision** | separately measured by an independent check, not part of the release protocol. Environment: `torch 2.14.1+cpu` (`torch.get_num_threads() == 20`), `Engine(dir, device="cpu")`, engine pre-warmed via `warmup`, 10 calls averaged after the first. Same machine class as the release runs. Treat as an order-of-magnitude figure, not a leaderboard value. |
| CPU 8 threads, batch | **8–21 decisions/s** | b=1 → 21.0, b=32 → 8.7 |
| CPU 8 threads, 2000-row mega-batch | 7–9 decisions/s | needs large RAM |

![latency comparison](figures/C2_latency_comparison.png)
![params vs latency](figures/C8_params_vs_latency.png)

## 3. Option-order flip robustness

Protocol: reorder the options of a decision; a "flip" means the answer changed. Lower is better. Main table (CPU fp32, idle, double-reproduced):

| protocol | value |
|---|---|
| flip150 reversed (300 items) | **0.0300** (9/300) |
| flip400 reversed (600 items) | **0.0300** (18/600) |
| random reorder, 3-seed mean | **0.0233** |
| any of 3 reorders flips | **0.0433** |

Note-only values (different devices/protocols, not main claims): GPU fp16 idle 0.027/0.028; 1k-row 4-perm (train-first-1000 rows) 0.0187/0.0205/0.0431.

Context: a 3.0% flip rate is roughly one changed answer per ~33 option reorders — compare Laya in-domain 3.7% (0.7 pp gap, not a magnitude gap) and Jev ~9% / Laya out-of-domain 19.4%.

![flip robustness](figures/C3_flip_robustness.png)

## 4. JevBench public-231 (honest disclosure)

Held-out protocol. **Not trained on any eval row.**

| metric | value |
|---|---|
| overall micro | **0.5108 (118/231)** |
| acceptance gate | 58.4% — **not passed** |
| tier easy | 0.8958 (43) |
| tier original | 0.4167 (30) |
| tier hard | 0.4054 (45) |
| family-macro | 0.4829 |
| tool_selection (k≤10) | 1.0 (12/12) |

![jevbench](figures/C4_jevbench.png)
![jevbench families](figures/C4b_jevbench_families.png)

## 5. Escalate routing (E1 gate, τ=0.6)

Confidence-gated routing to an external LLM: local accuracy **0.797 → 0.886 (kept subset)** (+0.089) while LLM calls drop **100% → 45.7% (−54.4%; 82.8% at τ=0.5)**. See [docs/cost-savings.md](./docs/cost-savings.md).

![routing savings](figures/C7_routing_savings.png)

## 6. Calibration

| item | value |
|---|---|
| shipped column ECE (en) | **0.1313** |
| true temperature | `rl_agent_config.json`: 0.7698 / 0.7879 / 0.7560 |
| calibration temperatures | 0.7698 / 0.7879 / 0.7560 (stored in repo config, applied at inference) |
| recommended recalibration column (A1, T=(0.62,0.52,0.52)) | 0.0106 — **not shipped** |

![calibration](figures/C5_calibration.png)


## 7. Chinese (translated protocol)

zh typed-decisions **0.789** (translated cases). Cross-domain anchor (E5-zh, same 200 translated decisions): **0.83 vs Kimi K3 0.72**.

![zh anchor](figures/C9_zh_anchor.png)

## 8. Context

| item | value |
|---|---|
| encoder max position embeddings | **8192** |
| default decision-head length | **512** (self-imposed training/inference default) |
| 16k / 32k row probes | 0.453 / 0.387 (long-context degradation) |

## 9. Parameters & storage

| item | value |
|---|---|
| parameters | **144.3M** (144,292,870; raw tensor sum 144,292,870) |
| architecture | mmBERT-small: hidden 384 × 22 layers × 6 heads, 256k vocab, RoPE + sliding-window + full attention |
| storage | fp16 safetensors 288.6 MB |
| sha256 | `db79d5ee2f16597f34e564f5a4363bddb5b5bbd9827c01819725dabcc7802697` |

## Methodology notes

- All local measurements are CPU fp32 unless noted; GPU values are fp16. Flip main table double-reproduced (2026-10-07, idle machine); GPU/CPU differences ≤2 decisions are fp16↔fp32 noise.
- Competitor numbers (Laya / JEV / meraGPT / Kimi) come from public leaderboards/papers on the same typed protocol where available; see [docs/reproduce.md](./docs/reproduce.md) for evidence paths and the eval harness.
- Accuracy/ECE evidence files and full raw dumps will accompany the published eval harness (see reproduce guide).
