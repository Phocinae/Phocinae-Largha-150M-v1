---
language:
- zh
- en
license: apache-2.0
pipeline_tag: text-classification
tags:
- decision-making
- typed-decisions
- text-classification
- small-model
- bilingual
- calibration
- option-order-invariance
- systemone
- zero-output-tokens
- on-premise
base_model: jhu-clsp/mmBERT-small
datasets:
- LocalLLaMA/typed-decisions
thumbnail: figures/C1_typed_acc_comparison.png
---

<p align="center">
  <img alt="License" src="https://img.shields.io/badge/License-Apache%202.0-blue?style=flat-square">
  <img alt="Params" src="https://img.shields.io/badge/Params-144.3M-orange?style=flat-square">
  <img alt="Typed ACC" src="https://img.shields.io/badge/Typed%20ACC-en%200.797%20%2F%20zh%200.789-brightgreen?style=flat-square">
  <img alt="Latency" src="https://img.shields.io/badge/Latency-18.6ms%20GPU%20fp16-9cf?style=flat-square">
</p>

<div align="center">
  <img src="figures/logo_phocinae.png" width="180" alt="斑海豹 Phocinae 标志">
  <h1>斑海豹 · Phocinae-Largha-150M-v1</h1>
  <p><strong>小海豹，大决断。</strong> / <em>Tiny model. Big decisions.</em></p>
  <p><em>一斑见全豹，一点定全局。</em> / <em>Spotted seal. Spot-on calls.</em></p>
</div>

