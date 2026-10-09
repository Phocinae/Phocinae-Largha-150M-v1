#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""flip 五组复现配方 · 选项序翻转护栏评测脚本（发布版，Phocinae-Largha-150M-v1）。

本脚本是选项顺序翻转（option-order flip）评测的发布复现件，协议与指标逻辑
逐位镜像以下两个本地来源（未改动任何计算口径）：
  - exp/eval_flip.py（原序 / 全反序 / 随机排列三预测）
  - exp/cf_20261004/results_m_20261007/run_flip_m_20261007.py
    （N-seed 随机排列扩展，产出发布定案读数，2026-10-09 重测定案）
发布口径出处：exp/refresh_v1_20261009/flip_cpu_r4/（r4 权重，双次复跑逐位一致）
与 08_发布材料_20261007/00_定案口径表_20261008.md。

────────────────────────────────────────────────────────────────────────
【翻转协议（五组配方）】
  对每个评测 case 的每个 choice 型问题，把选项（criteria）按 5 组顺序各预测
  一次，比较模型选出的选项标签（chosen label）与「原序」是否一致：

    组1  原序 original        —— 不重排，对照基线
    组2  全反序 reversed      —— dict(reversed(list(criteria.items())))
    组3  随机排列 seed=0      —— random.Random(0)，逐 case 对 items shuffle
    组4  随机排列 seed=1      —— random.Random(1)，同上
    组5  随机排列 seed=2      —— random.Random(2)，同上

  组3–5 的种子表见同包 reshuffle_seeds.json。随机排列语义与
  exp/eval_flip.py 的 --rand-seed 逐位一致（每 seed 一个顺序 rng 逐 case
  shuffle）。翻转（flip）定义：同一问题的 chosen label 与原序不同。

────────────────────────────────────────────────────────────────────────
【三口径定义与计算方式（本脚本实现位置见 score_choice_decisions）】

  n_choice = 全部 case 中 type=="choice" 且五组均能取到 answer.choice 的
             问题-次数（发布口径：flip400 = 600，flip150 = 300）

  1) rev（flip_rate_reversed，全反序翻转率）
        rev = count(原序 chosen != 全反序 chosen) / n_choice
     发布值 0.0217（flip400：13/600；flip150：0.0200＝6/300）
     ——衡量对「选项完全倒序」的敏感性。

  2) random-mean（flip_rate_random_mean，随机排列平均翻转率）
        per_seed[s] = count(原序 chosen != seed-s 随机排列 chosen) / n_choice
        random-mean = sum(per_seed[s] for s in seeds) / len(seeds)
                    = count(所有 (问题, seed) 对中的翻转) / (n_choice * len(seeds))
     发布值 0.0144（flip400，seeds=0,1,2；flip150 为 0.0144）
     ——衡量对「随机打乱选项顺序」的平均敏感性；对 seed 取均值以压低
     单次洗牌的抽样噪声。

  3) any（flip_rate_random_any，任一随机排列翻转率）
        any = count(存在至少 1 个 seed 使 chosen != 原序) / n_choice
     发布值 0.0283（flip400：17/600；flip150：0.0300＝9/300）
     ——按「问题」计（union 口径）：只要 3 个随机排列中有任意一个翻转即
     计数一次。any ≥ per_seed[s]，且 any ≥ random-mean。

  三个口径均为「越低越好」（0 = 完全顺序不变）。

────────────────────────────────────────────────────────────────────────
【发布定案读数（CPU fp32 空载，2026-10-09 双次复现，逐位一致）】
  flip400（本包 flip_rows_subset.jsonl 全部 400 行 / 600 choice 决策）：
      rev 0.0217（13/600）· random-mean 0.0144 · any 0.0283（17/600）
      per_seed: seed0 0.0183(11) / seed1 0.0150(9) / seed2 0.0100(6)
  flip150（前 150 行 / 300 choice 决策）：
      rev 0.0200（6/300）· random-mean 0.0144 · any 0.0300（9/300）
      per_seed: seed0 0.0267(8) / seed1 0.0067(2) / seed2 0.0100(3)
  发布主数取 flip400：rev 0.0217 / random-mean 0.0144 / any 0.0283。
  备注（非发布主数）：GPU fp16 rev 0.0200/0.0217；flip1k4（train 前 1000 行，4 排列）
  0.0181/0.0150/0.0331（协议/设备/行集不同，仅证据附录）。

