# Attributions

本包（`flipaug_recipe`）是 Phocinae-Largha-150M-v1 复现配套材料（训练侧选项序翻转增广）。

## 上游数据与决策协议

- **LocalLLaMA/typed-decisions** — 训练数据与决策协议上游；本包的行件格式、样例结构与
  flipaug 所增广的「state / criteria / options」协议均源自该数据集 train split。
  - 链接：https://huggingface.co/datasets/LocalLLaMA/typed-decisions
  - 许可：Apache-2.0
  - 复现口径：HF revision `f7a2487e`（主仓 reproduce.md「Data sources」节同口径）

## 训练入口涉及的上游模型

- **jhu-clsp/mmBERT-small** — 训练命令 `--encoder-dir` / `--tokenizer-dir` 指向的编码器基座
  （MIT 许可）。本包不包含其权重，仅在本包 README 的训练命令模板中引用。

## flipaug 算法出处

选项序增广算法与种子方案出自本项目（Phocinae contributors）训练侧构建器：

- `exp/pt2_v2_prep_20261006/build_flipaug_mix.py`
  （π = randperm(k, seed=1000003*42+i)）
- `exp/pt2_v2_prep_20261006/build_pt2v2_flipaug_mix.py`
  （π = randperm(k, seed=1000003*42+i*101+o)，o3/o5 臂）

本包 `flipaug.py` 为上述构建器的行件级等价实现（同公式；随机流为 Python 标准库 random，
见 README「已知差异与注意」）。

## 许可

- 本包代码与文档：Apache License 2.0（见本目录 LICENSE）。
- typed-decisions 数据集：Apache-2.0（上游署名）。
- mmBERT-small 模型：MIT（上游署名）。
- 本包不含任何第三方权重或数据文件，样例数据为本包自制的 3 行演示行件。
