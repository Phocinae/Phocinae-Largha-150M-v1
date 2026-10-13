#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_l0_count_claims.py — 每个 README 里对 L0 表条数的声称，是否等于真实条数。

**为什么单独做这一条**：L0 表的条目数是**全项目被引用最多的数字**（guard、mcp、cli、
js、以及模型仓的文档都会提到），而它**会随加规则而变化**。实测就发现两处不一致：

    guard README（含已发布的 0.1.5）: "24 条黑名单正则"      实际 26   <- 过期
    phocinae-js README            : "40 + 30 + 26"          实际 40+31+26 <- 前缀数过期

两处**互相矛盾**（一份说 24、一份说 26 描述同一张表），而**两份读起来都很权威** ——
这正是数字类声称的危险之处：它们比"若干条"更可信，因此更少被质疑。

判据：把每个 README 里 `N 条精确白名单` / `N 条前缀白名单` / `N 条黑名单` 抽出来，
与 `l0_table.json` 的实测长度逐个比对。**数字与真实值不符即 FAIL。**
"""
import io
import json
import os
import re
import sys

def _work_root():
    """Directory holding the sibling checkouts, or the CWD as a last resort."""
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
    return os.getcwd()


def _wp(*parts):
    return os.path.join(WORK, *parts)


WORK = _work_root()


W = WORK or os.getcwd()
# Built with _wp so the platform separator is used: os.path.join with a literal
# backslash inside the second argument does not convert it, so on Linux this was a
# filename that literally contained a backslash and never existed.
GUARD_TABLE = _wp("repos", "phocinae-guard", "l0_table.json")
if not GUARD_TABLE or not os.path.isfile(GUARD_TABLE):
    # Also accept the environment override used by the other tools.
    _env = os.environ.get("PHOC_GUARD_REPO")
    if _env and os.path.isfile(os.path.join(_env, "l0_table.json")):
        GUARD_TABLE = os.path.join(_env, "l0_table.json")

READMES = [
    os.path.join(W, r"repos\phocinae-guard\README.md"),
    os.path.join(W, r"repos\phocinae-mcp\README.md"),
    os.path.join(W, r"repos\phocinae-server\README.md"),
    os.path.join(W, r"staging\phocinae-cli\README.md"),
    os.path.join(W, r"staging\phocinae-js\README.md"),
    os.path.join(W, r"repos\dsh-phocinae\README.md"),
    os.path.join(W, r"repos\codebuddy-phocinae\README.md"),
    os.path.join(W, r"repos\workbuddy-phocinae\README.md"),
]

# 三种写法都要认：`40 条精确白名单` / `31 条前缀白名单` / `26 条黑名单正则`
PATTERNS = [
    (r"(\d+)\s*条(?:精确)?白名单", "whitelist"),
    (r"(\d+)\s*条前缀白名单", "whitelist_prefix"),
    (r"(\d+)\s*条黑名单", "blacklist"),
]

FAILS = []


def main():
    if not GUARD_TABLE or not os.path.isfile(GUARD_TABLE):
        print("SKIP the guard checkout is not available here, so the counts cannot "
              "be compared (nothing was verified)")
        return 0
    with io.open(GUARD_TABLE, encoding="utf-8") as fh:
        table = json.load(fh)
    actual = {k: len(table[k]) for k in ("whitelist", "whitelist_prefix", "blacklist")}
    print("actual counts in l0_table.json: %s\n" % actual)

    checked = 0
    for path in READMES:
        rel = os.path.relpath(path, W)
        if not os.path.isfile(path):
            print("  SKIP %s (no such file)" % rel)
            continue
        with io.open(path, encoding="utf-8") as fh:
            text = fh.read()
        found_any = False
        for pat, key in PATTERNS:
            for m in re.finditer(pat, text):
                claimed = int(m.group(1))
                # 前缀白名单的写法会同时命中"白名单"那条，所以先判更具体的
                if key == "whitelist" and "前缀" in m.group(0):
                    continue
                found_any = True
                checked += 1
                ok = claimed == actual[key]
                print("  [%s] %-42s %s: claims %d, actual %d"
                      % ("ok  " if ok else "FAIL", rel, key, claimed, actual[key]))
                if not ok:
                    FAILS.append("%s claims %d %s entries but the table has %d"
                                 % (rel, claimed, key, actual[key]))
        if not found_any:
            print("  [ -- ] %-42s no L0 count claim" % rel)

    print()
    if not checked:
        print("audit_l0_count_claims: FAILED — no claim was found to check; "
              "an empty scan is not a pass")
        return 1
    if FAILS:
        print("audit_l0_count_claims: FAILED %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("audit_l0_count_claims: every documented L0 count matches the table (%d claim(s))"
          % checked)
    return 0


if __name__ == "__main__":
    sys.exit(main())
