<p align="center">
  <a href="https://github.com/Phocinae/Phocinae-Largha-150M-v1/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/badge/License-Apache%202.0-blue?style=flat-square"></a>
  <a href="https://huggingface.co/Phocinae/Phocinae-Largha-150M-v1"><img alt="Params" src="https://img.shields.io/badge/Params-144.3M-orange?style=flat-square"></a>
  <a href="https://github.com/Phocinae/Phocinae-Largha-150M-v1/blob/main/BENCHMARKS.md"><img alt="Typed ACC" src="https://img.shields.io/badge/Typed%20ACC-en%200.906-brightgreen?style=flat-square"></a>
  <a href="https://github.com/Phocinae/Phocinae-Largha-150M-v1/blob/main/BENCHMARKS.md"><img alt="Latency" src="https://img.shields.io/badge/Latency-21.0ms%20fp16%20RTX%205090-9cf?style=flat-square"></a>
  <a href="https://phocinae.github.io/Phocinae-Largha-150M-v1/"><img alt="Site" src="https://img.shields.io/badge/Site-live-brightgreen?style=flat-square"></a>
</p>

<div align="center">
  <img src="figures/logo_phocinae.png" width="180" alt="斑海豹 Phocinae 标志">
  <h1>斑海豹 · Phocinae-Largha-150M-v1</h1>
  <p><strong>小海豹，大决断。</strong> / <em>Tiny model. Big decisions.</em></p>
</div>

