# figures/ 数据源与口径（2026-10-07 定案）

所有数字只从以下证据读取；脚本 make_charts.py 内置数值与本文档一致（2026-10-08 批次 A 复核）。

| 图 | 数据 | 证据路径 |
|---|---|---|
| C1 typed acc | 斑海豹 en 0.906 / zh 0.848；Laya 0.766；meraGPT 0.768；JEV 0.727 | exp/zerogpu_calib_20261007/REPORT.md（typed_en/zh CPU JSON 逐位一致）；竞品公开值 01_研究资料/…/04_竞品全景矩阵 |
| C2 延迟 | GPU 21.0（RTX 5090）/ 25.6 / 5983 ms；CPU/API 1636 / 1510 / 5709.8 / 57481.7 ms | exp/latency_bench_20261007/REPORT.md §3；CPU 口径 1.64s 按 refresh 定案（空载复测 p50 1635.79ms） |
| C3 翻转率 | rev 0.0200（flip150 6/300）/ 0.0217（flip400 13/600）/ rand 3-seed mean 0.0144 / any-of-3 0.0283；阈值线 0.024 | flip400_cpu_idle_20261007.json（CPU fp32 空载复测）；flip1k4 0.0187/0.0205/0.0431 与 GPU fp16 idle 0.0200/0.0217 仅备注 |
| C4 JevBench | overall 0.5455（126/231）；tier easy 0.9167 (44/48) / original 0.5000 (36/72) / hard 0.4144 (46/111) | exp/jevbench_20260927/results/results_ft_n13_r4_native.json |
| C4b 家族分 | tool_selection 1.0 · intent .75 · extraction .708 · fact .667 绿；routing .417 · long_policy .316 · adversarial .333 · trap .375 · adequacy .083 灰 | jevbench231_familymacro_cpu_20261007.json per_family |
| C5 校准 | 发货口径：en raw 0.2519 / zh raw 0.1941；温度真值 rl_agent_config.json | exp/zerogpu_calib_20261007/REPORT.md §A1（raw 口径）0,0.54,0.52)） |
| C6 双语 | en 0.906 / zh 0.848 | 同 C1 |
| C7 路由省费 | acc 0.906→0.9936 (kept subset)；费用 100%→45.0%（省 55%） | 08_全流程研究与决策记录/10_应用场景研究/组合路由实验报告_20261004.md §1（E1 τ=0.6）＋04_省费评估 §3 |
| C8 参数量 vs 延迟 | 144.3M/21.0ms（RTX 5090）；Laya 421M/25.6ms；clef 9B/5983ms | latency_bench REPORT §3＋竞品矩阵 |
| C9 中文域外锚 | 斑海豹 .855 vs Kimi K3 .72（同 200 翻译决策） | 组合路由实验报告 §5（E5-zh）；诚实脚注：英译中翻译件口径 |

flip 发布口径：flip150 0.0200 / flip400 0.0217（CPU fp32 空载复现值，refresh_v1_20261009 定案）；flip1k4 rev 0.019 为参考口径。

SHA256SUMS 随图更新（同目录）。
