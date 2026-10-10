# Gallery — 27 application scenarios (S01–S24 + G25–G27)

Animated demos of Phocinae-Largha-150M-v1 in typical agent workflows. All 27 demos: 800×450, loop forever, first frame = conclusion card with key numbers, last frame = one-line takeaway. Prefix legend: **S = application scenario, G = head-to-head & reliability**. All in-frame numbers match [BENCHMARKS.md](../../BENCHMARKS.md) and [MODEL_CARD.md](../../MODEL_CARD.md).

## Highlights

<details>
<summary>▶ Representative demos (6 selected, click to expand)</summary>

<div align="center">
  <img src="./S06_escalate_savings.gif" width="640"/>
  <p>−55.0% LLM calls (79.6% at τ=0.5), kept-subset accuracy 0.906→0.9936</p>
  <img src="./S01_rmrf_gate.gif" width="640"/>
  <p>Command gate: rm -rf blocked in 21.0 ms (RTX 5090)</p>
  <img src="./S07_tool_routing.gif" width="640"/>
  <p>Tool routing: 12/12 tool selection</p>
  <img src="./S24_quickstart.gif" width="640"/>
  <p>Three lines to run: pip install → serve → one decision</p>
  <img src="./S23_bilingual.gif" width="640"/>
  <p>Bilingual decisions: typed acc en 0.906 / zh 0.848</p>
  <img src="./S13_event_triage.gif" width="640"/>
  <p>Real-time event triage inside a 30 fps frame budget</p>
</div>

</details>

## Index

Click the ▶ toggle under each entry to expand its embedded demo GIF.

### Approval safety

**S01 · destructive command gate** — p(deny)=0.96 · 21.0 ms (RTX 5090)

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./S01_rmrf_gate.gif" alt="S01 — destructive command gate (demo GIF)" width="720"/>
</div>

</details>

**S02 · curl-pipe-shell gate** — p(allow)=0.21 → DENY · 21.0 ms (RTX 5090)

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./S02_curl_pipe_gate.gif" alt="S02 — curl-pipe-shell gate (demo GIF)" width="720"/>
</div>

</details>

**S03 · batch command triage** — 8 commands: 6 allow / 1 ask / 1 deny

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./S03_chmod_batch.gif" alt="S03 — batch command triage (demo GIF)" width="720"/>
</div>

</details>

**S04 · tri-state approval** — thresholds 0.30/0.65; git push 0.91 / sudo restart 0.44 / rm -rf /etc 0.05

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./S04_tristate_gate.gif" alt="S04 — tri-state approval (demo GIF)" width="720"/>
</div>

</details>

**S05 · replay battery** — 17 commands (9 benign / 8 dangerous); 0 false allows · 2 false rejects

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./S05_replay_battery.gif" alt="S05 — replay battery (demo GIF)" width="720"/>
</div>

</details>

### Routing & cost savings

**S06 · escalate savings** — acc 0.906→0.9936 (kept subset) · −55.0% LLM calls (79.6% at τ=0.5) (τ=0.6)

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./S06_escalate_savings.gif" alt="S06 — escalate savings (demo GIF)" width="720"/>
</div>

</details>

**S07 · tool routing** — p(python)=0.87 · JevBench tool_selection 12/12

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./S07_tool_routing.gif" alt="S07 — tool routing (demo GIF)" width="720"/>
</div>

</details>

**S08 · Chinese zero-escalate** — Largha 0.855 vs Kimi K3 0.72 (200 translated decisions)

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./S08_zh_zero_escalate.gif" alt="S08 — Chinese zero-escalate (demo GIF)" width="720"/>
</div>

</details>

**S09 · context screening** — 30 chunks: keep 19 / drop 11 · CPU 8-thread batch 8–20 decisions/s

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./S09_context_screen.gif" alt="S09 — context screening (demo GIF)" width="720"/>
</div>

</details>

**S10 · model routing** — simple → local 21.0 ms (RTX 5090); complex → escalate (τ=0.6)

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./S10_model_routing.gif" alt="S10 — model routing (demo GIF)" width="720"/>
</div>

</details>

### Real-time & fun

**S11 · microbatch 60 fps** — 21.0 ms (RTX 5090) → micro-batch-4 amortized 7.0 ms · p(RIGHT)=0.92

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./S11_microbatch_60fps.gif" alt="S11 — microbatch 60 fps (demo GIF)" width="720"/>
</div>

</details>

