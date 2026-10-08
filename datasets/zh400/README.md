# zh400 中文判定评测集（数据卡）

> 发布包版本：v1.0（2026-10-08 组装）｜数据文件：`zh400.jsonl`（400 行）｜许可证：Apache-2.0（上游衍生）
> 用途：Phocinae-Largha-150M-v1（斑海豹）发布包配套评测集；仅 test 切分，**不应用于训练**。

## 1. 数据集描述

zh400 是 **LocalLLaMA/typed-decisions 数据集的 typed_decisions_test 切分（400 用例）的简体中文翻译版**，
中文文本由 **DeepSeek API（deepseek-chat）机器翻译**生成（2026-09-27；翻译等级 **L3：API 机译，未经人工校订**）。

- 行数：400（test 切分全量）；用例 ID 与英文源一致（`<workflow>_<6 位序号>`）
- 工作流：4 个 × 100 用例——`agent_trace_observability` / `customer_service` / `invoice_processing` / `security_incidents`
- 判定决策：**2000**（choice 600 / noul 600 / score 800；每用例 5 题）
- 中文字段：`state`（状态描述）、`questions`（题目指令 + criteria/options 描述）；`gold` 与英文源**逐字节相同**（400/400 实测）
- 语种标注：`_lang: "zh-CN"`

## 2. 与 0.789 评测的关系

本集是发布口径中的中文评测集：**Phocinae-Largha-150M-v1 在本集上的中文判定准确率 = 0.789（400 用例 / 2000 决策）**。
该读数性质：模型训练数据不含中文，属英文训练模型的零样本中文迁移 + 机译输入下的判定精度。

## 3. 字段 Schema（每行一个 JSON 对象）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 用例 ID，与英文源一致 |
| `workflow` | string | 工作流名（4 值） |
| `split` | string | `"test"` |
| `state` | string(JSON) | 状态描述，中文翻译（内嵌标识符/专名按策略保留原文） |
| `questions` | string(JSON) | 判定题集合，中文翻译 |
| `gold` | string(JSON) | 判定标签与概率分布，与英文源逐字节相同 |
| `n_questions` | int | 判定题数（本集恒为 5） |
| `factors` | string(JSON) | 上游元数据，未翻译（与源一致） |
| `label_agreement` | string(JSON) | 上游标注一致度元数据，未翻译（与源一致） |
| `_lang` | string | `"zh-CN"` |
| `_trans` | object | 翻译元数据：`model`=deepseek-chat、`date`=2026-09-27、`src`=typed_decisions_test.jsonl、`src_sha256`、`mode`（whole 393 行 / whole+patch 7 行） |

`questions` 内部：`{题名: {type, criteria, instructions}}`；choice/noul 的 criteria 为 `{键: 中文描述}`（键不翻译，
与上游及多语惯例一致），score 的 criteria 为 4 档中文量表。`gold` 内部：`{题名: {label, probabilities, type, ...}}`；
choice/noul 各选项概率和与 1 的最大偏差 ≈1e-6（1e-9 容差下 455/2000 题有浮点尾差，英文源同数 455/455，属上游固有属性，非缺陷）。

## 4. 来源、生成方式与修改声明

- **上游**：LocalLLaMA/typed-decisions（Hugging Face；Apache-2.0），test 切分 400 用例；
  源文件 `typed_decisions_test.jsonl` sha256 = `e6b149efbae9d91b111f20d18fca3ed0e7df2043497f8364f03d9310e3f1c796`。
- **生成方式**：**AI / 机器翻译生成**——DeepSeek API `deepseek-chat`（2026-09-27），8 并发、内容哈希缓存、重试/退避；
  400/400 一次通过，0 失败；回译抽查 20 例（5/工作流）语义保真良好、数字零丢失。
- **翻译规则**：只翻文本字段；schema / 键 / qid / label 映射不动；程序标识符、状态码、型号、URL、金额、日期、
  协议缩写保留原文（7 条 `freight_terms` 首轮漏译已字段级补译，mode=whole+patch）。
- **修改声明**：本衍生集对上游**仅做文本字段翻译**；结构字段逐项保留、gold 逐字节未动；
  `factors` / `label_agreement` 元数据未翻译。

## 5. 许可证

Apache-2.0（上游 typed-decisions 为 Apache-2.0，本衍生集延续）。全文见 `LICENSE`；
上游署名与 DeepSeek 输出声明见 `ATTRIBUTIONS.md`；PII 扫描结果见 `PII_SCAN.md`。

## 6. 校验记录（2026-10-08 实跑）

- JSONL 可解析：400/400；行数 = 400；字段齐全（id/workflow/split/state/questions/gold/n_questions 等 11 字段 0 缺失）
- id 唯一 400/400；split 全为 test；题型计数 choice 600 / noul 600 / score 800（合计 2000 决策）
- gold 有效性：label ∈ criteria（键或 0–3 量表）400/400 用例全过；概率和与 1 的最大偏差 ≈1e-6（浮点存储尾差，与英文源一致）
- 乱码扫描：U+FFFD 替换符 0、latin-1 乱码 0、私用区 0、半个代理对 0
- PII 扫描：0 真实个人可识别信息（详见 `PII_SCAN.md`）

## 7. 已知局限（如实披露）

- **无原生中文训练行**：模型训练数据不含中文，本集仅为机译评测集——0.789 反映零样本中文迁移 + 机译输入，不等价于中文训练能力
- **机译噪声**：L3 级机译未经人工校订，个别句法生硬、术语口径可能与人工译不同
- **残留英文**：全部 400 用例均含少量英文长串（公司名/地名等专名、对话中引用的界面错误信息原文，如
  "transaction could not be processed"），属翻译策略保留、非乱码；security_incidents 工作流因含 IP/端口/服务名等标识符残留比例相对最高
- **仅 test 切分**：不得用于训练；评测口径与英文 typed-decisions 同协议（2000 决策）

## 校验

- `zh400.jsonl` sha256：`c5dece44434d302c4be337ce9fae57a3a9952c7833620f8e15364f0dacb12b20`
