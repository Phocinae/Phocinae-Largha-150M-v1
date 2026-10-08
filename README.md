# 斑海豹 Phocinae-Largha-150M-v1

> **小海豹，大决断。** Tiny model. Big decisions.
> **一斑见全豹，一点定全局。** Spotted seal. Spot-on calls.

144.3M 参数的双语决策引擎（zh/en）。结构化决策——状态、标准、选项进去，一次前向，裁决＋校准置信度出来。纯 CPU 可跑，本地开源使用，**不对外服务**。

| 指标 | 值 |
|---|---|
| typed-decisions en | 0.797（400 用例 / 2000 决策） |
| typed-decisions zh | 0.789（译件 400 案，零中文训练行） |
| 翻转率（越低越好） | rev 0.0300 / random-mean 0.0233 / any 0.0433 —— 选项怎么排，答案基本不变 |
| 校准（发货列 ECE） | 0.1313（如实披露） |
| 推理速度 | CPU 单线程 p50 1.51s / 决策（GPU fp16 18.6ms） |
| 体积 | JEV-27B 的 1/193 |
| JevBench public-231 | 0.5108（118/231）（门 58.4%，未过门，如实披露） |

**30 秒上手**
1. 模型卡（权重、指标、局限性）：https://huggingface.co/Phocinae/Phocinae-Largha-150M-v1
2. 本地推理服务（一行起）：https://github.com/Phocinae/phocinae-server
3. 复现：模型卡 Evidence 节＋`exp/` 评测脚本（见模型卡）

**诚实的海豹**：预注册门 G1–G4 全过；没过门的（JevBench 聚合、封存集待测）也写给你看。局限与证据路径见模型卡 Limitations/Evidence。

License: Apache-2.0（底座 mmBERT-small 上游条款请自行核对）。
