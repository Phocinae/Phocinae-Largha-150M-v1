# flipaug_recipe —— 选项序翻转增广训练复现包

Phocinae-Largha-150M-v1 复现四件套（数据 / 种子 / 环境 / 脚本）的**训练侧增广件**：
发布模型训练数据含「flip-augmented option reorderings」（主仓 MODEL_CARD「Fine-tune data」行），
本包把这一训练侧环节做成可独立复现的最小发布单元。

## 包内文件

| 文件 | 说明 |
|---|---|
| `flipaug.py` | 行件级选项序翻转增广脚本（零第三方依赖，纯标准库） |
| `train_seeds.json` | 训练种子表：增广 base seed、n_orders、训练运行 seed 清单与命令模板 |
| `README.md` | 本文件 |
| `LICENSE` | Apache License 2.0 全文 |
| `ATTRIBUTIONS.md` | 上游 typed-decisions / mmBERT-small 署名 |
| `examples/sample_in.jsonl` | 3 行演示行件（含 choice 题） |
| `examples/sample_out.jsonl` | `--seed 42` 的确定性输出（15 行，可自行复算比对） |

## flipaug 原理

**翻转护栏是什么。** 主仓发布表里的 flip150 / flip400 读数，测的是「把一道 choice 题的
选项顺序反转/重排后，模型的答案是否改变」（flip = 答案变了）。翻转率越低，模型对选项
呈现顺序越不敏感，决策越接近「看内容、不看顺序」。

**flipaug 做什么。** 对每个含 choice 题的用例（行件），产出 `n_orders`（默认 **5**）份
副本，每份副本按一个**确定性随机置换** π 重排该题选项的呈现顺序，正确答案（label 指向
的选项键）与概率分布随选项走、语义不变。把同一问题按 5 种选项序喂给训练，就是在数据层
直接教模型「答案与选项呈现顺序无关」——这就是发布模型 flip 读数的训练侧来源。

**为什么是 5 序。** 训练侧实证结论（本项目 exp/ 链 za/zar，2026-10-06）：单一乱序 ×
多 epoch 只是重复同一顺序（链 y 3ep 后 flip 仍破门）；改成「每题多种不同乱序 ×1ep」
（o3=3 序 / o5=5 序）才真正教会顺序不变性。o5 臂（seed42）开发侧 flip400 降到
0.0133（发布权重为 0.0300），是开发侧 flip 读数最低的一臂。默认 5 序即对齐 o5 臂。

**确定性。** π = randperm(k, seed = 1000003·seed + i·101 + o + q)（i=行序号，o=副本
序号，q=题内序号，k=选项数，seed=42）。同 seed、同输入 → 输出逐字节一致，可复现、
可审计；每份副本携带 `_flipaug` 元数据字段记录置换轨迹。

## 用法

```bash
# 基本用法（默认 --seed 42，--n-orders 5）
python3 flipaug.py in.jsonl out.jsonl

# 显式指定 seed 与增广份数（训练侧 o3/o5 臂分别对应 3/5）
python3 flipaug.py in.jsonl out.jsonl --seed 42 --n-orders 5
```

自带样例验证（预期：3 行 → 15 行，`x5 per choice row`）：

```bash
python3 flipaug.py examples/sample_in.jsonl /tmp/out.jsonl --seed 42
# 输出：IN rows=3 choice_rows=3 OUT rows=15 (x5 per choice row) seed=42
cmp /tmp/out.jsonl examples/sample_out.jsonl && echo 与随包样例输出逐字节一致
```

脚本自检：`python3 -m py_compile flipaug.py`（零第三方依赖，系统 python3 即可）。

**输入行件格式**（typed-decisions 行，一行一个 JSON 对象；`questions`/`gold` 为
JSON **字符串**字段）：

```json
{"id": "tr_..._000000", "workflow": "...", "split": "train",
 "state": "{\"task\": \"...\"}",
 "questions": "{\"action\": {\"criteria\": {\"allow\": \"...\", \"deny\": \"...\", ...}}}",
 "gold": "{\"action\": {\"type\": \"choice\", \"label\": \"allow\",
             \"probabilities\": {\"allow\": 0.6, \"deny\": 0.4}, ...}, ...}",
 "n_questions": 5}
```

要点：

- choice 题的 `criteria` 字典**键序 = 选项呈现顺序**，`gold.probabilities` 键序与之对齐；
- 仅 `gold.type == "choice"` 的题参与增广；noul/score 题与其余字段原样透传；
- 含 ≥1 个 choice 题的行 → 输出 `n_orders` 份副本；无 choice 题的行 → 原样 1 份
  （与训练侧 token 层构建器口径一致）；
