#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""flipaug.py —— 选项序翻转增广（行件级；typed-decisions jsonl 行格式）

训练侧 flipaug 的行件级等价实现：把「每个用例产出 n_orders（默认 5）份选项序
随机增广副本」做成独立、可复现的命令行工具，供复现四件套（数据/种子/环境/脚本）
中的训练侧增广环节使用。

与训练侧 token 层构建器的关系：
  本脚本镜像 exp/pt2_v2_prep_20261006/build_flipaug_mix.py 与
  build_pt2v2_flipaug_mix.py（o3/o5 臂）的算法与种子公式，但操作对象是
  typed-decisions 行件（jsonl 行），只用 Python 标准库（无 torch/tokenizer 依赖）。
  置换公式一致（见下「种子方案」）；随机流实现不同——本脚本用标准库 random
  （Fisher–Yates），token 层构建器用 torch.randperm，两者置换序列不逐位一致。
  若要逐字节复现已发布的 .pt 训练混件（meta.json 内记录 sha256），请用 token 层
  构建器 + torch；本脚本面向「用上游 typed-decisions 行件自行重建 flipaug 训练集」。

原理（为什么做这个）：
  发布模型的翻转护栏读数（flip150 / flip400）测的是「选项序反转后答案是否翻转」，
  即选项呈现顺序敏感性。把同一问题按多种选项序喂给训练，是在数据层直接教模型
  「答案与选项呈现顺序无关」——这就是发布模型 flip 读数的训练侧来源
  （主仓 MODEL_CARD：train split + flip-augmented option reorderings）。

输入行件格式（每行一个 JSON 对象；键与 typed-decisions 行一致）：
  {
    "id": "tr_..._000000",
    "workflow": "agent_trace_observability",
    "split": "train",
    "state": "{\"task\": \"...\"}",      # JSON 字符串，原样透传
    "questions": "{\"action\": {\"criteria\": {\"allow\": \"...\", \"deny\": \"...\", ...}}}",
                                         # JSON 字符串；choice 题的 criteria 字典
                                         # 键序 = 选项呈现顺序（训练按此序编码选项）
    "gold": "{\"action\": {\"type\": \"choice\", \"label\": \"allow\",
              \"probabilities\": {\"allow\": 0.6, \"deny\": 0.4}, ...}, ...}",
                                         # JSON 字符串；probabilities 键序与
                                         # criteria 对齐；type ∈ choice/noul/score
    "n_questions": 5,
    "factors": "...", "label_agreement": "..."   # 可选，原样透传
  }
  注：questions/gold 在本仓库行件里是 JSON 字符串字段；上游若给嵌套对象同样兼容。
  仅 gold.type == "choice" 的题参与增广；noul/score 题不动。

输出行件（增广后，每行一个 JSON 对象）：
  - 含 ≥1 个 choice 题的行件 → 输出 n_orders 份副本（默认 5×；3 行 → 15 行）；
  - 不含 choice 题的行件 → 原样输出 1 份（与 token 层构建器一致：非 choice 件不增广）；
  - 第 o 份副本（o = 0..n_orders-1）内，每个 choice 题：
      · criteria 按置换后的键序重建（选项呈现顺序改变）；
      · gold.probabilities 按同一键序重建（概率随选项走）；
      · gold.label 保持原键（正确答案不变，仅呈现顺序变）；
      · label_agreement 等键值字段不动（均以选项键寻址，顺序无关）；
  - 每份副本新增 "_flipaug" 字段：{"order": o, "row_idx": i, "seed": N,
    "perms": {qid: [重排后的选项键序]}}，供审计与回溯；
  - 输出不含原序行件（n_orders 份均为随机序；需要原序请自行合并原文件）；
  - 注：n_orders 份副本是 n_orders 次独立随机置换，允许个别相同——与训练侧
    构建器口径一致（o5 混件 audit 即含约 5% identity 置换；k 越小碰撞概率越高）。

种子方案（与训练侧构建器同公式）：
  π = randperm(k, seed = 1000003 * base_seed + i * 101 + o + q)
  i = 行序号（0-based）、o = 副本序号、q = 该题在本行内序号、k = 该题选项数、
  base_seed = --seed（默认 42，训练侧 BASE_SEED=42）。
  确定性：同 --seed、同参数、同输入文件 → 输出逐字节一致（无系统随机源）。

用法：
  python3 flipaug.py in.jsonl out.jsonl [--seed 42] [--n-orders 5]
  校验：python3 -m py_compile flipaug.py
  样例：python3 flipaug.py examples/sample_in.jsonl /tmp/out.jsonl --seed 42
        （3 行含 choice 题 → 15 行；详见 README.md「用法」节）
