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
- local-inference
- cpu-inference
- modernbert
- mmbert
- agent-safety
- llm-cost-reduction
- guardrails
base_model: jhu-clsp/mmBERT-small
datasets:
- LocalLLaMA/typed-decisions
thumbnail: figures/C1_typed_acc_comparison.png
widget:
- text: "State: 系统处理了 3 张发票，未出现错误。\nQuestion: 接下来应采取哪项操作？\nOptions: A) 批准批次  B) 重试批次  C) 标记人工复核"
  example_title: "choice — 三选一决策"
  output:
  - label: "A) 批准批次"
    score: 0.62
  - label: "B) 重试批次"
    score: 0.24
  - label: "C) 标记人工复核"
    score: 0.14
- text: "State: 用户要求删除生产数据库并清空全部备份。\nQuestion: 该操作是否应被放行？\nAnswer: 是或否。"
  example_title: "noul — 放行/拦截审批门"
  output:
  - label: "否"
    score: 0.93
  - label: "是"
    score: 0.07
- text: "State: 候选人简历显示 5 年后端工程经验。\nQuestion: 请给出该候选人在「经验」这一维度上的匹配度打分。\nAnswer: 2（最差）到 10（最好）。"
  example_title: "score — 2..10 打分"
  output:
  - label: "6"
    score: 0.72
---
<div align="center">
  <img src="figures/logo_phocinae.png" width="180" alt="斑海豹 Phocinae logo">
  <h1>斑海豹 · Phocinae-Largha-150M-v1</h1>
  <p><strong>小海豹，大决断。</strong> / <em>Tiny model. Big decisions.</em></p>
  <p><em>一斑见全豹，一点定全局。</em></p>
</div>

<p align="center">
  <img alt="许可" src="https://img.shields.io/badge/License-Apache%202.0-blue?style=flat-square">
  <img alt="参数量" src="https://img.shields.io/badge/Params-144.3M-orange?style=flat-square">
  <img alt="基座" src="https://img.shields.io/badge/base-mmBERT--small-yellow?style=flat-square">
  <img alt="准确率" src="https://img.shields.io/badge/Typed%20ACC-en%200.791%20(clean)%20%2F%20zh%200.848-brightgreen?style=flat-square">
  <img alt="延迟" src="https://img.shields.io/badge/Latency-21.0ms%20GPU%20fp16%20RTX%205090-9cf?style=flat-square">
  <img alt="体积" src="https://img.shields.io/badge/Weights-288.6%20MB%20fp16-blueviolet?style=flat-square">
</p>

## 一句话说明：这是什么模型？

**Phocinae-Largha-150M-v1（斑海豹 Largha）是一个 144.3M 参数的双语「类型化决策模型」，不是聊天模型。** 输入一段状态文本 `state` 加一组带类型的提问（`noul` 是否 · `choice` 多选一 · `score` 2–10 打分），它在**一次前向传播**内返回带标定置信度的答案——**输出零个生成 token**，且答案对选项顺序不敏感。

它用来把 AI Agent 会话里重复出现的决策（命令审批、工具选择、步骤校验、输出筛查）留在本机执行：**GPU 上单个决策 21.0 ms**，CPU 单线程 1.64 秒/用例，权重仅 288.6 MB，无需 GPU 也能跑。不确定的部分再升级给大模型——τ=0.6 置信度门下，**45.0%** 的决策会升级，**外部 LLM 调用减少 55.0%**。

> **关于数字，请先读这一段。** 本卡此前把 **0.906** 当头条；那个数字是在模型**部分见过**的划分上测得的——v1.1 的训练混料里含有一个 500 条的纠错池，而该池是从测试行预测中挖出来的。基准维护者随后把我们重评为 **0.791**；自动榜上那条 0.906 被标为 `verified: false`。我们现在以 **0.791** 为准。完整分解见下方「诚实披露」：**被污染的 500 条干净口径只有 0.198；而未被触及的 1,500 条干净口径是 0.989。**

> **它是「决策层」，不是「对话层」。** 不要用聊天补全接口调用它；本模型所在生态刻意不实现 OpenAI 兼容接口。也不能用 `transformers` 的常规路径加载——官方运行时是 `phocinae-server`（纯 PyTorch 前向）。

### 它是什么 / 它不是什么

| | |
|---|---|
| **是** | 结构化决策 · 审批门 · 工具路由 · 置信度升级 · 文档分诊 · 步骤校验 · 输出筛查 |
| **不是** | 开放对话 / 文本生成 · 长文档推理 · 世界知识问答 · 唯一安全防线 |
| **不是** | OpenAI 兼容接口 / Ollama 模型 / 聊天补全 API |
| **不支持** | GGUF / llama.cpp / Ollama 量化路径（今天确实没有，见下） |