- `n_orders` 份为**独立随机置换**（允许个别相同，k 小时碰撞概率高；见 flipaug.py 头注）；
- 输出不含原序行；每份副本新增 `_flipaug` 元数据（order / row_idx / seed / perms）。

## 与已发布 flip 翻转率读数的关系

- **对外主数（发布权重 斑海豹 Largha，CPU fp32 双复现）**：flip150 = **0.0300**、
  flip400 = **0.0300**、random-mean = 0.0233、any-of-3 = 0.0433（主仓 reproduce.md
  「Option-order flip」节，2026-10-07 复现）。这些读数**就是** flipaug 想压制的量。
- **本包 = 主数的训练侧来源**：发布模型训练数据含选项序增广重排（MODEL_CARD），
  本包给出该环节的可复现脚本与种子。
- **开发侧对照（不对外，作复现背景）**：flipaug 各臂读数见本项目内部 verdict 件
  （如 `exp/cf_20261004/ft_pt2_flipaug_o5_s42_flip400_en.json` = 0.0133，
  `..._flip_en.json` = 0.0067，同为开发侧读数，不对外）；o5 臂未成为发布权重（2026-10-06 定案 o5 弃用、
  10-07 发布权重定案），这些数字只证明「flipaug 方向有效」，**不得**对外宣称为
  发布模型读数。
- 结论口径：发布模型的 flip 读数 = 训练含 flipaug 增广后的护栏结果；用本包重建
  flipaug 训练集并复训，是第三方独立核验该环节的路径。

## 训练种子（详见 train_seeds.json）

- **增广 base seed**：42（公式 π = randperm(k, seed=1000003·42 + i·101 + o)，token 层
  构建器同公式；行件级脚本每题再加题内序号偏移）。
- **训练运行 seed**：7 / 42 / 123。所有 flipaug 臂（链 v/w/x/y/z/z2/za/zar）训练超参
  一致，唯一变量 = choice 选项序增强；seed42 为主臂，seed7/123 为 zar 链的 seed 稳健
  性复测（s7/s123 后缀臂）。
- **n_orders**：o3 = 3 序（13,188 件）、o5 = 5 序（18,376 件）；默认 5。

## 训练环境与入口（四件套 · 环境件）

flipaug 训练臂在本项目内的执行形态（供内部复现参考；发布侧以主仓为准）：

- 环境：项目 venv（torch cu128、sm_120 构建）；入口
  `bash run_gpu.sh <script.py> [args…]`（宿主 venv 包装 + GPU 节流值守 + flock 串行）。
- 命令模板（train_seeds.json 亦收录）：

```bash
bash run_gpu.sh exp/train_small.py \
  --encoder-dir <mmBERT-small> --tokenizer-dir <mmBERT-small> \
  --items <mix.pt> --init-from <ft_cf4_ls_brier_cf2> --out <ft_dir> \
  --epochs 1 --micro-batch 8 --grad-accum 4 --loss ce+brier --label-smooth 0.15 \
  --brier-weights 0.5:0.5:0.3 --optimizer adafactor --seed 42 --max-len 512 --perm-aug 0
```

- `--perm-aug 0`：训练时选项乱序**关闭**——flipaug 是数据层预注入，不是训练期随机增广
  （训练期 perm-aug 已证维度错配无效，见 PREREG_FROZEN_FLIPAUG_20261006）。
- 行件 → token 层 `.pt` 混件用 token 层构建器（`build_flipaug_mix.py` /
  `build_pt2v2_flipaug_mix.py`，见 ATTRIBUTIONS.md）；本包 flipaug.py 是行件级的
  等价实现，产出直接可入同一行件管线。

## 已知差异与注意

1. **随机流不同源**：flipaug.py 用 Python 标准库 `random`（Fisher–Yates）；token 层
   构建器用 `torch.randperm`。置换**公式**一致，**序列**不逐位一致。逐字节复现已发布
   `.pt` 混件（.meta.json 内 sha256）必须用 token 层构建器 + torch；本脚本面向自行重建
   flipaug 训练集（同 seed 下自身完全可复现）。
2. `_flipaug` 为新增元数据字段；下游管线若不识别可忽略，不影响其余字段。
3. 输出不含原序行件；需要「原序 + 5 序」混合集请自行合并原文件与输出。
4. 无 choice 题的行只输出 1 份——增广倍数对纯 noul/score 行不适用。

## 许可证

- 本包代码与文档：**Apache License 2.0**（见 LICENSE 全文）。
- 上游数据/模型署名与许可：见 ATTRIBUTIONS.md（typed-decisions Apache-2.0、
  mmBERT-small MIT）。
