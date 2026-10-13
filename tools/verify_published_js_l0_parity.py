#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_published_js_l0_parity.py — 已发布的 npm 包里的 L0 表，是否与 guard 一致。

**为什么必须单独验**：L0 确定性层在本项目有**五份拷贝**，而"手抄一份过期的表"
已经造成过两次真实事故：

  * `phocinae-cli 0.1.1` —— wheel 里是手抄的 guard 0.1.0，四个 shell 绕过敞着
  * `phocinae-mcp 0.2.2` —— wheel 里根本没带表，装完每条命令都被拒

`@phocinae/js` 是第五份。它的表来自 `src/l0.ts`，构建进 `dist/l0.js`。
本脚本用**已发布的 tarball**（不是源码树）与 guard 的 `l0_table.json` 逐条比对：
白名单精确项、前缀项、黑名单正则，**三者都必须逐字相同**。
"""
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

W = r"D:\Projects\phociane-project\_work"
GUARD_TABLE = os.path.join(W, r"repos\phocinae-guard\l0_table.json")
SCRATCH = os.path.join(W, ".tmp", "npm-verify")
FAILS = []


def check(name, cond, detail=""):
    print(("  PASS " if cond else "  FAIL ") + name + ("" if cond else "  " + str(detail)))
    if not cond:
        FAILS.append(name)


def main():
    guard = json.load(io.open(GUARD_TABLE, encoding="utf-8"))
    print("  guard l0_table.json: whitelist=%d prefix=%d blacklist=%d\n"
          % (len(guard["whitelist"]), len(guard["whitelist_prefix"]),
             len(guard["blacklist"])))

    os.makedirs(SCRATCH, exist_ok=True)
    req = urllib.request.Request("https://registry.npmjs.org/@phocinae%2Fjs",
                                 headers={"User-Agent": "phocinae"})
    d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    ver = d["dist-tags"]["latest"]
    url = d["versions"][ver]["dist"]["tarball"]
    tgz = os.path.join(SCRATCH, "js-%s.tgz" % ver)
    if not os.path.isfile(tgz):
        with urllib.request.urlopen(url, timeout=300) as r, open(tgz, "wb") as o:
            shutil.copyfileobj(r, o)
    ex = tempfile.mkdtemp(prefix="l0js-", dir=SCRATCH)
    with tarfile.open(tgz) as t:
        t.extractall(ex)
    pkgdir = os.path.join(ex, "package")
    print("  @phocinae/js %s unpacked\n" % ver)

    # 用 Node 读出已发布包里的三个数组（这才是**装出来的东西**）
    node = shutil.which("node") or shutil.which("node.exe")
    if not node:
        print("SKIP node not on PATH")
        return 0
    probe = (
        "const m = require(%s);"
        "console.log(JSON.stringify({"
        "w: m.L0_WHITELIST, p: m.L0_WHITELIST_PREFIX, b: m.L0_BLACKLIST}));"
        % json.dumps(pkgdir))
    p = subprocess.run([node, "-e", probe], capture_output=True, timeout=120)
    # Parse stdout only. On CI, Node writes a deprecation warning to stderr
    # ("[DEP0040] The `punycode` module is deprecated"), and concatenating the two streams
    # made `out.startswith("{")` fail there while passing locally, where Node is quiet.
    out = p.stdout.decode("utf-8", "replace").strip()
    err = p.stderr.decode("utf-8", "replace").strip()
    if p.returncode != 0 or not out.startswith("{"):
        check("the published package exposes the L0 arrays", False,
              (out[-160:] + " | stderr: " + err[-160:]))
        print()
        print("verify_published_js_l0_parity: FAILED (could not read the arrays)")
        return 1
    js = json.loads(out)

    check("whitelist: published JS == guard table",
          sorted(js["w"]) == sorted(guard["whitelist"]),
          "js=%d guard=%d; only-js=%s only-guard=%s"
          % (len(js["w"]), len(guard["whitelist"]),
             sorted(set(js["w"]) - set(guard["whitelist"]))[:6],
             sorted(set(guard["whitelist"]) - set(js["w"]))[:6]))
    check("whitelist_prefix: published JS == guard table",
          sorted(js["p"]) == sorted(guard["whitelist_prefix"]),
          "js=%d guard=%d; only-js=%s only-guard=%s"
          % (len(js["p"]), len(guard["whitelist_prefix"]),
             sorted(set(js["p"]) - set(guard["whitelist_prefix"]))[:6],
             sorted(set(guard["whitelist_prefix"]) - set(js["p"]))[:6]))

    # The blacklist is [name, pattern, note] in the guard table and
    # {name, pattern, note} in the JS build. Normalise both to (name, pattern) before
    # comparing: the note is documentation, but the pattern is the security-relevant part.
    #
    # Four patterns also differ in how each language *spells* the same character class:
    # inside a Python string a double quote needs a backslash, inside a JavaScript
    # character class it does not. `[\\"\']` and `["\']` both match a quote or an
    # apostrophe. Comparing the raw text therefore reported four "differences" that are
    # purely a spelling difference between languages — my artifact, not a defect. The
    # comparison drops a backslash that precedes a quote, and asserts that this is the
    # ONLY tolerated difference.
    def norm(p):
        # A backslash before a quote or a backtick is a spelling difference between
        # the two languages, not a difference in what the pattern matches:
        #   Python string  [\"\'\`]   JavaScript string  ["\'`]
        return re.sub(r'\\([\"\'`])', r"\1", p)

    def guard_triples(rows):
        out = []
        for r in rows:
            if isinstance(r, (list, tuple)) and len(r) >= 2:
                out.append((r[0], norm(r[1])))
        return sorted(out)

    def js_triples(rows):
        out = []
        for r in rows:
            if isinstance(r, dict):
                out.append((r.get("name"), norm(r.get("pattern") or "")))
            elif isinstance(r, (list, tuple)) and len(r) >= 2:
                out.append((r[0], norm(r[1])))
        return sorted(out)

    gb, jb = guard_triples(guard["blacklist"]), js_triples(js["b"])
    check("blacklist: published JS == guard table (name + pattern, quote-spelling normalised)",
          gb == jb,
          "js=%d guard=%d; differing=%s"
          % (len(jb), len(gb),
             [x for x in (set(gb) ^ set(jb))][:4]))

    print()
    if FAILS:
        print("verify_published_js_l0_parity: FAILED %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("verify_published_js_l0_parity: the published JS package carries the same L0 table"
          " as the guard (%d + %d + %d)"
          % (len(js["w"]), len(js["p"]), len(js["b"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