## 速览

| 项目 | 值 |
|---|---|
| 参数量 | **144.3M**（safetensors 实测 total 144,292,870，F16） |
| 结构 | mmBERT-small 基座：hidden 384 × 22 层 × 6 头，256k 词表，RoPE + 滑窗 + 全局注意力；编码器支持 **8192 位置**，但**出厂配置把整条序列截断到 `max_len: 512`**（状态 + 提问 + 选项合计），决策头注意力窗口 192 |
| 权重体积 | **288.6 MB**（fp16）· sha256 `b6472511eea30729985374f43968cf7f4b16bbe0827de6c6ca07cf92afbb778a`（已对实际文件校验） |
| 推理峰值 | ≈1.6 GB 显存 / ≈1.8 GB 内存 · **无 GPU 可跑** |
| 输出 | 零生成 token；`noul`=布尔 · `choice`=0 基下标 · `score`=2–10 整数，均附标定置信度 |
| 延迟 | GPU fp16 p50 **21.0 ms**/决策（RTX 5090，单卡单次，**未获独立复现**）· CPU 单线程 p50 **1.64 秒/用例** · CPU 8 线程批处理 **8–20 决策/秒** |
| 准确率（**策展口径**） | typed-decisions 英文 **0.791**（基准维护者清洗后复评）· 其中训练数据未触及的 1,500 条 **0.989** |
| 准确率（中文） | 中文 **0.848**——机翻用例上的 **in-mix（拟合）** 评测，不是零样本迁移 |
| 同协议对照 | Laya 0.766 · JEV-27B 0.727 · meraGPT 0.768（**口径不同，不可直接横比**，见下） |
| 选项顺序翻转率 | 越低越好：CPU fp32 flip150 **0.0200** · flip400 **0.0217** · random-mean **0.0144** · any **0.0283** |
| 升级门收益 | τ=0.6：外部 LLM 调用 **−55.0%**（τ=0.5 档 −79.6%），保留集准确率 **+0.0876** |
| 标定 | 出厂列 ECE **0.2519**(英) / **0.1941**(中)；可选 `calib/` 列 **0.0168** / **0.0152**，**代价是 Brier 0.0207 → 0.1218**；默认不启用 |
| 许可 | **Apache-2.0**（基座 `jhu-clsp/mmBERT-small` 为 MIT） |

### 口径警告

上表「同协议对照」那一行**不是同类测量**：我们的英文分是**在该协议上拟合出来的 specialist**，而 Laya / JEV / meraGPT 那几行不是同一类测量，不能当作同口径的横评。该数据集的 gold 是约 4B 级教师模型三次采样的均值，基准自己写明**教师自一致性上限 0.735**——这个分数衡量的是「与教师的一致程度」，不是「正确性」。

### 它在同类里的位置，说实话

150M 这一档的决策模型**已经很挤**，而我们**不是第一个，也不是最小的**：

| 模型 | 参数量 | 说明 |
|---|---|---|
| Julia-1 | **144,292,870**（与我们逐位相同，同一个 `mmBERT-small` 底座） | 比我们早 15 天（2026-09-23） |
| decima-small | **122M** | 比我们更小 |
| Crivo-150M | 149.6M | 自述「≤150M 参数第 7 个提交中最好的一个」 |
| Bekko System One | 17M / 68M / 400M | 在我们上下都铺了一整个家族 |
| **斑海豹 Largha** | **144.3M** | 本模型 |

**真正属于我们、且能被核对的东西：** 公布中文分数（在调研过的 ≤150M 决策模型里没找到第二个公布中文评测的）；把权重哈希、翻转率、标定列、τ 全扫表、成本模型，以及**一个我们没通过的基准**放在一起；以及在训练数据从未触及的 1,500 条上做到 **0.989**。如果你正在我们和 Julia-1 或 decima-small 之间选，也去读它们的卡。

## 三种题型

| 题型 | 语义 | 返回 |
|---|---|---|
| `noul` | 是 / 否 | 布尔值（可带 `threshold`） |
| `choice` | 多选一 | 0 基选项下标（最多 255 个选项） |
| `score` | 打分 | 整数 2–10 |

一次请求最多 **64** 题。**注意上下文预算**：编码器支持 8192 位置，但出厂 `max_len` 为 **512**，会截断整条序列（状态 + 提问 + 选项合计）；`head_max_len` 192 是决策头的注意力窗口。**按 512 而不是 8192 规划你的输入。**

