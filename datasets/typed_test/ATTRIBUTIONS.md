# ATTRIBUTIONS（上游归属声明）

## 上游数据集

- 名称：typed-decisions
- 发布方：LocalLLaMA（Hugging Face 数据集）
- 地址：https://huggingface.co/datasets/LocalLLaMA/typed-decisions
- 许可证：Apache-2.0
- 本包使用部分：test split 全部 400 用例（2000 决策）

## 版权声明保留

- 本包（`typed_test/`，Phocinae-Largha-150M-v1 发布包 05_dataset_release 子目录）
  由上游 LocalLLaMA/typed-decisions test 集按评测协议归一化/字段规整而来
  （详见 `README.md`「修改声明」：仅 JSON 结构归一化与 `options` 字段派生，
  criteria / gold / state 内容未做改写）。
- 依据上游 Apache-2.0 许可，本文件保留上游版权声明：**上游数据内容版权归
  LocalLLaMA/typed-decisions 原作者所有**；Apache-2.0 许可全文见本包 `LICENSE`。
- 本包新增文件（`normalize.py`、`README.md`、`PII_SCAN.md` 等）：
  © 2026 Phocinae，以 Apache-2.0 提供。
