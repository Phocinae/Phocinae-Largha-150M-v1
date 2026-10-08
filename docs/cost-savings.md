# Cost model — escalate routing (E1 gate)

How routing repetitive agent decisions through Phocinae-Largha-150M-v1 cuts LLM spend.

## Mechanism

The E1 gate (τ=0.6, frozen) runs one local forward pass per decision and reads `answer_confidence` — the temperature-calibrated top probability. Decisions below τ are escalated to an external LLM (or a human); the rest are answered locally for (near) zero marginal cost.

## Measured effect (typed-decisions protocol)

| metric | value |
|---|---|
| local-only accuracy | 0.789 |
| combined accuracy (local + escalate) | **0.7948** (+0.006) |
| decisions escalated to LLM | 18% |
| LLM calls | **−82%** (100% → 18%) |

The gate improves combined accuracy while replacing ~4 of every 5 LLM calls with a local 18.6 ms (GPU) / 1.51 s (CPU) forward pass.

## Worked example

- 10,000 routed decisions/month, ~1,720 tokens per LLM call → ≈17.2M LLM tokens/month.
- At Claude Sonnet 5 list prices (Oct 2026) that is **≈ $492/yr saved** per 10k routed decisions/month, before local compute (negligible: 144.3M-param forwards).

## Throughput context

- CPU 8-thread batch: **8–21 decisions/s** (b=1 → 21.0, b=32 → 8.7) — local pre-screening capacity.
- GPU fp16: p50 18.6 ms/decision.
- Local screening time is the main cost trade-off: on CPU budget ~1.5 s per single-threaded decision (or batch on 8 threads); on GPU it is effectively free relative to an API round-trip.

## Caveats (read before quoting)

- Cost figures are **estimates on public list prices**; actual savings depend on your workload mix, your LLM pricing, and how many decisions really are routine.
- The τ=0.6 gate is frozen for the typed-decisions domain. **Re-scan τ for new domains** before assuming the same 82% call reduction and +0.006 accuracy hold.
- The model is a decision layer, not a replacement for LLM judgment: anything it is unsure about is escalated by design (that is where the 18% goes).
- Numbers are relative framing, not absolute revenue promises.
