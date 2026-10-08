# ATTRIBUTIONS（上游署名）

本包（flip 五组复现配方，`05_dataset_release/flip_recipe/`）使用以下上游数据与脚本逻辑，署名如下。

## 1. typed-decisions（上游协议与评测数据）

- 名称：**typed-decisions**（Hugging Face 数据集）
- 组织：LocalLLaMA（Hugging Face org）
- 链接：https://huggingface.co/datasets/LocalLLaMA/typed-decisions
- 许可证：**Apache-2.0**
- 用途：本包 `flip_rows_subset.jsonl` 的 400 个翻转评测行件取自其 **test split**（本地镜像 `exp/typed_decisions_test.jsonl`，未作实质修改）。typed 决策协议（state 情景 + typed 问题 + criteria 选项字典）为该数据集定义，本包翻转护栏评测即在该协议的 choice 题选项顺序上做重排重判。
- 声明：本包仅以评测与复现目的分发这些行件；数据内容与标注归属原数据集作者（LocalLLaMA org）。

## 2. 评测脚本逻辑来源（本项目）

- `eval_flip.py` 的协议与指标逻辑逐位镜像：
  - `exp/eval_flip.py`（原序 / 全反序 / 随机排列三预测，`--rand-seed` 语义）；
  - `exp/cf_20261004/results_m_20261007/run_flip_m_20261007.py`（N-seed 随机排列扩展，产出发布定案读数）。
- 版权：Phocinae contributors，Apache-2.0（同本包 `LICENSE`）。

## 3. 关联署名（模型基座，与数据包无直接包含关系）

- **jhu-clsp/mmBERT-small**（Hugging Face 模型，MIT 许可证）：本发布模型（Phocinae-Largha-150M-v1）的编码器基座与初始权重来源。https://huggingface.co/jhu-clsp/mmBERT-small

## 4. 发布读数溯源

- 发布定案读数（rev 0.0300 / random-mean 0.0233 / any 0.0433）出处：
  - `exp/cf_20261004/results_m_20261007/NEXT_AFTER_IDLE_20261007.md` §③（2026-10-07 22:42 定案，CPU fp32 空载双次复现）；
  - `08_发布材料_20261007/00_定案口径表_20261008.md`（2026-10-08 发布口径）。
