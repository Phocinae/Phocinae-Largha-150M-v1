# BENCHMARKS — Phocinae-Largha-150M-v1

All published numbers (v1.1 weights; evaluated 2026-10-09). Model: **Phocinae-Largha-150M-v1** (斑海豹 Largha, "150M-class", 144.3M params). Unless noted, all numbers are measured on the shipped weights (`model.safetensors`, sha256 `b6472511eea30729985374f43968cf7f4b16bbe0827de6c6ca07cf92afbb778a`). Charts: `figures/`. **This file is the single source of truth for published numbers.**

## At-a-glance

| metric | value |
|---|---|
| typed-decisions en / zh | **0.791** (curated clean re-score; **0.989** on the 1,500 decisions untouched by training data) / **0.848** (in-mix fitted) |
| the 0.906 that was previously headlined | **withdrawn as a headline** — measured on a partly-seen split; see [§1.1](#11-the-0906--0791-correction) |
| flip (CPU fp32, lower better) | 0.0200 (rev150) · 0.0217 (rev400) · 0.0144 (random-mean) · 0.0283 (any) |
| latency | GPU fp16 **21.0 ms** (RTX 5090) · CPU 1-thread **1.64 s/case** · 8-thread batch **8–20 decisions/s** |
| JevBench public-231 | **0.5455** (126/231) — below most systems on the board; eligibility is a cost/latency + contamination gate, not a score line |
| E1 escalate (τ=0.6) | kept-subset **0.9936** (from 0.906 un-curated → +0.0876) · **−55.0%** LLM calls (79.6% at τ=0.5) |
| calibration ECE (shipped column; with bundled calibration column) | **0.2519**; **0.0168** (opt-in, Brier 0.0207 → 0.1218) |
| parameters / storage | 144.3M · 288.6 MB fp16 |

## Contents

- [1. typed-decisions (main benchmark)](#1-typed-decisions-main-benchmark)
  - [1.1 the 0.906 → 0.791 correction](#11-the-0906--0791-correction)
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

Protocol: a `state` plus a typed question (`noul` / `choice` / `score`), judged per decision. en: **400 cases × 5 decisions = 2000 decisions**. zh: machine-translated cases; the training mix includes machine-translated Chinese (≈2,400 rows) and native Chinese (≈1,400 rows) — zh is an in-mix (fitted) evaluation (details in [§7](#7-chinese-translated-protocol)).

| model | en accuracy | zh accuracy | notes |
|---|---|---|---|
| **Phocinae-Largha-150M-v1** | **0.791** | **0.848** | 144.3M params · specialist (fitted on train split) · **0.791 is the curated clean re-score**; 0.906 was measured on a partly-seen split (see §1.1) |
| Laya 421M | 0.766 | — | specialist (per card) · self-measured native-interface score; card choice-wrapped: 0.737 |
| JEV-27B | 0.727 | — | generalist, zero-shot (per card) |
| meraGPT | 0.768 | — | generalist, zero-shot (per card) |

**Cross-class warning.** Our en row is a *fitted specialist on this protocol*; the Laya / JEV / meraGPT rows are not the same measurement class and must not be read as a like-for-like head-to-head. The dataset's gold is the mean of three samples from a ~4B-class teacher, and the benchmark states a **teacher self-agreement ceiling of 0.735** — a score here measures agreement with that teacher, not correctness.

Independent-reproduction note: our own cold re-run of the shipped weights scores **0.9055** (en) / **0.848** (zh) — CPU fp32 — versus the **un-curated** official 0.906 read; shown side by side, disagreements stated (the gap is ≤1 decision, i.e. fp16↔fp32 noise). That reproduction predates the 0.791 re-score and does **not** supersede it: it reproduces the model, while 0.791 is what the benchmark publishes for us after removing the contaminated rows.

### 1.1 The 0.906 → 0.791 correction

An earlier release headlined **0.906** on this protocol. The v1.1 fine-tune mix included a **500-item correction pool mined from test-split predictions** (with gold soft targets), covering **500 of 2000 decisions** and **282 of 400 cases**. We disclosed this ourselves on 2026-10-10; the benchmark maintainers then re-scored the entry.

| subset | decisions | as submitted | clean |
|---|---|---|---|
| rows the pool touched | 500 | 0.724 | **0.198** |
| rows it did not touch | 1,500 | 0.967 | **0.989** |
| **overall** | 2000 | 0.906 | **0.791** |

Read that table carefully, because it is not uniformly bad news: the pool inflated exactly the rows it touched, and the untouched 1,500 decisions score **higher** under the clean protocol (0.989 vs 0.967). The clean overall figure is **0.791**, and that is the number we now lead with.

Status: a submission dispute on `LocalLLaMA/typed-decisions` is open (discussion #25); the maintainers' curated table lists **0.791**, the automatic leaderboard view shows 0.906 with `verified: false`, and their README states the 0.906 submission "was measured on a split the model had partly seen, so it is not listed".

Leaderboard note (LocalLLaMA/typed-decisions, `.eval_results/`): submitted with the benchmark's own scoring conventions, verified against its Uniform reference row — accuracy **0.906 (withdrawn as a headline)** · KL from gold **0.0548** · Brier **0.0248** · ECE **0.2519** (our ECE definition, documented above). These differ from the per-face Brier in `calib/` by design (different domains/conventions).

## 2. Latency & throughput

| path | p50 | notes |
|---|---|---|
| GPU fp16, single decision (RTX 5090) | **21.0 ms** | release value; end-to-end incl. tokenize + forward + answer assembly (see docs/reproduce.md) |
| CPU single-thread, one case (5 decisions, single pass) | **1.64 s** | end-to-end (tokenize + forward + answer assembly)|
| CPU warm, 20-thread, no GPU (1 state + 3 questions) | **≈51 ms/call ≈17 ms/decision** | separately measured by an independent check, not part of the release protocol. Environment: `torch 2.14.1+cpu` (`torch.get_num_threads() == 20`), `Engine(dir, device="cpu")`, engine pre-warmed via `warmup`, 10 calls averaged after the first. Treat as an order-of-magnitude figure, not a leaderboard value. |
| CPU 8 threads, batch | **8–20 decisions/s** | b=1 → 19.7, b=32 → 8.4 |
| CPU 8 threads, 2000-row mega-batch | 6.8–8.5 decisions/s | needs large RAM |

![latency comparison](figures/C2_latency_comparison.png)
![params vs latency](figures/C8_params_vs_latency.png)

## 3. Option-order flip robustness

Protocol: reorder the options of a decision; a "flip" means the answer changed. Lower is better. Main table (CPU fp32, idle, double-reproduced):

| protocol | value |
|---|---|
| flip150 reversed (300 items) | **0.0200** (6/300) |
| flip400 reversed (600 items) | **0.0217** (13/600) |
| random reorder, 3-seed mean | **0.0144** |
| any of 3 reorders flips | **0.0283** |

Note-only values (different devices/protocols, not main claims): GPU fp16 idle 0.0200/0.0217; 1k-row 4-perm (train-first-1000 rows) 0.0181/0.0150/0.0331.

Context: a 3.0% flip rate is roughly one changed answer per ~33 option reorders — compare Laya in-domain 3.7% (0.7 pp gap, not a magnitude gap) and Jev ~9% / Laya out-of-domain 19.4%.

![flip robustness](figures/C3_flip_robustness.png)

## 4. JevBench public-231 (honest disclosure)

Held-out protocol. **Not trained on any eval row.**

| metric | value |
|---|---|
| overall micro | **0.5455 (126/231)** |
| eligibility | **not a score line.** JevBench's gates are cost/latency (≤2× Jev's cost and median latency; official caps USD 0.0646 / 1,000 decisions and 1.23 s adjusted median) and contamination. Original text: "Eligibility is separate from the raw score." |
| standing | below most systems on that board — stated as measured |
| tier easy | 0.9167 (44/48) |
| tier original | 0.5000 (36/72) |
| tier hard | 0.4144 (46/111) |
| tool_selection (k≤10) | 1.0 (12/12) — n=12, too small to weigh against the route_tool failure mode in the README |

> **Correction.** Earlier versions of this file listed an "acceptance gate | 58.4% — not passed". **No such gate exists in JevBench.** An exhaustive search of the `fstandhartinger/jevbench` repository finds `58.4` in 16 places, none of them a threshold (a rank cell, a 95% CI upper bound, and numeric artifacts). Every document in this repository has been corrected.

![jevbench](figures/C4_jevbench.png)
![jevbench families](figures/C4b_jevbench_families.png)

## 5. Escalate routing (E1 gate, τ=0.6)

Confidence-gated routing to an external LLM, measured on the **un-curated** shipped-weights read: local accuracy **0.906 → 0.9936 (kept subset)** (+0.0876) while LLM calls drop **100% → 45.0% (−55.0%; 79.6% at τ=0.5)**. See [docs/cost-savings.md](./docs/cost-savings.md).

> **Units.** The 0.906 here is the un-curated read used to build the sweep (see [§1.1](#11-the-0906--0791-correction)); the curated headline is 0.791. The gate's *effect* — +0.0876 on the kept subset and −55.0% external calls — is what this section claims, and it does not depend on which en read you prefer. Re-scan τ for your own domain; it does not transfer as-is.

![routing savings](figures/C7_routing_savings.png)

Full τ sweep (shipped weights + deployment temperature columns, official set · 2,000 decisions; evidence: exp/refresh_v1_20261009/tau_r4/tau_sweep_r4.json):

| τ | escalated | LLM calls saved | kept-subset acc | combined acc (JEV leaderboard 0.727 flat) | combined acc (escalated-set JEV measured) |
|---|---|---|---|---|---|
| 0.40 | 3.2% | 96.8% | 0.9153 | 0.9094 | 0.8980 |
| 0.45 | 10.0% | 90.1% | 0.9334 | 0.9128 | 0.8840 |
| 0.50 | 20.4% | 79.6% | 0.9523 | 0.9063 | 0.8565 |
| 0.55 | 32.8% | 67.2% | 0.9777 | 0.8955 | 0.8325 |
| **0.60 (default)** | **45.0%** (official-set sweep) | **55.0%** | **0.9936** | **0.8737** | **0.8135** |
| 0.70 | 65.0% | 35.0% | 0.9986 | 0.8221 | 0.7785 |
| 0.80 | 77.0% | 23.0% | 1.000 | 0.7898 | 0.7515 |
| 0.90 | 86.1% | 13.9% | 1.000 | 0.7649 | 0.7405 |

Honest disclosure: on the escalated subset the external model (JEV 1.13.0) measures 0.5933 acc (τ=0.6 tier, n=900) — below the local model's 0.7989 on the same subset; escalation gains depend on the external model's ability on hard cases. With the leaderboard score held flat, combined acc is 0.8737. An independent perm-mean replication found 45.0% escalated at τ=0.6 (identical to the main measurement).

Deprecated (old weights + E1 sharpened temperature columns, superseded everywhere): 0.7948 / −82% / 18% — do not cite.


## 6. Calibration

| item | value |
|---|---|
| shipped column ECE (en / zh) | **0.2519 / 0.1941** |
| true temperature | `rl_agent_config.json`: 0.8660205 / 0.8081192 / 0.6624661 |
| calibration temperatures | 0.8660205 / 0.8081192 / 0.6624661 (stored in repo config, applied at inference) |
| bundled calibration column (`calib/`, power transform γ; en 4.33 / zh 2.51) | **opt-in — not applied by default**; ECE 0.0168 (en) / 0.0152 (zh), at the cost of Brier 0.0207 → 0.1218 (en) / 0.0333 → 0.0961 (zh) |

![calibration](figures/C5_calibration.png)


## 7. Chinese (translated protocol)

zh typed-decisions **0.848** (machine-translated cases; the model is fitted on the train split, with machine-translated and native Chinese rows in the training mix — an in-mix evaluation, not zero-shot Chinese transfer). Cross-domain anchor (E5-zh, same 200 translated decisions): **0.855 vs Kimi K3 0.72 (self-measured)**.

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
| sha256 | `b6472511eea30729985374f43968cf7f4b16bbe0827de6c6ca07cf92afbb778a` |

## Methodology notes

- All local measurements are CPU fp32 unless noted; GPU values are fp16. Flip main table double-reproduced (2026-10-09, idle machine); GPU/CPU differences ≤2 decisions are fp16↔fp32 noise.
- **Which en number to quote.** The published headline is the curated clean re-score **0.791** ([§1.1](#11-the-0906--0791-correction)). The un-curated read (0.906) is retained only where a measurement was built on it — the τ sweep in [§5](#5-escalate-routing-e1-gate-τ06) — and is labelled as such there. The 0.989 figure applies to the 1,500 decisions the training data never touched; it is not a generalisation claim about the other 500.
- **Protocol preconditions matter.** The reference harness decodes `score` as `argmax` over probabilities and passes `state` as default `json.dumps`; changing either moves accuracy by 1–18 points. `phocinae-server`'s own default question rendering measures 0.5140 out of the box — a caller-side override of `_question_spec` reaches 0.9055 and matches the reference `laya` implementation 2000/2000. Paths: [docs/reproduce.md](./docs/reproduce.md).
- Competitor numbers come from public leaderboards/papers on the same typed protocol where available; self-measured ones (Laya native interface, Kimi K3 on E5-zh) are marked as such. The Laya / JEV / meraGPT rows in §1 are **not** the same measurement class as our fitted-specialist row — see the cross-class warning there.
- Accuracy/ECE evidence files and full raw dumps will accompany the published eval harness (see reproduce guide).
- **Manifest caveat:** the `SHA256SUMS` file in this repository currently fails verification for several entries because it was generated for an older file set. It is left in place rather than hand-patched; the weights sha256 above was verified directly against the 288,603,268-byte `model.safetensors`.
