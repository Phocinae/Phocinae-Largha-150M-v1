#!/usr/bin/env python3
"""normalize.py — typed-decisions test 行集归一化/预处理脚本.

输入 (INPUT):
  typed-decisions 上游 test 集 jsonl（LocalLLaMA/typed-decisions 原始形态）：
  每行一个 JSON 对象，嵌套字段 state / questions / gold / factors /
  label_agreement 以「JSON 字符串」二次编码存放；问题对象内没有 options 键。

输出 (OUTPUT):
  归一化后的 jsonl（本包 test_typed_400.jsonl 即由本脚本自原始行件生成）：
  1. state / questions / gold / factors / label_agreement 解析为一级 JSON
     对象（消除二次编码，逐字保留内容）；
  2. 每个问题补显式 "options" 字段（候选答案列表）：
       - choice / noul（带 criteria 字典）: criteria 的键列表（按原序）；
       - score: ["0", "1", ..., str(n_levels-1)]（0-based 等级下标）；
       - noul（无 criteria，即 duplicate / credential_compromise）:
         ["false", "true"]（取自该题 gold 概率键）；
  3. 其余内容（id / workflow / split / n_questions / criteria 文本 /
     gold 标签与分布）逐字保留，不做任何改写。
  幂等：对已归一化文件再跑一遍，经同样校验后原样输出（可作为行集自检器）。

用法:
  python normalize.py INPUT.jsonl OUTPUT.jsonl

示例:
  python normalize.py typed_decisions_test.jsonl test_typed_400.jsonl
"""
import json
import sys

EXPECT_ROWS = 400   # 上游 test 集固定 400 用例；不符仅告警不报错
QPER_ROW = 5        # 每用例固定 5 个决策问题；不符报错


def _load_rows(path):
    with open(path, encoding="utf-8") as f:
        lines = [ln for ln in f if ln.strip()]
    rows = []
    for i, ln in enumerate(lines, 1):
        try:
            rows.append(json.loads(ln))
        except json.JSONDecodeError as e:
            sys.exit(f"[FAIL] 第 {i} 行不是合法 JSON: {e}")
    if len(lines) != len(rows):
        sys.exit(f"[FAIL] 行数不一致: {len(lines)} vs {len(rows)}")
    return rows


def _derived_options(qdef, gold):
    """推导候选答案列表；返回 None 表示推导失败。"""
    qtype = qdef.get("type")
    criteria = qdef.get("criteria")
    if qtype in ("choice", "noul"):
        if isinstance(criteria, dict):
            return list(criteria.keys())
        if criteria is None:
            # 无 criteria 的 noul 题：候选集取自 gold 概率键（false/true）
            keys = sorted(gold.get("probabilities", {}).keys())
            return keys if keys else None
        return None
    if qtype == "score":
        if isinstance(criteria, list):
            return [str(i) for i in range(len(criteria))]
        return None
    return None


def normalize_rows(rows):
    out = []
    for r in rows:
        # 必需字段
        for key in ("id", "state", "questions", "gold"):
            if key not in r:
                sys.exit(f"[FAIL] 行缺字段 {key}: {r.get('id', '?')}")
        row = dict(r)
        # 消除 JSON 字符串二次编码（对 dict 幂等）
        for key in ("state", "questions", "gold", "factors", "label_agreement"):
            if isinstance(row.get(key), str):
                try:
                    row[key] = json.loads(row[key])
                except json.JSONDecodeError as e:
                    sys.exit(f"[FAIL] 行 {row['id']} 字段 {key} 解析失败: {e}")
        questions = row["questions"]
        gold = row["gold"]
        if not isinstance(questions, dict) or len(questions) != QPER_ROW:
            sys.exit(f"[FAIL] 行 {row['id']} 决策问题数 != {QPER_ROW}")
        for qid, qdef in questions.items():
            if "type" not in qdef or "instructions" not in qdef:
                sys.exit(f"[FAIL] 行 {row['id']} 问题 {qid} 缺 type/instructions")
            g = gold.get(qid)
            if not g or "label" not in g:
                sys.exit(f"[FAIL] 行 {row['id']} 问题 {qid} gold 缺失/为空")
            want = _derived_options(qdef, g)
            if want is None:
                sys.exit(f"[FAIL] 行 {row['id']} 问题 {qid} options 无法推导")
            if "options" in qdef:
                if qdef["options"] != want:  # 已归一化件的一致性自检
                    sys.exit(f"[FAIL] 行 {row['id']} 问题 {qid} options 与推导不一致")
            else:
                qdef["options"] = want
        out.append(row)
    return out


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__ + "\n用法: python normalize.py INPUT.jsonl OUTPUT.jsonl")
    src, dst = sys.argv[1], sys.argv[2]
    rows = _load_rows(src)
    if len(rows) != EXPECT_ROWS:
        print(f"[WARN] 行数 {len(rows)} != 上游 test 集固定值 {EXPECT_ROWS}")
    normalized = normalize_rows(rows)
    n_dec = sum(len(r["questions"]) for r in normalized)
    with open(dst, "w", encoding="utf-8") as f:
        for r in normalized:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[OK] 行数 {len(normalized)}，决策数 {n_dec}，已写入 {dst}")


if __name__ == "__main__":
    main()
