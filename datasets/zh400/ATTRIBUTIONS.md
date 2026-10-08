# 署名与来源声明（ATTRIBUTIONS）

## 1. 上游数据集

- **名称**：LocalLLaMA/typed-decisions（Hugging Face：`LocalLLaMA/typed-decisions`）
- **切分**：typed_decisions_test（test，400 用例，2000 判定决策）
- **许可证**：Apache-2.0
- **源文件**：`typed_decisions_test.jsonl`
- **源文件 sha256**：`e6b149efbae9d91b111f20d18fca3ed0e7df2043497f8364f03d9310e3f1c796`
- 本衍生集保留上游全部 `id` / 结构与 `gold` / `factors` / `label_agreement` 元数据原样（gold 逐字节一致）

## 2. DeepSeek 输出标注声明

- 本数据集 `state` / `questions` 中的中文文本由 **DeepSeek API（模型 `deepseek-chat`）** 于 **2026-09-27** 机器翻译生成。
- 性质：**AI 生成内容（机器翻译，L3 级）**，未经人工校订。
- 声明：翻译文本不主张额外版权；DeepSeek 输出不追加任何使用限制；
  本衍生数据集整体按上游 Apache-2.0 分发（见 `LICENSE`）。

## 3. 本衍生集

- **名称**：zh400 中文判定评测集
- **组装方**：Phocinae-Largha-150M-v1 发布包（`release_prep_20261007/05_dataset_release/zh400/`）
- **许可证**：Apache-2.0（上游衍生）
- **文件**：`zh400.jsonl`（数据，sha256 见 README 末节「校验」：c5dece44434d302c4be337ce9fae57a3a9952c7833620f8e15364f0dacb12b20）、
  `README.md`、`LICENSE`、`ATTRIBUTIONS.md`、`PII_SCAN.md`
