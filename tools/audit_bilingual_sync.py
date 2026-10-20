#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_bilingual_sync.py — 检查成对 README 的**结构性同步**。

（第二版。第一版有两个缺陷，都是我自己造的：）

缺陷一：把**代码块里的 `#` 注释当成标题**。根 README 的快速开始段落里有
`# 1) get the weights` 这类 Python 注释，被当成 Markdown 标题后，中英版"标题数
不一致"——而那纯粹是注释文字不同。修法：先剥掉 ``` 代码块再提取标题。

缺陷二：**把两个本就不同长度的 README 判为漂移**。`README.md` 与 `README.zh.md`
是"英文更详尽、中文更精简"的有意设计（英文版带 See it in action 与插图），
不是漏译。我的第一版把这种有意差异报成 DRIFT，属于把设计当缺陷。

所以这一版只做**真正能判定的事情**：
  * 标题层级序列（剥离代码块后）—— 允许数量不同，但报告差异供人判断
  * 图片集合 —— 只比较**本地**图片，且只报"一方有另一方完全没有"的文件，
    而不是报数量差
  * 覆盖表的**计数行**必须在两边都存在且数字相同 —— 这是我真正想防的漂移
    （我自己犯过：给中文版加了两百行覆盖表，英文版一字未动）

用法：python tools/audit_bilingual_sync.py [repo_root ...]
"""
import io
import os
import re
import sys

def _work_root():
    """Directory holding the sibling checkouts, or "" when it cannot be located."""
    env = os.environ.get("PHOC_WORK")
    if env and os.path.isdir(env):
        return env
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.isdir(os.path.join(d, "repos")) and \
                os.path.isdir(os.path.join(d, "staging")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    here = os.path.dirname(os.path.abspath(__file__))
    for _ in range(4):
        if os.path.basename(here) == "tools":
            return os.path.dirname(here)
        here = os.path.dirname(here)
    return ""


def _wp(*parts):
    """Rebuild a path this file used to hard-code, relative to the work root."""
    return os.path.join(WORK, *parts) if WORK else ""


WORK = _work_root()


PAIRS = [
    ("docs/gallery/README.md", "docs/gallery/README_cn.md"),
]
CODE_FENCE = re.compile(r"```.*?```", re.S)
HEADING = re.compile(r"^(#{1,4})\s+(.*)$", re.M)
IMG_SRC = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.I)
MD_IMG = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")

# 两边都该有、且数字必须相同的计数行。
# 2026-10-15 的文档把标签改成了 "Shipped plugin implementation" /
# "Measured, not shipped"；旧正则只认更早的两个英文写法，于是把现有行
# "看不见"，报成 one-sided —— 又是"规则没命中 vs 东西不存在"那个形状。
# 这里同时接受新旧写法，并补上另外两行：四行都该在两边出现且数字相同。
COUNT_ROWS = [
    (r"\|\s*\*\*(?:Shipped plugin implementation|Implemented by a published plugin"
     r"|已发布插件实现)\*\*\s*\|\s*(\d+)", "shipped"),
    (r"\|\s*\*\*(?:Measured, not shipped|已测量，判定不达标[^|*]*)\*\*\s*\|\s*(\d+)",
     "measured-not-shipped"),
    (r"\|\s*\*\*(?:Measured, viable|已测量，成立)\*\*\s*\|\s*(\d+)",
     "measured-viable"),
    (r"\|\s*\*\*(?:Not measured|Not yet measured|尚未测量)\*\*\s*\|\s*(\d+)",
     "unmeasured"),
]


def parse(path):
    s = io.open(path, encoding="utf-8", errors="replace").read()
    body = CODE_FENCE.sub("", s)                 # 先剥代码块，再找标题
    headings = [(len(m.group(1)), m.group(2).strip()) for m in HEADING.finditer(body)]
    imgs = {m.group(1) for m in IMG_SRC.finditer(body)}
    imgs |= {m.group(1) for m in MD_IMG.finditer(body)}
    local = {i for i in imgs if not i.startswith(("http://", "https://", "data:"))}
    return s, headings, local


def _default_root():
    """Where the paired READMEs live.

    Preferred: the sibling checkout under ``<work>/repos/...`` (the local layout).
    Fallback: the repository this tool lives in.  In CI the main repository is the
    checkout itself, not a sibling; the old single default therefore found no pair,
    printed "no real drift" and exited 0 — a green step that checked nothing.
    """
    cand = _wp("repos", "Phocinae-Largha-150M-v1")
    if cand and os.path.isdir(cand):
        return cand
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    roots = sys.argv[1:] or [_default_root()]
    fails = 0
    warned = 0
    checked = 0
    for root in roots:
        for a, b in PAIRS:
            pa, pb = os.path.join(root, a), os.path.join(root, b)
            if not (os.path.isfile(pa) and os.path.isfile(pb)):
                continue
            checked += 1
            sa, ha, ia = parse(pa)
            sb, hb, ib = parse(pb)
            problems, notes = [], []

            lvl_a, lvl_b = [h[0] for h in ha], [h[0] for h in hb]
            if lvl_a != lvl_b and len(lvl_a) == len(lvl_b):
                notes.append("same heading count but levels differ at index %d"
                             % next(i for i, (x, y) in enumerate(zip(lvl_a, lvl_b)) if x != y))
            elif len(lvl_a) != len(lvl_b):
                notes.append("heading counts differ (%d vs %d) — may be intentional"
                             % (len(lvl_a), len(lvl_b)))

            only_a = sorted(ia - ib)
            only_b = sorted(ib - ia)
            if only_a or only_b:
                problems.append("local images referenced by one language only: "
                                "in %s: %s; in %s: %s" % (a, only_a, b, only_b))

            for pat, label in COUNT_ROWS:
                ma, mb = re.search(pat, sa), re.search(pat, sb)
                if bool(ma) != bool(mb):
                    problems.append("%s row exists in one language only (%s vs %s)"
                                    % (label, bool(ma), bool(mb)))
                elif ma and ma.group(1) != mb.group(1):
                    problems.append("%s row differs: %s vs %s"
                                    % (label, ma.group(1), mb.group(1)))

            status = "DRIFT" if problems else ("note" if notes else "ok")
            print("  [%s] %s  <->  %s   headings=%d/%d local-images=%d/%d"
                  % (status, a, b, len(ha), len(hb), len(ia), len(ib)))
            for n in notes:
                print("        note: %s" % n)
            for p in problems:
                print("        %s" % p)
            if problems:
                fails += 1
            elif notes:
                warned += 1

    print()
    if checked == 0:
        # "一个 pair 都没找到" 不是通过。旧版在这里返回 0，CI 因此绿了
        # 很久而什么都没查 —— 本项目的头号失败形状。
        print("audit_bilingual_sync: FAILED — no paired README was found under %s; "
              "this is not a pass" % ", ".join(roots))
        return 1
    if fails:
        print("audit_bilingual_sync: FAILED (%d of %d pair(s) with real drift)"
              % (fails, checked))
        return 1
    print("audit_bilingual_sync: no real drift in paired READMEs"
          " (%d pair(s) checked" % checked
          + (", %d noted for review)" % warned if warned else ")"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