## 快速开始

官方运行时是 **[phocinae-server](https://github.com/Phocinae/phocinae-server)**：本机 FastAPI 服务（仅监听 127.0.0.1），纯 PyTorch 前向直读本仓库权重，运行时零额外框架依赖。

```bash
# 1) 取权重（两个 CLI 都可用，hf 是较新的一个）
hf download Phocinae/Phocinae-Largha-150M-v1 --local-dir ./largha
#   旧版 huggingface_hub：huggingface-cli download Phocinae/Phocinae-Largha-150M-v1 --local-dir ./largha

# 2) 安装运行时并指向该目录
pip install phocinae-server
PHOC_MODEL_DIR=./largha python -m phocinae.main          # http://127.0.0.1:8155
```

一次决策：

```bash
curl -s http://127.0.0.1:8155/v1/systemone -H 'Content-Type: application/json' -d '{
  "model": "Phocinae-Largha-150M-v1",
  "state": "agent 刚刚执行了 rm -rf /var/log/app，退出码为 0。",
  "questions": [
    {"id": "ok",   "type": "noul",   "threshold": 0.65},
    {"id": "act",  "type": "choice", "options": ["allow", "ask", "deny"]},
    {"id": "risk", "type": "score"}
  ]
}'
```

返回：

```json
{
  "model": "Phocinae-Largha-150M-v1",
  "answers": {"ok": false, "act": 0, "risk": 3},
  "usage": {"input_tokens": 146, "output_tokens": 0},
  "answer_confidence": {"ok": 0.668, "act": 0.409, "risk": 0.1633},
  "routing": {"model": "Phocinae-Largha-150M-v1", "device": "cpu", "perm": "none", "backend": "phocinae-pure-torch"}
}
```

> **关于直接用 `transformers` 加载：** 本仓库根目录 `config.json` 的 `architectures` 是基座的 `ModernBertForMaskedLM`，直接用 `AutoModelForSequenceClassification` 得到的是**基座分类头**，不是训练好的 decision head，也不含标定温度。请使用 `phocinae-server`。

## 已知缺陷：默认渲染路径复现不出头条数字

已发布的 `phocinae-server` 用自己的 `_question_spec` 渲染类型化问题，**开箱只有 0.5140**（同样这 2000 条决策）。权重不是问题：在**调用方**覆写这一个方法（约 20 行，不改任何库文件）即达 **0.9055**，并与参考实现 `laya` 在 **2000/2000 条决策上完全一致**。此外，已发布的 `phocinae-server` **0.1.3 / 0.1.4 wheel 里仍是旧口径数字**（0.797 / 45.7% / 54.4%）——请视为过期。我们将发一个更正版本。

## 常见问题

### 什么时候该用它，什么时候该用大模型？

判断标准是"决策是否重复且有封闭选项集"。命令审批、工具选择（k≤10）、步骤校验、输出筛查属于此列——交给本机；开放式推理、多轮对话、长文档理解交给大模型。配合 τ=0.6 置信度门，只有 **45.0%** 的不确定决策会上行。

### 能省多少成本？

按每月 1 万次被路由决策、Claude Sonnet 5 列表价估算：全量走大模型约 **$9.1/月（约 $109/年）**，过门后约 **$4.1/月（约 $50/年）**——**一年大约省 59 美元**。如果你采用它的唯一理由是省 token 钱，这笔账抵不过接入时间，**请不要采用**。算得过来的理由是：确定性、数据不出本机、没有限流，以及在 1.5 秒往返放不进去的地方能做到 25 毫秒以内。

### 需要什么硬件？

无 GPU 可跑：4 GB 内存 + 8 GB 存储即可试。推荐 16 GB 内存 + 8 GB 以上显存，可达 21.0–25 ms/决策。**目前不支持 GGUF / llama.cpp / Ollama。**

### 中文效果怎么样？

把英文用例**机翻成中文**后测得 **0.848**（英文为策展口径 0.791）。训练混料含机译中文 ≈2,400 行与原生中文 ≈1,400 行，因此这是 **in-mix（拟合）** 评测。另外，本项目一次 182 场景审计发现：**改变提问语言**会让相当比例的判定结果发生变化——中文能用，但不是这个模型的强项。

### 能当安全门或唯一防线用吗？

**不能。** 它是**一线决策辅助**：需要与升级机制（τ=0.6 门会把 45.0% 不确定项交出去）和确定性规则层（如 [phocinae-guard](https://github.com/Phocinae/phocinae-guard) 的 L0 表）配合，绝不可作为破坏性/安全关键操作的唯一控制。

### 主要局限有哪些？

不擅长生成、长文档推理、世界知识问答；长输入退化（16k/32k 探针 0.453 / 0.387）；JevBench 公开集 0.5455（**该基准没有分数门**，准入是成本/延迟 + 污染门）；默认渲染路径有缺陷；**尚未做人口统计学/公平性评估**。

## 看它实际跑起来

<div align="center">
  <img src="figures/C1_typed_acc_comparison.png" width="600" alt="typed-decisions 准确率：Largha 英文 0.791（策展清洗分）/ 中文 0.848"/>
  <p><em>图 1 · typed-decisions：Largha 英文 <strong>0.791</strong>（策展清洗分）/ 中文 0.848（in-mix）—— Laya 0.766 · meraGPT 0.768 · JEV 0.727</em></p>
  <img src="figures/C7_routing_savings.png" width="600" alt="升级路由：保留集 +0.0876，外部 LLM 调用 −55.0%"/>
  <p><em>图 2 · 升级路由（τ=0.6）：保留集 +0.0876，外部 LLM 调用 −55.0%（τ=0.5 档 −79.6%）</em></p>
  <img src="figures/C6_bilingual.png" width="600" alt="双语：英文 0.791（策展）/ 中文 0.848（in-mix）"/>
  <p><em>图 3 · 双语：英文 0.791（策展清洗分）/ 中文 0.848（in-mix 拟合）</em></p>
  <img src="docs/gallery/G25_race_local_vs_api.gif" width="600" alt="同一决策：本地 21.0 ms vs API 往返约 1.5 秒"/>
  <p><em>图 4 · 同一决策：本地 21.0 ms（RTX 5090） vs API 往返约 1.5 秒（我方实测 n=40；第三方实测 Jev API 单决策 238–301 ms）</em></p>
</div>

**全部 27 个场景演示（中文版）→ [docs/gallery/README_cn.md](https://github.com/Phocinae/Phocinae-Largha-150M-v1/blob/main/docs/gallery/README_cn.md)**。演示为合成渲染，不是屏幕录制。

## 基准数字

| 基准 | 结果 | 说明 |
|---|---|---|
| typed-decisions 英文（400 用例 / 2000 决策） | **0.791** | **策展清洗分**；训练未触及的 1,500 条为 **0.989** |
| typed-decisions 中文（机翻用例） | **0.848** | in-mix（拟合）评测，非零样本迁移 |
| 选项顺序翻转率（越低越好） | **0.0200 / 0.0217 / 0.0144 / 0.0283** | flip150 / flip400（反向）· random-mean · any-of-3，CPU fp32 |
| 标定 | ECE **0.2519**(英) / **0.1941**(中) | 可选 `calib/` 列 → 0.0168 / 0.0152，代价是 Brier 0.0207 → 0.1218 |
| JevBench public-231 | **0.5455**（126/231） | 低于该榜多数系统；**该基准没有分数门**（准入为成本/延迟 + 污染门） |
| 升级路由（E1 门，τ=0.6） | **+0.0876** 保留集准确率，**−55.0%** 外部调用 | 45.0% 上行 |
| 长输入 | 16k / 32k 探针 **0.453 / 0.387** | 退化明显，非长文档模型 |

完整对照表与方法学：[BENCHMARKS.md](https://github.com/Phocinae/Phocinae-Largha-150M-v1/blob/main/BENCHMARKS.md)

## 诚实披露

- **0.906 → 0.791 的完整分解。** v1.1 训练混料含一个 500 条的纠错池，取自测试行预测，覆盖 2000 条决策中的 500 条、400 个用例中的 282 个。我们于 2026-10-10 自行披露，基准维护者随后重评：
  - 被污染的 **500 条**：干净口径 **0.198** vs 提交口径 0.724；
  - 未触及的 **1,500 条**：干净口径 **0.989** vs 提交口径 0.967；
  - 总体干净口径 **0.791**。策展表收录 0.791，自动榜那条 0.906 标为 `verified: false`。
  - 该数据集 gold 为约 4B 级教师三次采样均值，基准写明**教师自一致性上限 0.735**。
- **JevBench public-231：0.5455（126/231）。** 更正我们此前写错的框架：**JevBench 不存在「58.4% 验收门」**，其准入是成本/延迟门（≤2× Jev 成本与中位延迟；官方 cap USD 0.0646 / 1,000 决策、1.23 秒调整后中位延迟）与污染门。
- 中文 **0.848** 是机翻用例上的 **in-mix（拟合）** 结果，训练混料含机译中文 ≈2,400 行与原生中文 ≈1,400 行。**不要读成零样本跨语言迁移。**
- **21.0 ms 的 GPU 数字未获独立复现**（我们无 CUDA 主机），且为单卡单次测量。
- 翻转率按选项重排协议测量：CPU fp32 0.0200/0.0217（flip150/400 反向）· random-mean 0.0144 · any 0.0283。GPU fp16 0.0200/0.0217 与 1k 行 0.0181/0.0150/0.0331 为不同协议的备注值。
- 标定：出厂列英 **0.2519** / 中 **0.1941**；温度 0.8660205 / 0.8081192 / 0.6624661 存于 `rl_agent_config.json`，推理时应用。可选 `calib/` 列把 ECE 压到 0.0168 / 0.0152，但 Brier 从 0.0207 恶化到 0.1218——两个数字一起报。
- **尚未做任何人口统计学 / 公平性评估。**
- 本仓库的 `SHA256SUMS` 有多条无法通过校验（按更早文件集生成）；我们选择保留而不手工改它。上面的权重哈希是直接对文件校验得到的。

## 训练与许可

- 在 `jhu-clsp/mmBERT-small` 上以 `LocalLLaMA/typed-decisions` 训练（train split + 翻转增广重排）。配方 `rl_agent_config.json`：`head_layers 2` · `max_len 512` · `head_max_len 192` · loss `ce+brier` · optimizer `adafactor` · **`epochs 1`** · micro-batch 8 × grad-accum 4 · lr encoder 2e-05 / lr head 1e-04 · **`updates 300`** · **约 0.044 小时** · amp `fp16` · tag **`n13_r4`**。`checkpoint_meta.json`：`epoch 1 / total_epochs 1`，`avg_loss 1.3689859449863433`。
- **Apache-2.0**；基座编码器为 MIT。
- **本仓库（GitHub）只有文档、评测数据与图件**——权重与推理所需文件在模型仓（Hugging Face / 魔搭）：`model.safetensors` · `encoder/` · `tokenizer/` · `rl_agent_config.json` · `calib/`。本仓库单独 clone **不能**直接跑推理；请按上面的快速开始下载权重。

## 关于「海豹系列」

本组织预留了四个名字（`Caspica`、`Vitulina`、`Grypus`、`Barbatus`），它们的仓库现在写着 `Placeholder repository.`——**那是路线图，不是产品线**。这里**只有 Largha 一个有权重**。等第二个模型真的能跑起来，我们再叫它系列。

## 其他下载渠道与生态

- **Hugging Face**：https://github.com/Phocinae/Phocinae-Largha-150M-v1
- **GitHub**（完整文档与复现材料）：https://github.com/Phocinae/Phocinae-Largha-150M-v1
- **ModelScope 魔搭**（本页）：https://modelscope.cn/models/PerryLink/Phocinae-Largha-150M-v1
- 生态仓库：[phocinae-server](https://github.com/Phocinae/phocinae-server)（运行时）· [phocinae-guard](https://github.com/Phocinae/phocinae-guard)（命令审批门）· [phocinae-mcp](https://github.com/Phocinae/phocinae-mcp)（MCP 决策服务）

## 引用

```bibtex
@misc{phocinae2026largha,
  title   = {Phocinae-Largha-150M-v1: A 144M-parameter bilingual typed decision model},
  author  = {Phocinae Project},
  year    = {2026},
  url     = {https://github.com/Phocinae/Phocinae-Largha-150M-v1},
  license = {Apache-2.0}
}
```

## 修订记录

- **2026-10-15 — 0.791 更正。** 头条由 0.906 改为基准维护者的策展分 **0.791**；补入 500/1500 分解、0.735 教师上限、口径警告、同类位置对照表、成本算术与默认渲染缺陷；删除并不存在的「58.4% 验收门」；图件 C1/C4/C6/C7 重绘。
- **2026-10-09 — v1.1 刷新。** 权重升级（全部指标在新权重上重测；上一版 sha256 `db79d5ee2f16597f34e564f5a4363bddb5b5bbd9827c01819725dabcc7802697`）。图件/画廊重渲；新增 `calib/` 校准列。

## 致谢

- [typed-decisions](https://huggingface.co/datasets/LocalLLaMA/typed-decisions)（Apache-2.0，LocalLLaMA HF org）— 协议与测试数据
- [mmBERT-small](https://huggingface.co/jhu-clsp/mmBERT-small)（JHU CLSP）— 基座编码器
- [JevBench](https://github.com/fstandhartinger/JevBench) — 用于诚实披露的留出协议
