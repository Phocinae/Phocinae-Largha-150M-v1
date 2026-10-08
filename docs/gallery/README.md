# gif/ 全部 24 张场景 GIF（2026-10-08 补全）

合成引擎：`make_gifs.py`（S01/S06/S22）+ `make_gifs_batch2.py`（S02-S05、S07-S12）+ `make_gifs_batch3.py`（S13-S21、S23、S24）+ `make_gifs_batch4.py`（存量 11 张达标升级：S01/S02/S04-S11/S22）。纯 PIL 逐帧，零依赖可复现；800×450、循环播放、首帧=结论卡+数字钩子、尾帧=一句话结论。所有帧内数字遵循 `00_定案口径表_20261008.md`（旧口径命名与数字一律禁用；21.0ms（RTX 5090） / 0.906 / 0.848 / 0.9936（kept-subset）/ −55.0%（τ=0.6）/ −79.6%（τ=0.5）/ 144.3M（对外 150M 级）/ CPU 批 8–20 决策/s / flip 0.0217 为定案值）。

| 场景 | 文件 | 核心数字（口径） | 达标状态（2026-10-08 批次4 复核） |
|---|---|---|---|
| S01 | S01_rmrf_gate.gif | p(deny)=0.96 · 21.0ms（RTX 5090）（合成 mock，真录待 P0） | ✅ 9 帧 · 131KB · 800×450 · loop=0 |
| S02 | S02_curl_pipe_gate.gif | p(allow)=0.21 → DENY · 21.0ms（RTX 5090） | ✅ 9 帧 · 124KB · 800×450 · loop=0 |
| S03 | S03_chmod_batch.gif | 8 条 6 allow/1 ask/1 deny（按 03 清单「预期输出」；故事行「2 灰带 1 拦截」为叙述差异，以预期输出为准） | ✅ 10 帧 · 109KB · 800×450 · loop=0（批次 B 原有，复核通过） |
| S04 | S04_tristate_gate.gif | 阈值 0.30/0.65；git push 0.91 / sudo restart 0.44 / rm -rf /etc 0.05 | ✅ 8 帧 · 116KB · 800×450 · loop=0 |
| S05 | S05_replay_battery.gif | 17 条（9 良性/8 危险）；误放行 0 · 误拒 2（≤3 设计值） | ✅ 9 帧 · 133KB · 800×450 · loop=0 |
| S06 | S06_escalate_savings.gif | acc 0.906→0.9936 (kept subset) · 省费 55%（E1 实测冻结） | ✅ 12 帧 · 137KB · 800×450 · loop=0 |
| S07 | S07_tool_routing.gif | k≤10 · p(python)=0.87 · JevBench tool_selection 12/12 | ✅ 11 帧 · 126KB · 800×450 · loop=0 |
| S08 | S08_zh_zero_escalate.gif | 斑海豹 .855 vs Kimi K3 .72（E5-zh，同 200 翻译决策）· zh 零外呼 | ✅ 9 帧 · 119KB · 800×450 · loop=0 |
| S09 | S09_context_screen.gif | 30 chunk keep 19/drop 11 · CPU 8 线程常规批 8–20 决策/s（07_硬件需求实测 §1.4 实测口径；不用历史 95 口径） | ✅ 9 帧 · 130KB · 800×450 · loop=0 |
| S10 | S10_model_routing.gif | 简单→local 21.0ms（RTX 5090）；复杂→escalate（τ=0.6，E1） | ✅ 10 帧 · 120KB · 800×450 · loop=0 |
| S11 | S11_microbatch_60fps.gif | 21.0ms（RTX 5090）→微批4 摊销 7.0ms · 60fps 预算 16.7ms · p(RIGHT)=0.92 | ✅ 10 帧 · 124KB · 800×450 · loop=0 |
| S12 | S12_snake.gif | 144M 蛇脑 21.0ms（RTX 5090）/步 · 20×20 网格 · 吃 2 食物（合成游戏版，真录待 P3） | ✅ 20 帧 · 154KB · 800×450 · loop=0（批次 B 原有，复核通过） |
| S13 | S13_event_triage.gif | 实时监控事件分级：30fps 帧门（33ms/帧）内逐帧 score 0–3 · P(3)=0.81 红闪告警 · 21.0ms（RTX 5090）/事件（合成；低危事件批处理 CPU 批 8–20 决策/s 定案口径） | ✅ 10 帧 · 159KB · 800×450 · loop=0（批次 C） |
| S14 | S14_doc_triage.gif | 文档分类：8 文件本地贴标（合同/发票/会议纪要/周报/其他）· p(合同)=0.88 · 零上云零 token（合成） | ✅ 10 帧 · 130KB · 800×450 · loop=0（批次 C） |
| S15 | S15_expense_preapprove.gif | 审批预判：打车 ¥3,800 无发票 · p(approve)=0.07 → REJECT conf 0.91 · 灰带 0.30–0.65 才转人工 · 90% 单据免打扰 · 21.0ms（RTX 5090）/单（合成） | ✅ 9 帧 · 123KB · 800×450 · loop=0（批次 C） |
| S16 | S16_skill_routing.gif | 任务路由：一句话→合同解析技能 · p=0.94（其余 9 项低灰）· k≤10 菜单单次前向 · 21.0ms（RTX 5090） · schema 本地不传云端（合成） | ✅ 10 帧 · 118KB · 800×450 · loop=0（批次 C） |
| S17 | S17_quality_gate.gif | 质量 gate：周报草稿 p(需重写)=0.61 黄标打回＋批注 · 定位=廉价初筛、不做终审（口径如实）· 21.0ms（RTX 5090）/筛（合成） | ✅ 9 帧 · 117KB · 800×450 · loop=0（批次 C） |
| S18 | S18_invoice_verify.gif | 发票处理：¥12,600×13% 与税额 ¥1,638.79 一致（四舍五入到分）· p(一致)=0.95 绿勾 · invoice_processing 训练域 typed 判定（合成演示） · 21.0ms（RTX 5090）/张、微批4 摊销 7.0ms（合成） | ✅ 9 帧 · 127KB · 800×450 · loop=0（批次 C） |
| S19 | S19_step_verify.gif | 步骤校验：期望 200 OK+access_token vs 实际 HTTP 500 · p(pass)=0.04 → ✗ FAIL 链停＋重试建议 · 防级联错误 · 21.0ms（RTX 5090）/步（合成 mock，真调待 P0） | ✅ 9 帧 · 112KB · 800×450 · loop=0（批次 C） |
| S20 | S20_output_screen.gif | 输出初筛：shipped 列 ECE 0.2519（口径如实） · p(可用)=0.35 拦截、省主模型 token · 定位=第一道粗筛、选择力弱于大模型（口径如实）（合成） | ✅ 10 帧 · 129KB · 800×450 · loop=0（批次 C） |
| S21 | S21_content_gate.gif | 合规检查：放行/复核/拦截三级（0.30/0.65 双阈值）· 灰带转人工 · 本地跑不留数据痕迹 · 不当唯一守门员（合成） | ✅ 10 帧 · 111KB · 800×450 · loop=0（批次 C） |
| S22 | S22_flip_invariance.gif | flip150 0.0200 / flip400 0.0217（CPU fp32 空载定案口径）· README 头图 | ✅ 9 帧 · 118KB · 800×450 · loop=0 |
| S23 | S23_bilingual.gif | 双语决策：typed acc en 0.906 / zh 0.848（n=2000 各）· 并排 en 0.83 / zh 0.78 同判定（示范例；全量 2000 决策同判定率 89.8%） · zh 零外呼 · E1 τ=0.6 保留集 acc 0.9936 · −55% LLM 调用（τ=0.5 档 79.6%）（45.0% escalate）· zh 行为机译用例、训练混料含中文行（口径如实）（合成） | ✅ 8 帧 · 106KB · 800×450 · loop=0（批次 C） |
| S24 | S24_quickstart.gif | 三行跑起来：pip install → phocinae serve → POST /v1/systemone · 结构化决策 JSON · 144.3M 参数（对外 150M 级）· 21.0ms（RTX 5090） GPU fp16 p50 · 硬件三档（4GB 无卡 1.5–1.7s / 3060 档 30–60ms / RTX 5090 实测档 21.0ms）（合成 mock 占位，asciinema 真录待 P0） | ✅ 9 帧 · 135KB · 800×450 · loop=0（批次 C） |

验收（2026-10-08，批次4 后 PIL 全量复核）：**24/24 全部通过**——帧数 8–20（≥6）、尺寸 800×450、体积 106–159KB（>100KB 且 <5MB）、loop=0 循环。其中批次 4（`make_gifs_batch4.py`）升级存量 11 张：S01/S02/S08（3 帧→9 帧）、S10（4 帧→10 帧）按各自主题补足内容帧；S04（5→8）、S05（5→9）、S06（10→12）、S07（6→11）、S09（7→9）、S11（6→10）、S22（5→9）逐张加帧加内容；帧内数字全部对齐 `00_定案口径表_20261008.md`（S06 删除「$326/11.4M tokens」未重算省费金额，改用 −55.0% 相对口径（τ=0.6）；S22 换用定案 flip 0.0217 口径）。批次 A/B/C 其余 13 张原样保留、复核通过（见 统一修复_gif存量达标_20261008.md）。

SHA256SUMS 随文件更新（同目录，24 张全量重算）。
