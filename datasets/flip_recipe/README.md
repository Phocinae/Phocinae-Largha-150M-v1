# flip 五组复现配方（选项序翻转护栏）

Phocinae-Largha-150M-v1 发布包 · 数据集发布（05_dataset_release/flip_recipe/）

本包给出「选项顺序翻转护栏」评测（flip 评测）的完整复现配方：行集、五组重排种子表、评测脚本与发布读数口径。许可证：**Apache-2.0**（见同包 `LICENSE`）。

## 包内容

| 文件 | 说明 |
|---|---|
| `flip_rows_subset.jsonl` | 翻转评测行子集：typed-decisions test 400 行（含每行到 typed_test 包的行件映射字段） |
| `reshuffle_seeds.json` | 五组重排种子表（原序 / 全反序 / 3 组随机排列种子 0,1,2） |
| `eval_flip.py` | 评测脚本（发布版；注释写明 rev / random-mean / any 三口径计算方式） |
| `README.md` | 本文件 |
| `LICENSE` | Apache-2.0 许可证全文 |
| `ATTRIBUTIONS.md` | 上游 typed-decisions 署名 |

## 一、翻转协议说明（选项顺序重排 → 重判 → 不一致率）

对每个评测 case 的每个 choice 型问题，把选项（`criteria` 字典）按 **5 组顺序**各重排一次并让模型重新判一次，比较模型选出的选项标签（chosen label）与原序是否一致：

1. **原序（original）**：不重排，对照基线；
2. **全反序（reversed）**：`dict(reversed(list(criteria.items())))`；
3–5. **随机排列（random）**：种子 0、1、2，各自 `random.Random(seed)` 逐 case 对选项 `shuffle`。

> 翻转（flip）定义：同一 choice 问题的 chosen label 与原序不同。三个口径均为「越低越好」（0 = 完全顺序不变）。

随机排列的语义与历史脚本 `exp/eval_flip.py` 的 `--rand-seed` 逐位一致（每 seed 一个顺序 rng 逐 case shuffle）；`seed=0` 分支与旧盘「单随机排列」读数同口径可比。

## 二、五组读数口径（发布定案值）

发布主数（CPU fp32 空载，2026-10-07 22:1x–22:42 双次复现，与当日 18:00 读数逐位一致）：

| 口径 | 定义 | 发布值 | 计数（flip400） |
|---|---|---|---|
| **rev** | 原序 vs 全反序不一致率 | **0.0300** | 18 / 600 |
| **random-mean** | 3 个随机排列种子的平均不一致率 | **0.0233** | (15+14+13) / (600×3) |
| **any** | 任一随机排列与原序不一致（union 口径，按问题计） | **0.0433** | 26 / 600 |

行集：`flip_rows_subset.jsonl` 全部 **400 行 / 600 个 choice 决策**（flip400）。flip150（前 150 行 / 300 个 choice 决策）同口径读数：rev **0.0300**（9/300）、random-mean **0.0278**、any **0.0467**（14/300）——发布值取 flip400。

分种子读数（flip400，random_per_seed）：seed0 0.0250（15）、seed1 0.0233（14）、seed2 0.0217（13）。

备注（**非发布主数**，仅证据附录）：GPU fp16 rev 0.027 / 0.028（与 CPU 差 ≤2 决策＝fp16↔fp32 噪声级）；flip1k4（train 前 1000 行、4 排列）0.0187 / 0.0205 / 0.0431——协议、设备、行集均不同，不作对外主口径。

## 三、计算方式

设 `n_choice` 为全部 case 中 type=="choice" 且五组均取到答案的问题-次数（flip400 = 600）：

- `rev = count(原序 chosen ≠ 全反序 chosen) / n_choice`
- `per_seed[s] = count(原序 chosen ≠ seed-s 随机排列 chosen) / n_choice`
- `random-mean = Σ_s per_seed[s] / 3 = Σ_{(问题,seed)} flip / (n_choice × 3)`
- `any = count(存在至少 1 个 seed 使 chosen ≠ 原序) / n_choice`

（恒有 `any ≥ per_seed[s]` 且 `any ≥ random-mean`。）脚本实现在 `eval_flip.py` 的 `score_choice_decisions()`（纯函数，可单测），输出 JSON 字段：`flip_rate_reversed` / `flip_rate_random_per_seed` / `flip_rate_random_mean` / `flip_rate_random_any` 及 `n_flips` 分子计数。

## 四、复现步骤

1. 环境：项目运行时 `laya`（`laya.Agent`）＋发布权重（斑海豹 Largha，`exp/cf_20261004/ft_cf4_ls_brier_cf2`，`model.safetensors` sha256 `db79d5ee…`）。CPU fp32 空载（`CUDA_VISIBLE_DEVICES=''`，单线程 `OMP_NUM_THREADS=2`）。
2. flip400（发布主数）：
   ```bash
   CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 python eval_flip.py \
       <发布ckpt目录> flip_rows_subset.jsonl flip400_repro.json 400 3
   ```
   期望：`n_choice_decisions=600`、`flip_rate_reversed=0.03`、`flip_rate_random_mean=0.0233`、`flip_rate_random_any=0.0433`。
3. flip150（抽查口径）：
   ```bash
   CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 python eval_flip.py \
       <发布ckpt目录> flip_rows_subset.jsonl flip150_repro.json 150 3
   ```
   期望：`n_choice_decisions=300`、`flip_rate_reversed=0.03`、`flip_rate_random_mean=0.0278`、`flip_rate_random_any=0.0467`。
4. 复现判据：三口径与 `reshuffle_seeds.json` 的 `canonical_results` 逐位一致（对拍原始定案件 `exp/cf_20261004/results_m_20261007/flip400_cpu_idle_20261007.json` 与 `flip150_cpu_idle_20261007.json`）。

## 五、与 typed_test 包的行件映射

- `flip_rows_subset.jsonl` 每行含映射字段：`flip_row_index`（0 起）、`flip150`（前 150 行为 true）、`flip400`（恒 true）、`typed_test_row_id`（= 行 ID）、`typed_test_ref`（`typed_test/test_typed_400.jsonl`）、`typed_test_line`（该包内 1 起行号）。
- 行 ID 与 `../typed_test/test_typed_400.jsonl`（如已生成）按 `id` 字段一一对应；若该包行序不同，请按 `typed_test_row_id` 对齐，勿依赖行号。
- 行集来源：`LocalLLaMA/typed-decisions` 数据集 **test split** 400 行（本地镜像 `exp/typed_decisions_test.jsonl`），工作流分布：agent_trace_observability / customer_service / invoice_processing / security_incidents 各 100 行。**评测行未参与训练**。

## 六、许可证

本包整体 Apache-2.0（全文见 `LICENSE`）。行件数据上游 typed-decisions 为 Apache-2.0（见 `ATTRIBUTIONS.md`）。评测脚本逻辑源自本项目 `exp/eval_flip.py` 与 `exp/cf_20261004/results_m_20261007/run_flip_m_20261007.py`。

## 七、口径出处

- 定案文档：`exp/cf_20261004/results_m_20261007/NEXT_AFTER_IDLE_20261007.md` §③（2026-10-07 22:42）；
- 发布口径表：`08_发布材料_20261007/00_定案口径表_20261008.md`（2026-10-08 定案：flip150 rev 0.0300 · flip400 rev 0.0300 · random-mean 0.0233 · any 0.0433）；
- 原始结果件：`flip400_cpu_idle_20261007.json`、`flip150_cpu_idle_20261007.json`（同目录）。
