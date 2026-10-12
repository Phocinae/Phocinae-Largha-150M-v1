#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_gallery_coverage.py — 把"27 个演示哪些有插件、哪些没有"变成可核查的事。

为什么需要：`docs/FEASIBILITY*.md` 里写了结论（哪些演示不该做插件），但结论是
**散文**。散文会过期、也会被误读成"作者觉得不行"。这个脚本把同一件事写成
机器可检查的断言：

  1. 27 个演示必须**全部分类**，不允许漏（数量断言，不是靠人眼数）；
  2. 声称"已实现"的演示，其插件必须**真的在发布渠道上**（PyPI / npm 查得到），
     而不是只在某个仓库里有个目录；
  3. 声称"已测量、判定不达标"的演示，必须指得出**测量脚本存在**；
  4. 声称"未测量"的必须显式列出，不允许默默消失。

这样，如果以后有人删掉了某个测量脚本、或把插件下架了，这个脚本会失败，
而不是让 README 继续宣称一件不再成立的事。

用法：python tools/audit_gallery_coverage.py
退出码：0=全部自洽；1=有断言失败。
"""
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
GALLERY = os.path.join(REPO, "docs", "gallery", "README_cn.md")
SCREEN_DOCS = os.path.join(
    r"D:\Projects\phociane-project\_work\staging\dsh-phocinae-screen", "docs")

# demo -> 状态。三种状态，含义必须清楚：
#   shipped    有已发布的插件实现它（下面 SHIPPED 给出渠道与包名）
#   measured   做过标注集测量，结论是不达标 → 不发（MEASURED 给出脚本）
#   unmeasured 尚未测量（显式列出，不隐藏）
STATUS = {
    "S01": "shipped", "S02": "shipped", "S03": "shipped",
    "S04": "shipped", "S05": "shipped",
    "S06": "measured", "S07": "measured", "S08": "measured",
    "S09": "measured", "S10": "measured", "S11": "measured",
    "S12": "measured", "S13": "measured", "S14": "measured",
    "S15": "measured", "S16": "measured", "S17": "measured",
    "S18": "measured", "S19": "measured", "S20": "measured",
    "S21": "measured", "S22": "measured", "S23": "measured",
    "S24": "measured", "G25": "measured", "G26": "measured",
    "G27": "measured",
}

# 已发布的实现。渠道必须真的查得到 —— 这是这个脚本最有价值的一条断言。
SHIPPED = {
    "S01": [("pypi", "phocinae-guard"), ("pypi", "phocinae-mcp"),
            ("npm", "dsh-phocinae")],
    "S02": [("pypi", "phocinae-guard"), ("pypi", "phocinae-mcp")],
    "S03": [("pypi", "phocinae-guard"), ("pypi", "phocinae-mcp")],
    "S04": [("pypi", "phocinae-guard")],
    "S05": [("pypi", "phocinae-guard")],
}

# 做过的测量：demo -> 脚本文件名（必须存在于 dsh-phocinae-screen/docs/）
MEASURED = {
    "S07": "measure-routing.mjs",
    "S09": "measure-screen.mjs",
    "S13": "feasibility-matrix.mjs",
    "S14": "feasibility-matrix.mjs",
    "S16": "measure-routing.mjs",
    "S17": "measure-quality-gate.mjs",
    "S22": "measure-variance-vs-order.mjs",
    "S10": "measure-latency.mjs",
    "S12": "measure-snake.mjs",
    "S08": "FEASIBILITY-zh-zero-escalate.md",
    "G27": "../Phocinae-Largha-150M-v1/tools/measure_failclosed.py",
    "S11": "measure-latency.mjs",
    "S24": "measure-latency.mjs",
    "G25": "measure-latency.mjs",
    "S06": "measure-escalation-savings.mjs",
    "G26": "measure-escalation-savings.mjs",
    "S15": "measure-expense-approval.mjs",
    "S23": "measure-bilingual.mjs",
    "S18": "measure-deterministic-first.mjs",
    "S19": "feasibility-matrix.mjs",
    "S20": "measure-screen.mjs",
    "S21": "feasibility-matrix.mjs",
}

FAILS = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + str(detail)))
    if not cond:
        FAILS.append(name)
    return bool(cond)


def get_json(url, attempts=3):
    """GET JSON，对**瞬时网络故障**重试。

    加这个是因为一次运行里出现了
    `SSL: UNEXPECTED_EOF_WHILE_READING`，于是 S02 被报成"包没发布" —— 而
    phocinae-guard 明明在 PyPI 上。把网络抖动报成"发布物缺失"是最坏的一类误报：
    它会让人去重新发布一个本来好好的包。
    """
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "phocinae-audit",
                              "Cache-Control": "no-cache"})
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError:
            raise                       # 4xx/5xx 是确定答案，不重试
        except Exception as e:          # noqa: BLE001
            last = e
            if i + 1 < attempts:
                time.sleep(2 * (i + 1))
    raise last


def pypi_ok(pkg):
    try:
        d = get_json("https://pypi.org/pypi/%s/json" % pkg)
        return True, d["info"]["version"]
    except urllib.error.HTTPError as e:
        return False, "HTTP %s" % e.code
    except Exception as e:                      # noqa: BLE001
        return False, "network: %s: %s" % (type(e).__name__, e)


def npm_ok(pkg):
    name = pkg.replace("/", "%2F")
    try:
        d = get_json("https://registry.npmjs.org/%s" % name)
        return True, d.get("dist-tags", {}).get("latest", "?")
    except urllib.error.HTTPError as e:
        return False, "HTTP %s" % e.code
    except Exception as e:                      # noqa: BLE001
        return False, "network: %s: %s" % (type(e).__name__, e)


def main():
    text = io.open(GALLERY, encoding="utf-8").read()
    demos = re.findall(r"\*\*(S\d+|G\d+)\s*·\s*([^*]+)\*\*", text)
    ids = [d[0] for d in demos]
    print("gallery demos found: %d" % len(ids))

    check("the gallery lists 27 demos", len(ids) == 27, "got %d" % len(ids))
    check("every demo is classified (no silent omissions)",
          set(ids) == set(STATUS), "missing from STATUS: %s"
          % sorted(set(ids) - set(STATUS)))
    check("no extra ids in STATUS", set(STATUS) == set(ids),
          "extra: %s" % sorted(set(STATUS) - set(ids)))

    counts = {}
    for v in STATUS.values():
        counts[v] = counts.get(v, 0) + 1
    print("classification: %s" % json.dumps(counts, sort_keys=True))

    # 1) shipped -> 渠道上真的查得到
    for demo in sorted(SHIPPED):
        check("%s is classified shipped" % demo, STATUS.get(demo) == "shipped",
              STATUS.get(demo))
        for kind, pkg in SHIPPED[demo]:
            ok, info = pypi_ok(pkg) if kind == "pypi" else npm_ok(pkg)
            check("%s: %s package %r is published (%s)" % (demo, kind, pkg, info),
                  ok, info)

    # 2) measured -> 测量脚本真的存在。
    #    脚本可能落在两处：screen 仓的 docs/（判定质量类的测量），或本仓 tools/
    #    （发布物验证与降级行为）。两处都查，而不是把路径猜成一个。
    for demo, script in sorted(MEASURED.items()):
        check("%s is classified measured" % demo, STATUS.get(demo) == "measured",
              STATUS.get(demo))
        found = None
        for cand in (os.path.join(SCREEN_DOCS, script),
                     os.path.join(HERE, os.path.basename(script)),
                     os.path.join(SCREEN_DOCS, os.path.basename(script))):
            if os.path.isfile(cand):
                found = cand
                break
        check("%s: the evidence file %s exists" % (demo, script),
              found is not None,
              "looked in %s and %s" % (SCREEN_DOCS, HERE))

    # 3) measured 的每个 demo 都要有对应的结论文档
    for doc in ("FEASIBILITY.md", "FEASIBILITY-deterministic.md",
                "FEASIBILITY-routing.md", "FEASIBILITY-quality-gate.md",
                "FEASIBILITY-flip-invariance.md",
                "FEASIBILITY-bilingual.md",
                "FEASIBILITY-expense.md",
                "FEASIBILITY-escalation.md",
                "FEASIBILITY-latency.md",
                "FEASIBILITY-failclosed.md",
                "FEASIBILITY-snake.md",
                "FEASIBILITY-zh-zero-escalate.md"):
        p = os.path.join(SCREEN_DOCS, doc)
        check("conclusion doc %s exists" % doc, os.path.isfile(p), p)

    # 4) 声明为 shipped 的 demo 必须有对应插件仓库在本地
    for demo in sorted(SHIPPED):
        if demo in ("S01", "S02", "S03", "S04", "S05"):
            check("%s: the guard repo checkout is present" % demo,
                  os.path.isfile(r"D:\Projects\phociane-project\_work\repos"
                                 r"\phocinae-guard\guard.py"))

    # 5) gallery README 里那张表必须与本脚本算出的数一致。
    #    加这条是因为它真的发生过：S17 测完之后本脚本算得 measured=10，而文档里
    #    还写着 9 —— 两处各说一套，读者无从判断哪个是真的。
    #    文档与断言不一致，等于断言没做。
    doc_path = os.path.join(REPO, "docs", "gallery", "README_cn.md")
    if os.path.isfile(doc_path):
        dt = io.open(doc_path, encoding="utf-8").read()
        # "已测量"在文档里拆成两行（判定不达标 / 成立），所以读的是**两行之和**；
        # 其余两类各一行。断言针对状态总数，避免把"分成两行"误判成数字错。
        def row_total(*labels):
            tot = 0
            seen = False
            for lab in labels:
                m = re.search(r"\*\*%s\*\*\s*\|\s*(\d+)" % re.escape(lab), dt)
                if m:
                    tot += int(m.group(1))
                    seen = True
            return tot if seen else None

        doc_rows = {
            "shipped": row_total("已发布插件实现"),
            "measured": row_total("已测量，判定不达标 → 不发", "已测量，成立"),
            "unmeasured": row_total("尚未测量"),
        }
        for key, total in doc_rows.items():
            check("gallery README states %s=%d" % (key, counts.get(key, 0)),
                  total == counts.get(key, 0),
                  "doc rows sum to %s, audit computed %d"
                  % (total, counts.get(key, 0)))

    print()
    if FAILS:
        print("audit_gallery_coverage: FAILED %d assertion(s)" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("audit_gallery_coverage: the coverage claim holds")
    print("  shipped=%d measured=%d unmeasured=%d"
          % (counts.get("shipped", 0), counts.get("measured", 0),
             counts.get("unmeasured", 0)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
