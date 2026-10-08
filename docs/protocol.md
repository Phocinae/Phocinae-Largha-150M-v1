# `/v1/systemone` — decision protocol

The official runtime contract, implemented by [phocinae-server](https://github.com/Phocinae/phocinae-server). The server is deliberately minimal: it exposes one decision endpoint family and **does not implement any chat/completions-style compatibility layer** (by design — this model is not a chat model and the API does not pretend to be one).

## Endpoints

| method | path | description |
|---|---|---|
| GET | `/` | service info |
| GET | `/health` | liveness + model/device info (no auth) |
| GET | `/v1/models` | model directory (name, context, answer formats, extensions) |
| POST | `/v1/systemone` | single decision request |
| POST | `/v1/systemone/permute` | same, but choice questions are averaged over 4 option orders |
| POST | `/v1/systemone/batch` | batch of ≤64 decision requests |

## Request

```json
{
  "model": "Phocinae-Largha-150M-v1",
  "state": "The agent restarted nginx after checking the logs and the health endpoint is green.",
  "questions": [
    {"id": "ok",   "type": "noul",   "threshold": 0.65},
    {"id": "act",  "type": "choice", "options": ["allow", "ask", "deny"]},
    {"id": "risk", "type": "score"}
  ]
}
```

| field | constraints |
|---|---|
| `model` | must be exactly `"Phocinae-Largha-150M-v1"` (case-sensitive) — otherwise **422** |
| `state` | string, the context to decide on |
| `questions` | list, **1–64** items — otherwise **422** |
| `questions[].id` | non-empty, unique within the request — otherwise **422** |
| `questions[].type` | `noul` · `choice` · `score` (unknown → **422**) |
| `questions[].options` | required for `choice` (non-empty, ≤255) — otherwise **422**; **forbidden** on `score` (**422**) |
| `questions[].threshold` | `noul` only, within [0, 1] — otherwise **422** |

## Response

```json
{
  "model": "Phocinae-Largha-150M-v1",
  "answers": {"ok": true, "act": 0, "risk": 2},
  "usage": {"input_tokens": 24, "output_tokens": 0},
  "answer_confidence": {"ok": 0.91, "act": 0.72, "risk": 0.18},
  "action": {"act": {"act_probability": 0.72}},
  "option_scores": {},
  "routing": {
    "model": "Phocinae-Largha-150M-v1",
    "device": "cpu",
    "perm": "none",
    "backend": "phocinae-pure-torch"
  }
}
```

| field | shape |
|---|---|
| `answers` | dict {qid: value}; `noul` → bool · `choice` → 0-based option index (int) · `score` → int 2–10 |
| `usage` | `input_tokens` / `output_tokens` (int) |
| `answer_confidence` | dict {qid: float}, temperature-calibrated top probability |
| `action` | dict {qid: {"act_probability": float}} |
| `option_scores` | calibrated per-option probability vectors (choice: request order; noul: [p(false), p(true)]; score: levels 2–10); averaged over the 4 permutations when `perm=avg-k4` |
| `routing` | `device` (`cpu`/`cuda`), `perm` (`none` / `avg-k4`), `backend` |

Extension keys (`answer_confidence`, `action`, `option_scores`, `routing`) can be disabled with `PHOC_EXTENSIONS=0`.

Batch: `POST /v1/systemone/batch` accepts either a JSON array of requests or `{"requests": [...]}`, ≤64 items (empty or >64 → **422**), and returns a list of responses in order.

## Errors

| code | when |
|---|---|
| **422** | unknown model name; unknown question type; >64 questions; empty/duplicate question id; `choice` without/empty/>255 options; `score` carrying options; `noul` threshold outside [0,1]; empty/oversized batch |
| **413** | request body > 2 MiB (`PHOC_MAX_BODY`); body `{"error": {"code": 413, "message": "..."}}` |
| **401** | `PHOC_BEARER_TOKEN` set and `Authorization: Bearer <token>` missing or wrong |

## Permutation averaging

`/v1/systemone/permute` (or `PHOC_PERM_AVG=1`) averages every choice question over 4 option orderings to suppress order flips. Costs 4× the forward passes; use it when order-invariance matters more than latency.

## Determinism

Same request, same device, same batch shape → bit-identical answers. fp16 vs fp32, or different batch shapes, may differ in the last digit.