斑海豹 **Largha**：**144.3M 参数（150M 级）中英双语决策模型**，用于结构化决策——一次前向、一张决策、全部本地运行。它不是聊天模型：输入一段 `state`（状态描述）加若干条类型化问题（`noul` 是非判定 · `choice` 单选 · `score` 2–10 打分），输出带置信度的标定答案，且对选项顺序重排鲁棒（「Shuffle the options. Same decision.」）。下载渠道：[魔搭](https://modelscope.cn/models/PerryLink/Phocinae-Largha-150M-v1) · [Hugging Face](https://huggingface.co/Phocinae/Phocinae-Largha-150M-v1) · [GitHub](https://github.com/Phocinae/Phocinae-Largha-150M-v1)。完整英文文档：[README](./README.md)。

**基于 [mmBERT-small](https://huggingface.co/jhu-clsp/mmBERT-small) 构建**（JHU CLSP，MIT）——完整血统与许可说明见「权重与许可」。

## 一句话速览

| 项 | 值 |
|---|---|
| 参数量 | **144.3M**（mmBERT-small 底座：hidden 384 × 22 层 × 6 头，25.6 万词表；基础上下文 8192；决策序列 ≤512 token，决策头注意力窗口 192） |
| typed-decisions 英文（400 用例 / 2000 决策） | **0.906**（specialist：本数据集 train 分割微调；高于教师自一致性参考 0.735——卡面提示显著高于该值需警惕标签特异性过拟合）— Laya 0.766（我方实测·原生接口）· JEV-27B 0.727（零样本 generalist）· meraGPT 0.768（零样本 generalist） |
| typed-decisions 中文（机器翻译用例；训练混料含机译中文 ≈2,400 行＋原生中文 ≈1,400 行） | **0.848** |
| 选项顺序翻转鲁棒性（越低越好） | CPU fp32：flip150 **0.0200** / flip400 **0.0217** · random-mean **0.0144** · any **0.0283** |
| 推理延迟 | GPU fp16 p50 **21.0 ms**（RTX 5090）· CPU 单线程 **1.64 s/case**（1 case = 1 状态 + 5 题一次前向） · CPU 8 线程批量 **8–20 决策/s** |
| 升级路由（E1 门，τ=0.6） | 保留集 acc **0.906→0.9936**，LLM 调用 **−55.0%**（τ=0.5 档 −79.6%） |
| 校准 | 发货列 ECE **0.2519**（随包校准列 0.0168）；标定温度 0.8660205/0.8081192/0.6624661 |

全部数字与证据：[BENCHMARKS.md](./BENCHMARKS.md)（对外数字唯一权威源）。

## 它解决什么问题：把智能体的重复决策成本打下来

**55.0% 的 LLM 调用节省、21.0 ms（RTX 5090）一次决策。** 斑海豹把智能体会话中的重复决策——命令审批、工具选择、步骤检查、输出筛查——路由到本地单前向引擎，替代每次 500–4,000 token 的 API 调用。τ=0.6 置信门在**保留子集准确率升至 0.9936**（全量含本地判定 0.8135，如实披露）的同时砍掉一半以上 LLM 流量；确定性推理意味着决策可审计、可复现，数据不出本机。省费按 τ=0.6 −55.0% LLM 调用口径。完整成本模型：[docs/cost-savings.md](./docs/cost-savings.md)。

**📽️ 27 个场景动画演示：[docs/gallery/](./docs/gallery/)**（中文版 [gallery/README_cn.md](./docs/gallery/README_cn.md)）——审批安全 · 路由省费 · 实时分级 · 办公文档 · 流程工程 · 对照与可靠性。

## 快速开始

> `phocinae-server` 提供的是**运行时**，不含权重——请先按第 1 步取权重。

官方运行时 [phocinae-server](https://github.com/Phocinae/phocinae-server)：本地 FastAPI 服务（仅监听 127.0.0.1），纯 PyTorch 前向加载权重，无需额外运行时。协议规范：[docs/protocol.md](./docs/protocol.md)。硬件档位：[docs/deployment.md](./docs/deployment.md)。

```bash
# 1) 取权重（两个 CLI 都可用，hf 是较新的一个）
hf download Phocinae/Phocinae-Largha-150M-v1 --local-dir ./largha
#   旧版 huggingface_hub：
#   huggingface-cli download Phocinae/Phocinae-Largha-150M-v1 --local-dir ./largha

# 2) 安装运行时并指向该目录
pip install phocinae-server
PHOC_MODEL_DIR=./largha python -m phocinae.main   # http://127.0.0.1:8155
```

上面下载得到的目录，正是 `PHOC_MODEL_DIR` 需要的布局（`model.safetensors`、`encoder/`、`tokenizer/`、`rl_agent_config.json`）。

Python 用法（与服务端同一个引擎）：

```python
from phocinae.engine import Engine

eng = Engine("./largha", device="cpu")   # device="auto" 时优先用 CUDA
answers, confidence, action, usage = eng.run(
    "The agent restarted nginx after checking the logs and the health endpoint is green.",
    [{"id": "ok",   "type": "noul"},
     {"id": "act",  "type": "choice", "options": ["allow", "ask", "deny"]},
     {"id": "risk", "type": "score"}],
)
# answers    -> {'ok': False, 'act': 0, 'risk': 3}
# confidence -> {'ok': 0.668, 'act': 0.409, 'risk': 0.1633}
# usage      -> {'input_tokens': 146, 'output_tokens': 0}
# 传 with_scores=True 会多返回第 5 个值（逐选项分数）
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
  "answers": {"ok": false, "act": 0, "risk": 3},
  "usage": {"input_tokens": 146, "output_tokens": 0},
  "answer_confidence": {"ok": 0.668, "act": 0.409, "risk": 0.1633},
  "action": {"act": {"act_probability": 0.1581}},
  "routing": {"model": "Phocinae-Largha-150M-v1", "device": "cpu", "perm": "none", "backend": "phocinae-pure-torch"}
}
```

> **工具路由的已知限制。** `Router.route_tool()` 会混淆语义相近的工具名。可复现用例：状态 *"The user wants to find the latest news about the product launch."* 配六个工具 `web_search / read_file / run_command / list_files / fetch_url / ask_user`，返回 **`fetch_url`** 而非 `web_search`，置信度 ≈0.33。低置信度的工具选择应按「待升级」处理，而非直接执行。

`answers` 取值：`noul` = 布尔 · `choice` = 0 起始选项下标 · `score` = 2–10 整数。输出 token 恒为 **0**（只出决策，不出文本）。错误码：**422**（未知模型/类型、>64 题、choice 缺 options、score 带 options、threshold 越界）· **413**（>2 MiB）· **401**（bearer token）。扩展键 `answer_confidence` / `action` / `routing` 可用 `PHOC_EXTENSIONS=0` 关闭。

## 它适合 / 不适合

- **适合**：结构化决策——审批门、工具路由、升级判定、文档分级、步骤检查、输出筛查；任何需要「快、便宜、本地」决策层的场景。
- **不适合**：开放式聊天/生成、长文档推理、百科问答（MMLU 类探针欠佳，见模型卡）。它不是安全预言机：作为第一道门 + 升级兜底使用，切勿作为唯一防线。

## 诚实披露

- **JevBench public-231：0.5455（126/231），未达 58.4% 准入线——如实公开**；评测行从未进入训练集。
- 中文成绩基于机器翻译用例；训练混料含机译中文 ≈2,400 行＋原生中文 ≈1,400 行——zh 属「含中文训练材料的机译评测」（fitted），非零中文训练迁移。
- 升级路由旧口径（−79.6% 配 τ=0.6）不成立：τ=0.6 实测 −55.0%，−79.6% 属于 τ=0.5 档。两档均真实可调，文档与官方数字并排、不一致处明说（[docs/cost-savings.md](./docs/cost-savings.md)）。
- 发货列 ECE **0.2519**（随包校准列 0.0168）；标定温度存于模型仓 `rl_agent_config.json`（0.8660205/0.8081192/0.6624661），由 phocinae-server 推理时应用。

## 权重与许可

- `model.safetensors` sha256 `b6472511eea30729985374f43968cf7f4b16bbe0827de6c6ca07cf92afbb778a`（fp16 存储，144.3M 参数）；底座 `jhu-clsp/mmBERT-small`，数据 `LocalLLaMA/typed-decisions`（训练集 + 翻转增广）。
- **Apache-2.0**（见 LICENSE）；底座编码器 mmBERT-small 为 MIT（见 NOTICE）。

## 更多文档

- [MODEL_CARD.md](./MODEL_CARD.md) — 详细模型卡 · [BENCHMARKS.md](./BENCHMARKS.md) — 基准 · [docs/deployment.md](./docs/deployment.md) — 部署 · [docs/protocol.md](./docs/protocol.md) — 协议 · [docs/reproduce.md](./docs/reproduce.md) — 复现 · [docs/cost-savings.md](./docs/cost-savings.md) — 省费测算 · [docs/faq.zh.md](./docs/faq.zh.md) — 常见问题 · [docs/technical-report.md](./docs/technical-report.md) — 技术报告 · [calib/](./calib/) — 随包校准列

## 版本与机器可读源

- **本版本**：`v1.1`——模型仓上的固定 tag（`v1.0.0` 为上一版），便于可复现引用。
  用 `git ls-remote --tags https://huggingface.co/Phocinae/Phocinae-Largha-150M-v1` 解析其提交。
  （**刻意不在此文件写死提交散列**：任何散列都会在下一次提交后过期。）
- **机器可读事实**（与本卡数字一致，供 AI 与检索系统使用）：[llms.txt](./llms.txt)
- **引用元数据**：[CITATION.cff](./CITATION.cff)
- **官网**（镜像本卡，含结构化数据）：https://phocinae.github.io/Phocinae-Largha-150M-v1/

## 致谢

- [typed-decisions](https://huggingface.co/datasets/LocalLLaMA/typed-decisions)（Apache-2.0，LocalLLaMA HF 组织）— 协议与测试数据
- [mmBERT-small](https://huggingface.co/jhu-clsp/mmBERT-small)（JHU CLSP）— 底座编码器
- [JevBench](https://github.com/fstandhartinger/JevBench) — 用于诚实披露的保留评测

## 修订记录

- **2026-10-09 — v1.1 刷新。** 权重升级（本卡全部指标已在新权重上重测；上一版 sha256 `db79d5ee2f16597f34e564f5a4363bddb5b5bbd9827c01819725dabcc7802697`）。图件/画廊已重渲；新增随包校准列 [`calib/`](./calib/)。
- **2026-10-09 — 文档。** 快速开始扩写（权重下载、Python/HTTP 示例、工具路由限制说明）；补回官网与机器可读源指引入口。
- **2026-10-10 — 卡片元数据。** 移除机器可读的 base_model 字段；血统（mmBERT-small，MIT）继续以正文完整披露（见「权重与许可」）。
