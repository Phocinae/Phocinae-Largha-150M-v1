# Cost model — escalate routing (E1 gate)

How routing repetitive agent decisions through Phocinae-Largha-150M-v1 cuts LLM spend.

## Mechanism

The E1 gate (τ=0.6) runs one local forward pass per decision and reads `answer_confidence` — the temperature-calibrated top probability. Decisions below τ are escalated to an external LLM (or a human); the rest are answered locally for (near) zero marginal cost.

## Measured effect (typed-decisions protocol, en · 400 cases / 2,000 decisions)

Official numbers (frozen 2026-10-09) and independent reproductions are shown side by side; where they disagree, we say so. Deprecated headline claims are listed in a separate column so they cannot be mistaken for current numbers.

| metric | official (frozen 2026-10-09) | independent reproduction | deprecated claim |
|---|---|---|---|
| local-only accuracy (en / zh) | **0.906 / 0.848** | **0.9055** (en) / **0.848** (zh) — CPU fp32 re-runs | — |
| kept-subset accuracy at τ=0.6 | **0.9936** | — | — |
| decisions escalated at τ=0.6 | **45.0%** (official-set sweep) | — | — |
| LLM calls saved at τ=0.6 | **55.0%** | — | — |
| LLM calls saved at τ=0.5 | **79.6%** (20.4% escalated; kept-subset 0.9523) | — | — |

**"−79.6% LLM calls" and "τ=0.6" cannot both be true.** At the frozen τ=0.6 the measured reduction is 55.0%; the 79.6% headline belongs to τ≈0.50 (where 20.4% of decisions escalate and kept-subset accuracy is 0.9523). Both thresholds are real and tunable; the docs below quote the τ=0.6 default.

<div align="center">
  <img src="../figures/C7_routing_savings.png" width="600" alt="routing savings"/>
  <p><em>图 · E1 escalate 门（τ=0.6）：保留集 acc 0.906→0.9936，LLM 调用 −55.0%（τ=0.5 档 −79.6%）</em></p>
</div>

The gate answers ~55% of decisions locally with an 21.0 ms (RTX 5090) (GPU) / 1.64 s-per-case (CPU) forward pass, and escalates the rest.

## τ sweep (shipped weights, deployment temperature columns, official set · 2,000 decisions)

| τ | escalated | LLM calls saved | kept-subset acc |
|---|---|---|---|
| 0.40 | 3.2% | 96.8% | 0.9153 |
| 0.45 | 10.0% | 90.1% | 0.9334 |
| 0.50 | 20.4% | 79.6% | 0.9523 |
| **0.60 (default)** | **45.0%** (official-set sweep) | **55.0%** | **0.9936** |
| 0.70 | 65.0% | 35.0% | 0.9986 |
| 0.80 | 77.0% | 23.0% | 1.000 |
| 0.90 | 86.1% | 13.9% | 1.000 |

Evidence: `exp/refresh_v1_20261009/tau_r4/tau_sweep_r4.json` (v1.1 weights · official set · shipped temperature column); confidence = temperature-calibrated top probability with the shipped temperature columns (0.8660205/0.8081192/0.6624661).

## Worked example (recomputed 2026-10-09, grounded in the shipped test rows)

- 10,000 routed decisions/month at τ=0.6 → 45.0% escalated = 4,500 LLM calls/month.
- Average escalated prompt = 204 tokens (state + question + options; measured with the shipped tokenizer on `datasets/typed_test/test_typed_400.jsonl`), plus ~50 output tokens per call.
- LLM bill at Claude Sonnet 5 permanent list prices (Anthropic rate card, effective 2026-08-10: $2/M input, $10/M output): 0.92M × $2 + 0.23M × $10 ≈ **$4.1/month ≈ $50/yr** per 10k routed decisions/month.
- Baseline (routing every decision to the LLM, same volume): ≈ $9.1/month ≈ $109/yr. The gate therefore removes ≈ **55% of the LLM spend**, consistent with the −55.0% call reduction.
- These are tokenizer-dependent estimates (Claude's tokenizer may count ±30% differently); before local compute, which is negligible (144.3M-param forwards on CPU/GPU).
- Superseded: an earlier draft quoted ≈$326/yr using a different token assumption and pre-August pricing; it is withdrawn.

## Throughput context

- CPU 8-thread batch: **8–20 decisions/s** (b=1 → 21.0, b=32 → 8.7) — local pre-screening capacity.
- GPU fp16: p50 21.0 ms (RTX 5090)/decision.
- Local screening time is the main cost trade-off: on CPU budget ~1.5 s per single-threaded case (or batch on 8 threads); on GPU it is effectively free relative to an API round-trip.

## Caveats (read before quoting)

- Cost figures are **estimates on public list prices**; actual savings depend on your workload mix, your LLM pricing, and how many decisions really are routine.
- The τ=0.6 gate is set for the typed-decisions domain. **Re-scan τ for new domains** before assuming the same 55.0% call reduction (79.6% at τ=0.5) and +0.0876 kept-subset accuracy hold.
- The model is a decision layer, not a replacement for LLM judgment: anything it is unsure about is escalated by design (that is where the 45.0% goes).
- Numbers are relative framing, not absolute revenue promises.