斑海豹 **Largha**：**144.3M 参数（150M 级）中英双语决策模型**，用于结构化决策——一次前向、一张决策、全部本地运行。它不是聊天模型：输入一段 `state`（状态描述）加若干条类型化问题（`noul` 是非判定 · `choice` 单选 · `score` 2–10 打分），输出带置信度的标定答案，且对选项顺序重排鲁棒（「Shuffle the options. Same decision.」）。下载渠道：[魔搭](https://modelscope.cn/models/PerryLink/Phocinae-Largha-150M-v1) · [Hugging Face](https://huggingface.co/Phocinae/Phocinae-Largha-150M-v1) · [GitHub](https://github.com/Phocinae/Phocinae-Largha-150M-v1)。完整英文文档：[README](./README.md)。

## 一句话速览

| 项 | 值 |
|---|---|
| 参数量 | **144.3M**（mmBERT-small 底座：hidden 384 × 22 层 × 6 头，25.6 万词表；基础上下文 8192，默认头 512） |
| typed-decisions 英文（400 用例 / 2000 决策） | **0.797** — Laya 0.766 · JEV 0.727 · meraGPT 0.768（同一协议） |
| typed-decisions 中文（机器翻译用例，无中文训练行） | **0.789** |
| 选项顺序翻转鲁棒性（越低越好） | CPU fp32：flip150/400 **0.0300** · random-mean **0.0233** · any **0.0433** |
| 推理延迟 | GPU fp16 p50 **18.6 ms** · CPU 单线程 **1.51 s/case**（1 case = 1 状态 + 5 题一次前向） · CPU 8 线程批量 **8–21 决策/s** |
| 升级路由（E1 门，τ=0.6） | 保留集 acc **0.797→0.886**，LLM 调用 **−54.4%**（τ=0.5 档 −82.8%） |
| 校准 | 发货列 ECE **0.1313**；标定温度 0.7698/0.7879/0.7560 |

全部数字与证据：[BENCHMARKS.md](./BENCHMARKS.md)（对外数字唯一权威源）。

## 它解决什么问题：把智能体的重复决策成本打下来

**54.4% 的 LLM 调用节省、18.6 ms 一次决策。** 斑海豹把智能体会话中的重复决策——命令审批、工具选择、步骤检查、输出筛查——路由到本地单前向引擎，替代每次 500–4,000 token 的 API 调用。τ=0.6 置信门在**组合准确率不降反升**（0.797→0.886，保留子集）的同时砍掉一半以上 LLM 流量；确定性推理意味着决策可审计、可复现，数据不出本机。约合每 1 万次路由决策/月 **≈$326/年** LLM 费用节省（Claude Sonnet 5 公开价目，2026-10）。完整成本模型：[docs/cost-savings.md](./docs/cost-savings.md)。

**📽️ 27 个场景动画演示：[docs/gallery/](./docs/gallery/)**（中文版 [gallery/README_cn.md](./docs/gallery/README_cn.md)）——审批安全 · 路由省费 · 实时分级 · 办公文档 · 流程工程 · 对照与可靠性。

## 快速开始

官方运行时 [phocinae-server](https://github.com/Phocinae/phocinae-server)：本地 FastAPI 服务（仅监听 127.0.0.1），纯 PyTorch 前向加载权重，无需额外运行时。协议规范：[docs/protocol.md](./docs/protocol.md)。硬件档位：[docs/deployment.md](./docs/deployment.md)。

```bash
pip install phocinae-server
PHOC_MODEL_DIR=/path/to/Phocinae-Largha-150M-v1 python -m phocinae.main   # http://127.0.0.1:8155
```

一次决策（curl）：

```bash
curl -s http://127.0.0.1:8155/v1/systemone -H 'Content-Type: application/json' -d '{
  "model": "Phocinae-Largha-150M-v1",
  "state": "The agent restarted nginx after checking the logs and the health endpoint is green.",
  "questions": [
    {"id": "ok",   "type": "noul",   "threshold": 0.65},
    {"id": "act",  "type": "choice", "options": ["allow", "ask", "deny"]},
    {"id": "risk", "type": "score"}
  ]
}'
```

```json
{
  "model": "Phocinae-Largha-150M-v1",
  "answers": {"ok": true, "act": 0, "risk": 2},
  "usage": {"input_tokens": 24, "output_tokens": 0},
  "answer_confidence": {"ok": 0.91, "act": 0.72, "risk": 0.18},
  "routing": {"model": "Phocinae-Largha-150M-v1", "device": "cpu", "perm": "none", "backend": "phocinae-pure-torch"}
}
```

`answers` 取值：`noul` = 布尔 · `choice` = 0 起始选项下标 · `score` = 2–10 整数。输出 token 恒为 **0**（只出决策，不出文本）。

## 它适合 / 不适合

- **适合**：结构化决策——审批门、工具路由、升级判定、文档分级、步骤检查、输出筛查；任何需要「快、便宜、本地」决策层的场景。
- **不适合**：开放式聊天/生成、长文档推理、百科问答（MMLU 类探针欠佳，见模型卡）。它不是安全预言机：作为第一道门 + 升级兜底使用，切勿作为唯一防线。

## 诚实披露

- **JevBench public-231：0.5108（118/231），未达 58.4% 准入线——如实公开**；评测行从未进入训练集。
- 中文成绩基于机器翻译用例（无原生中文训练行）。
- 升级路由旧口径（−82% 配 τ=0.6）不成立：τ=0.6 实测 −54.4%，−82.8% 属于 τ=0.5 档。两档均真实可调，文档与官方数字并排、不一致处明说（[docs/cost-savings.md](./docs/cost-savings.md)）。
- 发货列 ECE **0.1313**；标定温度存于模型仓 `rl_agent_config.json`（0.7698/0.7879/0.7560），由 phocinae-server 推理时应用。

## 权重与许可

- `model.safetensors` sha256 `db79d5ee2f16597f34e564f5a4363bddb5b5bbd9827c01819725dabcc7802697`（fp16 存储，144.3M 参数）；底座 `jhu-clsp/mmBERT-small`，数据 `LocalLLaMA/typed-decisions`（训练集 + 翻转增广）。
- **Apache-2.0**（见 LICENSE）；底座编码器 mmBERT-small 为 MIT（见 NOTICE）。

## 更多文档

- [MODEL_CARD.md](./MODEL_CARD.md) — 详细模型卡 · [BENCHMARKS.md](./BENCHMARKS.md) — 基准 · [docs/deployment.md](./docs/deployment.md) — 部署 · [docs/protocol.md](./docs/protocol.md) — 协议 · [docs/reproduce.md](./docs/reproduce.md) — 复现 · [docs/cost-savings.md](./docs/cost-savings.md) — 省费测算 · [docs/faq.zh.md](./docs/faq.zh.md) — 常见问题 · [docs/technical-report.md](./docs/technical-report.md) — 技术报告

## 致谢

- [typed-decisions](https://huggingface.co/datasets/LocalLLaMA/typed-decisions)（Apache-2.0，LocalLLaMA HF 组织）— 协议与测试数据
- [mmBERT-small](https://huggingface.co/jhu-clsp/mmBERT-small)（JHU CLSP）— 底座编码器
- [JevBench](https://github.com/fstandhartinger/JevBench) — 用于诚实披露的保留评测
