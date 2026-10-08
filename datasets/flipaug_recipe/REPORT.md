# flipaug_recipe 交付报告

日期：2026-10-08。交付目录：`09_常态探索/release_prep_20261007/05_dataset_release/flipaug_recipe/`
（本包只写该目录，未改动任何其他文件；未做任何 push/上传/联网发布）。

## 1. 交付文件清单

| 文件 | 角色（四件套） | 来源 |
|---|---|---|
| `flipaug.py` | 脚本件 | 训练侧 token 层构建器 `exp/pt2_v2_prep_20261006/build_flipaug_mix.py`、`build_pt2v2_flipaug_mix.py`（o3/o5 臂）的行件级等价实现（同公式，纯标准库） |
| `train_seeds.json` | 种子件 | 链 v/w/x/y/z/z2/za/zar（`exp/cf_20261004/gpu_chain_20261006*.sh`）+ `*.pt.meta.json` 实测 argv |
| `README.md` | 文档 | 新写（中文） |
| `LICENSE` | 许可 | `02_hf_release/hf_repo/LICENSE` 逐字节复制（sha256 cfc7749b…，与源一致） |
| `ATTRIBUTIONS.md` | 署名 | 新写（上游 typed-decisions Apache-2.0、mmBERT-small MIT、算法出处） |
| `examples/sample_in.jsonl` | 样例 | 新写（3 行含 choice 题演示行件） |
| `examples/sample_out.jsonl` | 样例 | flipaug.py `--seed 42` 实跑输出（15 行） |
| `SHA256SUMS` | 校验 | 对上述全部文件生成（`sha256sum -c` 可验） |

## 2. 校验结果（全部实跑通过）

1. **py_compile**：`python3 -m py_compile flipaug.py` → 通过（系统 Python 3.14.7，零第三方依赖）。
2. **增广倍数**：`python3 flipaug.py examples/sample_in.jsonl examples/sample_out.jsonl --seed 42`
   → `IN rows=3 choice_rows=3 OUT rows=15 (x5 per choice row)`；README 默认用法
   （不传 --seed）输出与显式 `--seed 42` 逐字节一致。
3. **语义审计**（独立口径脚本，scratch）：每行 5 份副本；criteria 键序按 `_flipaug.perms`
   重排且选项文本随键走；probabilities 键序与 criteria 对齐、数值不变；label 键与文本语义
   不变；noul/score 题与 id/state/n_questions 等字段原样；5 份副本为独立随机置换
   （k=3 的题 5 抽得 3 种不同序——碰撞属训练侧同口径，o5 混件 audit 含 645 次 identity）。
4. **确定性**：同 seed 两次运行输出逐字节一致（cmp 通过）。
5. **README 一致性**：README 中两条命令与 `--help` 参数名逐字一致，样例预期输出与实际一致。
6. **sha256**：`SHA256SUMS` 生成后已 `sha256sum -c` 全过（见下）。

## 3. 与主仓四件套文档的衔接建议（不直接改主仓）

主仓（`/home/hermes/dev/phocinae-largha-150m/`；发布稿同 `02_hf_release/hf_repo/`）
现有四件套文档为 `docs/reproduce.md` + `docs/protocol.md` + MODEL_CARD + NOTICE。
建议补充的章节：

1. **reproduce.md「Data sources」节**：typed-decisions 行后补一句「flip-augmented
   reorderings 的训练侧脚本与种子见 flipaug_recipe 发布包（flipaug.py / train_seeds.json）」，
   把「train split（with flip-augmented reorderings）」落到可复现件。
2. **reproduce.md「Option-order flip」节**：在读数后加一行「flip 读数的训练侧来源 =
   选项序增广（flipaug）；发布模型训练数据含该增广（MODEL_CARD 已述），复现包见
   flipaug_recipe/README「与已发布 flip 翻转率读数的关系」」。可另注开发侧 o5 臂
   flip400 0.0133 仅为开发证据、非发布模型读数（防口径混淆）。
3. **reproduce.md「Status / known gaps」节**：harness 待发布段把 flipaug_recipe 列入
   已就绪项（脚本+种子+样例+校验齐备，可随 harness 一并公开）。
4. **MODEL_CARD「Fine-tune data」行**：可加 flipaug_recipe 的链接/路径引用。
5. **protocol.md**：无需改动（运行时协议与训练侧增广无关）；permute/perm-avg 端点
   （4 序平均）与训练侧 5 序增广是两件事，README 已避免混述，建议主仓保持现状。
6. **建议新增 docs/training/（或 release_notes 附页）**：收编本包 README 的「训练
   环境与入口」节（venv / run_gpu.sh / train_small.py 模板）——这是四件套「环境件」
   目前唯一缺口；注意该节涉及项目内部路径，公开发布前需脱敏（去掉 /home/hermes 绝对路径）。

## 4. 遗留事项 / 注意

- 本包 flipaug.py 与 token 层构建器的随机流不同源（random vs torch.randperm）——
  已在上游文件头与 README「已知差异与注意」明示；逐字节复现 .pt 混件仍需 token 层构建器。
- 训练链脚本（gpu_chain_20261006v…zar.sh）与 train_small.py 未入包（仅模板收录于
  train_seeds.json）——若四件套要求完整训练脚本，建议下轮发布把 token 层构建器 +
  链脚本脱敏后并入本包同目录。