────────────────────────────────────────────────────────────────────────
用法：
  python eval_flip.py <model_dir> <rows_jsonl> <out_json> [n_cases] [n_perm]
                      [--perm-seeds=0,1,2] [--device=cpu] [--max-len N] [--head-max-len N]
  - n_cases：-1 = 全部行（缺省）；400 = flip400；150 = flip150。
  - n_perm：随机排列组数（缺省 3）；seeds 缺省 0..n_perm-1。
  - --device：发布口径用 cpu（fp32 空载）；cuda 可选。
复现发布值示例（CPU fp32 空载）：
  CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=2 python eval_flip.py \
      <发布ckpt目录> flip_rows_subset.jsonl flip400_repro.json 400 3
  期望输出：flip_rate_reversed=0.0217、flip_rate_random_mean=0.0144、
  flip_rate_random_any=0.0283（n_choice_decisions=600）。
"""
import os
import sys
import json
import time
import copy
import random


def _pop_int_flag(argv, name):
    """弹出可选的 `--flag N` 参数对（不存在返回 None）。"""
    if name in argv:
        i = argv.index(name)
        val = int(argv[i + 1])
        del argv[i:i + 2]
        return val
    return None


def build_variants(questions, rngs, seeds):
    """为一个 case 构造 5 组顺序的问题变体。

    questions: {qid: q}，q 含 type/criteria（criteria 为 dict 时才是选项字典）。
    返回 (q_rev, q_rand_by_seed)：
      q_rev          —— 组2：每个 choice 题 criteria 全反序；
      q_rand_by_seed —— 组3–5：{seed: {qid: q}}，每 seed 一个 rng 逐题 shuffle。
    非 choice 题原样透传（其答案不参与 flip 计数）。
    """
    q_rev = {}
    for qid, q in questions.items():
        q2 = copy.deepcopy(q)
        if q2.get("type") == "choice" and isinstance(q2.get("criteria"), dict):
            q2["criteria"] = dict(reversed(list(q2["criteria"].items())))
        q_rev[qid] = q2
    q_rand_by_seed = {}
    for s in seeds:
        q3 = {}
        for qid, q in questions.items():
            qq = copy.deepcopy(q)
            if qq.get("type") == "choice" and isinstance(qq.get("criteria"), dict):
                items = list(qq["criteria"].items())
                rngs[s].shuffle(items)
                qq["criteria"] = dict(items)
            q3[qid] = qq
        q_rand_by_seed[s] = q3
    return q_rev, q_rand_by_seed


def score_choice_decisions(questions, res_orig, res_rev, res_rand, seeds):
    """对一个 case 的 5 组预测结果做三口径计数（纯函数，便于单测）。

    res_* 均为 agent.predict 返回结构：{"answers": {qid: {"choice": label}, ...}}。
    返回 (n_choice, flips_rev, flips_per_seed{seed:cnt}, flips_any)：
      n_choice        —— 本 case 计入的 choice 问题-次数；
      flips_rev       —— 原序 vs 全反序 chosen label 不同的次数；
      flips_per_seed  —— 原序 vs 各 seed 随机排列不同的次数；
      flips_any       —— 任一 seed 随机排列与原序不同的问题数（union 口径）。
    口径定义：
      rev         = flips_rev / n_choice
      per_seed[s] = flips_per_seed[s] / n_choice
      random-mean = sum(flips_per_seed.values()) / (n_choice * len(seeds))
      any         = flips_any / n_choice
    """
    n_choice, flips_rev, flips_any = 0, 0, 0
    flips_per_seed = {s: 0 for s in seeds}
    for qid, q in questions.items():
        if q.get("type") != "choice":
            continue
        try:
            a0 = res_orig["answers"][qid]["choice"]
            a_rev = res_rev["answers"][qid]["choice"]
            a_rand = {s: res_rand[s]["answers"][qid]["choice"] for s in seeds}
        except Exception:
            continue  # 任一组缺答案则该问题不入分母（与定案脚本一致）
        n_choice += 1
        if a0 != a_rev:
            flips_rev += 1
        any_flip = False
        for s in seeds:
            if a0 != a_rand[s]:
                flips_per_seed[s] += 1
                any_flip = True
        if any_flip:
            flips_any += 1
    return n_choice, flips_rev, flips_per_seed, flips_any


def main():
    # 可选预算 override（缺省 None = ckpt cfg 默认，行为与 eval_flip_rows 一致）
    max_len = _pop_int_flag(sys.argv, "--max-len")
    head_max_len = _pop_int_flag(sys.argv, "--head-max-len")
    device = "cpu"
    if "--device" in sys.argv:
        i = sys.argv.index("--device")
        device = sys.argv[i + 1]
        del sys.argv[i:i + 2]
    model_dir = sys.argv[1]
    rows_path = sys.argv[2]
    out_json = sys.argv[3]
    n_cases = int(sys.argv[4]) if len(sys.argv) > 4 else -1
    n_perm = int(sys.argv[5]) if len(sys.argv) > 5 else 3
    seeds = list(range(n_perm))
    for a in sys.argv:
        if a.startswith("--perm-seeds="):
            seeds = [int(x) for x in a.split("=", 1)[1].split(",")]

    import laya  # 项目内运行时（laya.Agent）
    print("laya", getattr(laya, "__version__", "?"), "| model:", model_dir, flush=True)
    print(f"rows: {rows_path} | n_cases={n_cases} | perm seeds={seeds} | device={device}",
          flush=True)
    agent = laya.Agent(model_dir, device=device)
    print("agent ready", flush=True)

    all_rows = [json.loads(l) for l in open(rows_path, encoding="utf-8")]
    rows = all_rows if n_cases < 0 else all_rows[:n_cases]
    rngs = {s: random.Random(s) for s in seeds}

    n_choice, flips_rev, flips_any, n_ok, n_err = 0, 0, 0, 0, 0
    flips_rand = {s: 0 for s in seeds}
    t0 = time.time()
    for i, row in enumerate(rows):
        state = json.loads(row["state"])
        questions = json.loads(row["questions"])
        try:
            res_orig = agent.predict(state, questions, max_len=max_len, head_max_len=head_max_len)
            q_rev, q_rand_by_seed = build_variants(questions, rngs, seeds)
            res_rev = agent.predict(state, q_rev, max_len=max_len, head_max_len=head_max_len)
            res_rand = {s: agent.predict(state, q_rand_by_seed[s], max_len=max_len,
                                         head_max_len=head_max_len) for s in seeds}
            n_ok += 1
        except Exception as e:
            n_err += 1
            print("ERR", row.get("id"), type(e).__name__, str(e)[:120], flush=True)
            continue
        # 三口径计数：rev / per-seed / any（定义见 score_choice_decisions 注释）
        n_c, f_rev, f_rand, f_any = score_choice_decisions(questions, res_orig,
                                                           res_rev, res_rand, seeds)
        n_choice += n_c
        flips_rev += f_rev
        flips_any += f_any
        for s in seeds:
            flips_rand[s] += f_rand[s]
        if (i + 1) % 25 == 0:
            print(f"{i+1}/{len(rows)} elapsed={time.time()-t0:.0f}s n_choice={n_choice}",
                  flush=True)

    out = {
        "task": "flip 五组复现配方 · 选项序翻转护栏评测（发布版 eval_flip.py）",
        "model": model_dir,
        "rows": rows_path,
        "n_cases": len(rows),
        "n_cases_ok": n_ok,
        "n_errors": n_err,
        "n_choice_decisions": n_choice,
        "protocol": "每 case 的 choice 题做 5 组顺序预测：原序 / 全反序 / 随机排列(seed 0,1,2；"
                    "每 seed 一个顺序 rng 逐 case shuffle，语义=eval_flip --rand-seed)",
        "perm_seeds": seeds,
        # 三口径（发布主数，越低越好）：
        "flip_rate_reversed": round(flips_rev / max(1, n_choice), 4),
        "flip_rate_random_per_seed": {str(s): round(flips_rand[s] / max(1, n_choice), 4)
                                      for s in seeds},
        "flip_rate_random_mean": round(sum(flips_rand.values())
                                       / (max(1, n_choice) * len(seeds)), 4),
        "flip_rate_random_any": round(flips_any / max(1, n_choice), 4),
        "n_flips": {
            "reversed": flips_rev,
            "random_any": flips_any,
            "random_per_seed": {str(s): flips_rand[s] for s in seeds},
        },
        "device": device,
        "env": {"CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES", "unset"),
                "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS", "unset")},
        "elapsed_s": round(time.time() - t0, 1),
        "note": "flip = chosen label 与原序不同；发布定案值（CPU fp32 空载）：flip400 rev 0.0217"
                "(13/600) / random-mean 0.0144 / any 0.0283(17/600)；flip150 rev 0.0200(6/300) / "
                "random-mean 0.0144 / any 0.0300(9/300)；GPU fp16 与 flip1k4 读数仅备注。",
    }
    os.makedirs(os.path.dirname(out_json) if os.path.dirname(out_json) else ".", exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    print("FLIP_DONE")


if __name__ == "__main__":
    main()