"""

import argparse
import json
import random
import sys

DEFAULT_SEED = 42
DEFAULT_N_ORDERS = 5


def load_field(row, key):
    """questions/gold 兼容「JSON 字符串」与「嵌套对象」两种形态。"""
    v = row.get(key)
    if v is None:
        return None
    if isinstance(v, str):
        return json.loads(v)
    return v


def randperm(k, rng):
    """Fisher–Yates 均匀随机置换（随机流用标准库 random，见文件头注）。"""
    perm = list(range(k))
    rng.shuffle(perm)
    return perm


def choice_qids(questions, gold):
    """返回参与增广的 qid 列表：gold.type == 'choice' 且 criteria 为字典。"""
    if not isinstance(questions, dict):
        return []
    out = []
    for qid, q in questions.items():
        if not isinstance(q, dict) or not isinstance(q.get("criteria"), dict):
            continue
        g = gold.get(qid) if isinstance(gold, dict) else None
        g = g if isinstance(g, dict) else {}
        if g.get("type") == "choice":
            out.append(qid)
    return out

def reorder_row(row, row_idx, seed, n_orders):
    """返回该行件的增广副本列表（含 choice 题 → n_orders 份；否则 1 份原样）。"""
    questions = load_field(row, "questions")
    gold = load_field(row, "gold")
    qids = choice_qids(questions, gold)
    if not qids:
        return [row]
    copies = []
    for o in range(n_orders):
        new = dict(row)
        # 深拷贝（json 往返，保持与输入一致的类型语义）
        new_q = json.loads(json.dumps(questions, ensure_ascii=False))
        new_g = json.loads(json.dumps(gold, ensure_ascii=False)) if isinstance(gold, dict) else None
        perms = {}
        for q_pos, qid in enumerate(qids):
            criteria = new_q[qid]["criteria"]
            keys = list(criteria.keys())
            k = len(keys)
            if k < 2:
                continue
            rng = random.Random(1000003 * seed + row_idx * 101 + o + q_pos)
            perm = randperm(k, rng)
            new_order = [keys[j] for j in perm]
            new_q[qid]["criteria"] = {key: criteria[key] for key in new_order}
            if new_g is not None and isinstance(new_g.get(qid), dict):
                probs = new_g[qid].get("probabilities")
                if isinstance(probs, dict):
                    new_g[qid]["probabilities"] = {
                        key: probs.get(key, 0.0) for key in new_order}
            perms[qid] = new_order
        new["questions"] = json.dumps(new_q, ensure_ascii=False, separators=(",", ":"))
        if new_g is not None:
            new["gold"] = json.dumps(new_g, ensure_ascii=False, separators=(",", ":"))
        new["_flipaug"] = {"order": o, "row_idx": row_idx, "seed": seed, "perms": perms}
        copies.append(new)
    return copies


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="flipaug：每用例 n_orders 份选项序随机增广（typed-decisions 行件级）")
    ap.add_argument("in_jsonl", help="输入行件文件（typed-decisions jsonl）")
    ap.add_argument("out_jsonl", help="输出增广行件文件")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED,
                    help="增广 base seed（默认 %d；训练侧 BASE_SEED=42）" % DEFAULT_SEED)
    ap.add_argument("--n-orders", type=int, default=DEFAULT_N_ORDERS,
                    help="每用例增广份数（默认 %d；训练侧 o3/o5 臂用 3/5）" % DEFAULT_N_ORDERS)
    args = ap.parse_args(argv)
    if args.n_orders < 1:
        print("ERROR: --n-orders must be >= 1", file=sys.stderr)
        return 2

    rows = []
    with open(args.in_jsonl, "r", encoding="utf-8") as fh:
        for ln, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append((json.loads(line), ln))
            except json.JSONDecodeError as e:
                print("PARSE_ERROR line %d: %s" % (ln, e), file=sys.stderr)
                return 2

    out, n_choice_rows = [], 0
    for i, (row, ln) in enumerate(rows):
        copies = reorder_row(row, i, args.seed, args.n_orders)
        if len(copies) > 1:
            n_choice_rows += 1
        out.extend(copies)

    with open(args.out_jsonl, "w", encoding="utf-8") as fh:
        for row in out:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("IN rows=%d choice_rows=%d OUT rows=%d (x%d per choice row) seed=%d"
          % (len(rows), n_choice_rows, len(out), args.n_orders, args.seed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
