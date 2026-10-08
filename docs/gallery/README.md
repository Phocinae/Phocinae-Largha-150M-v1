# Gallery — application scenarios

Animated demos of Phocinae-Largha-150M-v1 in real agent workflows. All 24 demos: 800×450, loop forever, first frame = conclusion card with key numbers, last frame = one-line takeaway. All in-frame numbers follow the frozen calibration table (`00_定案口径表_20261008.md`): 18.6 ms · 0.797/0.789 (typed en/zh) · 0.7948 · −82% LLM calls · 8–21 decisions/s · flip 0.0300 · JevBench 0.5108 (118/231).

| # | scenario | demo | key numbers |
|---|---|---|---|
| S01 | destructive command gate | [S01_rmrf_gate.gif](./S01_rmrf_gate.gif) | p(deny)=0.96 · 18.6 ms (synthesized mock; live capture pending P0) |
| S02 | curl-pipe-shell gate | [S02_curl_pipe_gate.gif](./S02_curl_pipe_gate.gif) | p(allow)=0.21 → DENY · 18.6 ms |
| S03 | batch command triage | [S03_chmod_batch.gif](./S03_chmod_batch.gif) | 8 commands: 6 allow / 1 ask / 1 deny |
| S04 | tri-state approval | [S04_tristate_gate.gif](./S04_tristate_gate.gif) | thresholds 0.30/0.65; git push 0.91 / sudo restart 0.44 / rm -rf /etc 0.05 |
| S05 | replay battery | [S05_replay_battery.gif](./S05_replay_battery.gif) | 17 commands (9 benign / 8 dangerous); 0 false allows · 2 false rejects (≤3 design value) |
| S06 | escalate savings | [S06_escalate_savings.gif](./S06_escalate_savings.gif) | acc 0.789→0.7948 · −82% LLM calls (E1, τ=0.6) |
| S07 | tool routing | [S07_tool_routing.gif](./S07_tool_routing.gif) | k≤10 · p(python)=0.87 · JevBench tool_selection 12/12 |
| S08 | Chinese zero-escalate | [S08_zh_zero_escalate.gif](./S08_zh_zero_escalate.gif) | Largha 0.83 vs Kimi K3 0.72 (E5-zh, 200 translated decisions) |
| S09 | context screening | [S09_context_screen.gif](./S09_context_screen.gif) | 30 chunks: keep 19 / drop 11 · CPU 8-thread batch 8–21 decisions/s |
| S10 | model routing | [S10_model_routing.gif](./S10_model_routing.gif) | simple → local 18.6 ms; complex → escalate (τ=0.6) |
| S11 | microbatch 60 fps | [S11_microbatch_60fps.gif](./S11_microbatch_60fps.gif) | 18.6 ms → micro-batch-4 amortized 6.2 ms · p(RIGHT)=0.92 |
| S12 | snake with a 144M brain | [S12_snake.gif](./S12_snake.gif) | 18.6 ms/step, 20×20 grid (synthesized game demo; live capture pending P3) |
| S13 | real-time event triage | [S13_event_triage.gif](./S13_event_triage.gif) | 30fps frame gate (33 ms/frame) · P(3)=0.81 red alert · 18.6 ms/event (synthesized) |
| S14 | document triage | [S14_doc_triage.gif](./S14_doc_triage.gif) | 8 files labeled locally (contract/invoice/notes/weekly/other) · p(contract)=0.88 · zero cloud tokens |
| S15 | expense pre-approval | [S15_expense_preapprove.gif](./S15_expense_preapprove.gif) | taxi ¥3,800 no receipt · p(approve)=0.07 → REJECT conf 0.91 · gray band 0.30–0.65 → human |
| S16 | skill routing | [S16_skill_routing.gif](./S16_skill_routing.gif) | one sentence → contract-parsing skill · p=0.94 · k≤10 menu, one forward pass |
| S17 | quality gate | [S17_quality_gate.gif](./S17_quality_gate.gif) | draft report p(rewrite)=0.61 → flagged back with notes · cheap first screen, not final review |
| S18 | invoice verification | [S18_invoice_verify.gif](./S18_invoice_verify.gif) | ¥12,600×13% = ¥1,638.79 tax (matches) · p(ok)=0.95 · invoice_processing training domain acc 0.866 |
| S19 | step verification | [S19_step_verify.gif](./S19_step_verify.gif) | expected 200 OK + access_token vs actual HTTP 500 · p(pass)=0.04 → FAIL, stop chain (mock; live pending P0) |
| S20 | output screening | [S20_output_screen.gif](./S20_output_screen.gif) | shipped-column ECE 0.1313 (disclosed) · p(usable)=0.35 block saves LLM tokens · first coarse screen only |
| S21 | content gate | [S21_content_gate.gif](./S21_content_gate.gif) | allow / review / block (0.30/0.65 dual thresholds) · gray band → human · local, no data trail |
| S22 | option-order invariance | [S22_flip_invariance.gif](./S22_flip_invariance.gif) | flip150 0.030 / flip400 0.030 (CPU fp32, frozen) — README hero |
| S23 | bilingual decision | [S23_bilingual.gif](./S23_bilingual.gif) | typed acc en 0.797 / zh 0.789 (n=2000 each) · same verdict side-by-side · zh = translated cases, no native zh training rows |
| S24 | quickstart in three lines | [S24_quickstart.gif](./S24_quickstart.gif) | pip install → phocinae serve → POST /v1/systemone · 144.3M (150M-class) · hardware tiers: 4 GB no-GPU 1.5–1.7 s / 3060-class 30–60 ms / 4090-class 18.6 ms (mock; asciinema capture pending P0) |

Honesty notes: S01/S12/S13–S21/S23/S24 are synthesized mock demos (live captures pending the corresponding project phases); S05's battery counts are the demo battery (the guard's shipped acceptance battery is 15 benign / 24 dangerous / 4 gray); thresholds shown in S04/S15/S21 are demo values — production gates use the guard's fitted thresholds (see [deployment.md](../deployment.md)). The gallery is regenerated from `make_gifs.py`, `make_gifs_batch2.py`, `make_gifs_batch3.py`, `make_gifs_batch4.py` — pure PIL, deterministic, reproducible.
