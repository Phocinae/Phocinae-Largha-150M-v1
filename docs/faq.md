# FAQ — Phocinae-Largha-150M-v1

Questions people ask about Largha (斑海豹, the spotted seal), a **144.3M bilingual decision model**. All figures quoted here are from [BENCHMARKS.md](../BENCHMARKS.md) — the source of truth for published numbers.

## 1. What is this model, exactly?

An encoder-based **decision model**, not a chat model. One forward pass turns a `state` plus typed questions (`noul` yes/no, `choice` pick-one, `score` 2–10) into calibrated answers with confidence. No text generation, no sampling — deterministic for a fixed batch shape.

## 2. How do I run it locally?

The official runtime is [phocinae-server](https://github.com/Phocinae/phocinae-server) (pure-torch forward, no extra runtime needed):

```bash
git clone https://github.com/Phocinae/phocinae-server.git && cd phocinae-server
python -m venv .venv && . .venv/bin/activate
pip install fastapi uvicorn torch
PHOC_MODEL_DIR=/path/to/Phocinae-Largha-150M-v1 python -m phocinae.main   # http://127.0.0.1:8155
```

See [deployment.md](./deployment.md) for hardware tiers, guard and MCP setup, and [protocol.md](./protocol.md) for the request contract.

## 3. Is the server OpenAI-compatible?

**No — on purpose.** The model is not a chat model, so the API does not pretend to be one. It exposes `POST /v1/systemone` (plus `/permute`, `/batch`) on 127.0.0.1 only. Full contract: [protocol.md](./protocol.md).

## 4. What hardware do I need?

| tier | RAM / storage / GPU | expected |
|---|---|---|
| baseline (try it) | 4 GB RAM · 8 GB storage · no GPU | ~1.5–1.7 s per decision (CPU single-thread) |
| minimum (efficient) | 8 GB RAM · 8 cores · ≥4 GB VRAM (3060 → 30–60 ms; 4090 → 18.6 ms) | 18.6–60 ms GPU; 8–21 decisions/s on 8 CPU threads |
| recommended | 16 GB · 512 GB NVMe · 8 GB+ GPU | 18.6–25 ms while other apps run |

Weights are 288.6 MB (fp16 safetensors); inference peaks ~1.6 GB VRAM / ~1.8 GB RAM.
## 5. How fast is it — and why is CPU ~1.5 s?

- GPU fp16 single decision: **18.6 ms** p50 (release value).
- CPU single-thread: **1.51 s** p50 — end-to-end (tokenize + forward + answer assembly) on one fp32 thread. This is the honest CPU number, not the GPU number.
- CPU 8-thread batch: **8–21 decisions/s** (b=1 → 21.0, b=32 → 8.7).

## 6. What do the "flip" numbers mean?

We reorder a decision's options and check whether the answer changes ("flip", lower is better). CPU fp32, idle machine: reversed **0.0300** (flip150) / **0.0300** (flip400) · random-mean **0.0233** · any-of-3 **0.0433**. That is roughly one changed answer per ~33 reorders — a 0.7 pp gap vs Laya in-domain (3.7%), vs Jev ~9% and Laya out-of-domain 19.4%. GPU 0.027/0.028 and 1k-row 0.0187/0.0205/0.0431 are note-only values (different protocols).

## 7. How is the model calibrated?

The shipped column has **ECE 0.1313** (en). The calibration temperatures **0.7698 / 0.7879 / 0.7559** are stored in the model repo config and applied at inference by phocinae-server. A development recalibration reached 0.0106 — it is **not shipped** with the released weights.

## 8. Why didn't you pass the JevBench acceptance gate?

We didn't — and we publish it: **0.5108 (118/231)** vs the 58.4% acceptance gate. The number is as measured, we never trained on the eval rows, and we make no leaderboard claims from it. (tool_selection k≤10 is 12/12.)

## 9. Does it actually work in Chinese?

On the English test we measure **0.797**; on translated typed-decisions cases **0.789**. Reference points on the same typed protocol: Laya 0.766 · JEV 0.727 · meraGPT 0.768 (en test). Honest caveat: the zh rows are machine-translated English test cases — the model has **no native Chinese training rows**. Treat zh as cross-lingual transfer evidence.

## 10. Can I use it as a safety/security gate?

Not as the sole gate. Largha is a first-line decision aid: use it with escalation (the E1 τ=0.6 gate sends the 18% it is unsure about elsewhere) and a deterministic L0 rule layer such as [phocinae-guard](https://github.com/Phocinae/phocinae-guard) — never as the only control for destructive or safety-critical actions.


## 11. How much money does it save?

The τ=0.6 escalate gate raises combined accuracy 0.789 → **0.7948** (+0.006) while cutting LLM calls by **−82%** (100% → 18%). Worked example: ≈17.2M LLM tokens/month per 10k routed decisions ≈ **$492/yr saved** (Claude Sonnet 5 list prices, Oct 2026). Estimates only — see [cost-savings.md](./cost-savings.md).

## 12. What are the main limitations?

- Not for chat/generation, long-document reasoning, or world-knowledge QA.
- zh is translated-only; long inputs degrade (16k/32k probes: 0.453 / 0.387).
- JevBench gate not passed (Q8); order-robustness is good but not perfect (Q6).
- No demographic/fairness evaluation; English business-ops domain biases carry over.

Full list: [MODEL_CARD.md](../MODEL_CARD.md).

## 14. What license applies?

Weights: **Apache-2.0** (see LICENSE). Base encoder `jhu-clsp/mmBERT-small`: check its upstream license. Server/guard code: Apache-2.0.

## 15. How do I cite and reproduce?

```bibtex
@misc{phocinae-largha-150m-v1,
  title  = {Phocinae-Largha-150M-v1: a 150M-class decision model},
  author = {Phocinae},
  year   = {2026},
  note   = {https://huggingface.co/Phocinae/Phocinae-Largha-150M-v1}
}
```

Verify the weights (`sha256sum model.safetensors` → `db79d5ee2f16597f34e564f5a4363bddb5b5bbd9827c01819725dabcc7802697`), then follow [reproduce.md](./reproduce.md) for protocols, published values, and evidence paths. The eval harness is published in the main repo.
