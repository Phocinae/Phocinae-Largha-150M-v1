# typed-decisions 测试行集（typed_test）

## 数据集描述

本包为 typed-decisions 评测协议的**测试行集（test split）**，用于决策模型的公开评测与复现。

- 规模：**400 用例 × 每用例 5 个决策问题 = 2000 决策**。
- 场景：4 个工作流（workflow），各 100 用例——
  `agent_trace_observability`（智能体轨迹观察）、`customer_service`（客服工单）、
  `invoice_processing`（发票处理）、`security_incidents`（安全事件）。
- 每用例给出：`state`（结构化场景状态）、`questions`（5 个决策问题：任务描述 + 题型 + 判据 + 候选答案）、`gold`（正确答案标签与标注分布）。
- 题型三类：`choice`（多选一，criteria 为「候选 → 描述」字典）、
  `noul`（是/否判断，候选 false / true）、
  `score`（等级评分，0-based，criteria 为等级描述列表）。

## 字段 schema（每行一个用例）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 用例唯一标识，形如 `<workflow>_<6 位序号>` |
| `workflow` | string | 场景工作流 |
| `split` | string | 恒为 `"test"` |
| `state` | object | 决策场景状态（上游为 JSON 字符串二次编码，本包已解析为对象，内容未改） |
| `questions` | object | 5 个决策问题，键为问题 id（qid） |
| `gold` | object | 每问题的正确答案 |
| `factors` | object | 上游附加因子 |
| `label_agreement` | object | 上游标注一致性信息 |
| `n_questions` | int | 恒为 5 |

`questions.<qid>` 子字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `instructions` | string | 问题文本 |
| `type` | string | `choice` / `noul` / `score` |
| `criteria` | object / array / null | choice、noul：候选 → 描述字典；score：等级描述列表（0-based）；无 criteria 的 noul 题（`duplicate`、`credential_compromise`）为 null |
| `options` | array[string] | 候选答案列表（本包规整新增）：choice/noul → criteria 键列表；score → `["0", …, "n-1"]`；无 criteria 的 noul → `["false", "true"]` |

`gold.<qid>` 子字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `label` | string | 正确候选（choice/noul）；score 为 0-based 等级字符串 |
| `type` | string | 题型 |
| `confidence` | number | 标注置信度 |
| `probabilities` | object | 标注软标签分布 |
| `score` | number | 仅 score 题：连续分数 |
| `noul` | number | 仅 noul 题：是/否概率 |
## 统计

- 400 用例 / 2000 决策（每用例恰 5 题；已逐行校验）。
- 题型分布：`choice` 600 / `noul` 600 / `score` 800。
- 每工作流 100 用例；`agent_trace_observability` 与 `customer_service`：choice 2 / noul 1 / score 2；`invoice_processing` 与 `security_incidents`：choice 1 / noul 2 / score 2。
- 200 道 noul 题（`duplicate` 100、`credential_compromise` 100）上游未给 criteria，选项按 gold 概率键规整为 `["false", "true"]`。
- gold 完整性：400 行 × 5 题 gold 全部非空；label 与 criteria/options 一致性 0 处异常；无重复 id。

## 来源

- 上游数据集：LocalLLaMA/typed-decisions（Hugging Face：https://huggingface.co/datasets/LocalLLaMA/typed-decisions），test split。
- 上游许可：Apache-2.0。

## revision 说明

- **v1.0（2026-10-08）**：初版发布。取自上游 test 集（400 用例），按评测协议做字段归一化（见「修改声明」）；行集内容与本地评测（`exp/eval_local.py` 协议）所用行件同源同内容。
- 行件 sha256：`03cdab9296345a93e20dc416755c84bfdc86e2f4ba8e6529e7f27ba30022d436`。

## 修改声明

**本行集由上游 test 集按评测协议归一化/字段规整而来**，具体改动仅限以下三项：

1. `state` / `questions` / `gold` / `factors` / `label_agreement` 由「JSON 字符串二次编码」解析为一级 JSON 对象（内容逐字保留）；
2. 每个问题新增 `options` 字段（候选答案列表，由 criteria / gold 概率键推导，规则见 schema）；
3. 无 criteria 的 noul 题其 `criteria` 键缺省（消费端按键访问时按「无 criteria」处理，等价 null）。

`id` / `workflow` / `split` / criteria 文本 / gold 标签与分布均未做任何改写。归一化脚本见本包 `normalize.py`（幂等，可作为行集自检器复现校验）。

## 许可证

本包以 **Apache-2.0** 发布，全文见 `LICENSE`。上游 LocalLLaMA/typed-decisions 亦为 Apache-2.0，其版权声明保留于 `ATTRIBUTIONS.md`。

## 引用方式

```bibtex
@misc{phocinae-typed-test-rows,
  title   = {typed-decisions test rows (normalized release)},
  author  = {Phocinae},
  year    = {2026},
  note    = {Normalized field-regularized release of the LocalLLaMA/typed-decisions
             test split (400 cases / 2000 decisions), Apache-2.0},
  url     = {https://github.com/Phocinae/Phocinae-Largha-150M-v1}
}

@misc{typed-decisions,
  title       = {typed-decisions},
  publisher   = {Hugging Face},
  url         = {https://huggingface.co/datasets/LocalLLaMA/typed-decisions},
  note        = {上游数据集；作者与年份以该数据集卡为准，许可 Apache-2.0}
}
```

## 与模型 0.797 评测的关系

- Phocinae-Largha-150M-v1 的对外主数 **typed-decisions en acc 0.797（400 用例，n=2000 决策）** 即在本行集上测得（定案口径表 2026-10-08）。
- 评测协议：对每用例的 `state` + `questions` 做单遍前向，每题取 argmax 决策——choice/noul 按候选概率 argmax 判标签，score 按等级概率 argmax 判 0-based 等级；正确性对照本行集 `gold.label`。与项目内 `exp/eval_local.py` 协议一致。
- 本行集与评测所用行件（`exp/typed_decisions_test.jsonl`）同源同内容；经 `normalize.py` 归一化后，评测器按 `questions` / `gold` 结构的读取方式不变，可直接复现。
- 附属指标口径（软准确率 / Brier / ECE / 翻转率 / 延迟）见模型卡与定案口径表，不在此数据卡展开。
