# Cost model — escalate routing (E1 gate)

How routing repetitive agent decisions through Phocinae-Largha-150M-v1 cuts LLM spend.

## Mechanism

The E1 gate (τ=0.6) runs one local forward pass per decision and reads `answer_confidence` — the temperature-calibrated top probability. Decisions below τ are escalated to an external LLM (or a human); the rest are answered locally for (near) zero marginal cost.

## Measured effect (typed-decisions protocol, en · 400 cases / 2,000 decisions)

Official numbers (frozen 2026-10-08) and independent reproductions are shown side by side; where they disagree, we say so. Deprecated headline claims are listed in a separate column so they cannot be mistaken for current numbers.

| metric | official (frozen 2026-10-08) | independent reproduction | deprecated claim |
|---|---|---|---|
| local-only accuracy (en) | **0.797** | 0.7825 / 0.7820 | 0.797 (unchanged) |
| kept-subset accuracy at τ=0.6 | **0.886** | — | — |
| decisions escalated at τ=0.6 | **45.7%** (45.65%) | 40.9% (deployment recompute; 41–46% range) | 18% |
| LLM calls saved at τ=0.6 | **54.4%** | — | 82% |
| LLM calls saved at τ=0.5 | **82.8%** (17.15% escalated; kept-subset 0.821) | — | — |

**"−82% LLM calls" and "τ=0.6" cannot both be true.** At the frozen τ=0.6 the measured reduction is 54.4%; the 82.8% headline belongs to τ≈0.50 (where 17.15% of decisions escalate and kept-subset accuracy is 0.821). Both thresholds are real and tunable; the docs below quote the τ=0.6 default.

The gate answers ~1 of every 2 decisions locally with an 18.6 ms (GPU) / 1.51 s-per-case (CPU) forward pass, and escalates the rest.

## Worked example

- 10,000 routed decisions/month, ~1,720 tokens per LLM call → ≈11.4M LLM tokens/month.
- At Claude Sonnet 5 list prices (Oct 2026) that is **≈ $326/yr saved** per 10k routed decisions/month, before local compute (negligible: 144.3M-param forwards).

## Throughput context

- CPU 8-thread batch: **8–21 decisions/s** (b=1 → 21.0, b=32 → 8.7) — local pre-screening capacity.
- GPU fp16: p50 18.6 ms/decision.
- Local screening time is the main cost trade-off: on CPU budget ~1.5 s per single-threaded case (≈0.28 s per decision) (or batch on 8 threads); on GPU it is effectively free relative to an API round-trip.

## Caveats (read before quoting)

- Cost figures are **estimates on public list prices**; actual savings depend on your workload mix, your LLM pricing, and how many decisions really are routine.
- The τ=0.6 gate is set for the typed-decisions domain. **Re-scan τ for new domains** before assuming the same 54.4% call reduction (82.8% at τ=0.5) and +0.089 kept-subset accuracy hold.
- The model is a decision layer, not a replacement for LLM judgment: anything it is unsure about is escalated by design (that is where the 45.7% goes).
- Numbers are relative framing, not absolute revenue promises.