**S12 · snake with a 144.3M brain** — 21.0 ms (RTX 5090)/step, 20×20 grid

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./S12_snake.gif" alt="S12 — snake with a 144.3M brain (demo GIF)" width="720"/>
</div>

</details>

**S13 · real-time event triage** — 30 fps frame gate · P(3)=0.81 red alert · 21.0 ms (RTX 5090)/event

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./S13_event_triage.gif" alt="S13 — real-time event triage (demo GIF)" width="720"/>
</div>

</details>

### Office & documents

**S14 · document triage** — 8 files labeled locally · p(contract)=0.88 · zero cloud tokens

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./S14_doc_triage.gif" alt="S14 — document triage (demo GIF)" width="720"/>
</div>

</details>

**S15 · expense pre-approval** — taxi ¥3,800 no receipt · p(approve)=0.07 → REJECT · gray band → human

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./S15_expense_preapprove.gif" alt="S15 — expense pre-approval (demo GIF)" width="720"/>
</div>

</details>

**S16 · skill routing** — one sentence → contract-parsing skill · p=0.94

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./S16_skill_routing.gif" alt="S16 — skill routing (demo GIF)" width="720"/>
</div>

</details>

**S17 · quality gate** — draft report p(rewrite)=0.61 → flagged back · cheap first screen, not final review

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./S17_quality_gate.gif" alt="S17 — quality gate (demo GIF)" width="720"/>
</div>

</details>

**S18 · invoice verification** — ¥12,600×13% = ¥1,638.79 tax (matches) · p(ok)=0.95

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./S18_invoice_verify.gif" alt="S18 — invoice verification (demo GIF)" width="720"/>
</div>

</details>

### Workflow & engineering

**S19 · step verification** — expected 200 OK vs actual HTTP 500 · p(pass)=0.04 → FAIL, stop chain

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./S19_step_verify.gif" alt="S19 — step verification (demo GIF)" width="720"/>
</div>

</details>

**S20 · output screening** — p(usable)=0.35 block saves LLM tokens · first coarse screen only

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./S20_output_screen.gif" alt="S20 — output screening (demo GIF)" width="720"/>
</div>

</details>

**S21 · content gate** — allow / review / block (0.30/0.65 dual thresholds) · gray band → human

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./S21_content_gate.gif" alt="S21 — content gate (demo GIF)" width="720"/>
</div>

</details>

**S22 · option-order invariance** — flip rate 0.0217 — same verdict after option shuffle

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./S22_flip_invariance.gif" alt="S22 — option-order invariance (demo GIF)" width="720"/>
</div>

</details>

**S23 · bilingual decision** — typed acc en 0.906 / zh 0.848 · zh = translated cases

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./S23_bilingual.gif" alt="S23 — bilingual decision (demo GIF)" width="720"/>
</div>

</details>

**S24 · quickstart in three lines** — pip install → serve → POST · hardware tiers: 4 GB no-GPU 1.5–1.7 s / 3060-class 30–60 ms / 8 GB+ VRAM 21.0 ms (RTX 5090)

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./S24_quickstart.gif" alt="S24 — quickstart in three lines (demo GIF)" width="720"/>
</div>

</details>

### Head-to-head & reliability

**G25 · local vs API race** — 21.0 ms (RTX 5090) local vs 1.51 s API round-trip (our n=40; third-party Jev API single decision 238–301 ms)

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./G25_race_local_vs_api.gif" alt="G25 — local vs API race (demo GIF)" width="720"/>
</div>

</details>

**G26 · token savings** — 100 decisions: 54 local / 46 escalated · −55.0% LLM calls (79.6% at τ=0.5)

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./G26_token_savings.gif" alt="G26 — token savings (demo GIF)" width="720"/>
</div>

</details>

**G27 · fail-closed gate** — server unreachable → DENY by default, no silent pass

<details>
<summary>▶ Click to expand the demo GIF</summary>

<div align="center">
  <img src="./G27_failclosed.gif" alt="G27 — fail-closed gate (demo GIF)" width="720"/>
</div>

</details>


## Honest notes

- All demos are **synthesized** (fictional scenario data) for capability illustration — not real user data
- Thresholds shown in S04/S15/S21 are demo values; the shipped guard's thresholds are documented in [deployment.md](../deployment.md)
- In-frame numbers match [BENCHMARKS.md](../../BENCHMARKS.md); limitations (e.g. JevBench 0.5455, 58.4% gate not passed) are disclosed in [MODEL_CARD.md](../../MODEL_CARD.md)

Checksums: see [SHA256SUMS](./SHA256SUMS).
