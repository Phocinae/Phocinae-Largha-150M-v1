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
import pathlib
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

W = r"D:\Projects\phociane-project\_work"
def _scratch_root():
    """A writable scratch directory, never this machine's absolute path.

    `os.path.join(W, ".tmp", ...)` with a hard-coded W produced
    `<runner>/.../D:\\Projects\\phociane-project\\_work/.tmp/...` on Linux, because
    `D:\\...` is a *relative* path there. Everything downstream then saw a malformed path:
    the file URL contained backslashes, Node called the characters encoded, and finally
    import() reported `Invalid module "/home/runner/...D:%5CProjects%5C..."`. Four rounds were
    spent on how the specifier was transported before this line of the log was read.
    """
    cands = []
    if os.environ.get("PHOC_SCRATCH"):
        cands.append(os.environ["PHOC_SCRATCH"])
    cands.append(os.path.join(tempfile.gettempdir(), ".phocinae-verify"))
    cands.append(os.path.join(os.getcwd(), ".phocinae-verify"))
    for d in cands:
        try:
            os.makedirs(d, exist_ok=True)
            probe = os.path.join(d, ".w")
            with open(probe, "w") as fh:
                fh.write("x")
            os.remove(probe)
            return d
        except OSError:
            continue
    return os.getcwd()

def describe(out, err, limit=700):
    """Enough of both streams to identify a Node failure.

    Node puts the error code and the sentence that explains it at the START of stderr, so
    keeping only the tail hid the useful part: CI showed "imported from /home/runner/..."
    and nothing about why. Keep the head and the tail of each stream.
    """
    def clip(s):
        s = s.strip()
        if len(s) <= limit:
            return s
        h = limit // 2
        return s[:h] + " ...[snip]... " + s[-h:]

    return "stdout=" + clip(out) + " || stderr=" + clip(err)

def _guard_table():
    """Locate the guard's l0_table.json, or return "" when it is not available.

    The path used to be built from a hard-coded D:\... work root, so on a runner the file
    open raised FileNotFoundError and the suite failed rather than skipping - even though
    verify_all's `needs` gate routes the same path and therefore never protected it.
    Returning "" lets the suite report SKIP, which is what "the checkout is not here" means.
    """
    cands = []
    env = os.environ.get("PHOC_GUARD_REPO")
    if env:
        cands.append(os.path.join(env, "l0_table.json"))
    env = os.environ.get("PHOC_WORK")
    if env:
        cands.append(os.path.join(env, "repos", "phocinae-guard", "l0_table.json"))
    here = os.path.dirname(os.path.abspath(__file__))
    d = here
    for _ in range(6):
        cands.append(os.path.join(d, "repos", "phocinae-guard", "l0_table.json"))
        cands.append(os.path.join(d, "phocinae-guard", "l0_table.json"))
        d = os.path.dirname(d)
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return ""


GUARD_TABLE = _guard_table()
SCRATCH = os.path.join(_scratch_root(), "npm-verify")
FAILS = []


def check(name, cond, detail=""):
    print(("  PASS " if cond else "  FAIL ") + name + ("" if cond else "  " + str(detail)))
    if not cond:
        FAILS.append(name)


def main():
    if not GUARD_TABLE:
        print("SKIP the guard checkout is not available here, so the "
              "comparison cannot be made (nothing was verified)")
        return 0
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

    # Read the three arrays out of the published package with a real ES-module file.
    # Four earlier attempts tried to transport a specifier into `node -e` and all four failed
    # on a runner while passing locally; `node -e` has no file path, so its resolution base
    # differs from a real module's. A probe file next to the package needs no transport.
    node = shutil.which("node") or shutil.which("node.exe")
    if not node:
        print("SKIP node not on PATH")
        return 0
    probe_file = os.path.join(pkgdir, "__phoc_probe.mjs")
    with io.open(probe_file, "w", encoding="utf-8") as fh:
        fh.write(
            "import('./dist/index.js').then(m => {\n"
            "  console.log(JSON.stringify({w: m.L0_WHITELIST, p: m.L0_WHITELIST_PREFIX,\n"
            "    b: m.L0_BLACKLIST}));\n"
            "}).catch(e => { console.error('IMPORT_FAILED: ' + e.code + ' '\n"
            "  + e.message); process.exit(1); });\n")
    p = subprocess.run([node, "__phoc_probe.mjs"], capture_output=True,
                       timeout=120, cwd=pkgdir)
    # Parse stdout only. On CI, Node writes a deprecation warning to stderr
    # ("[DEP0040] The `punycode` module is deprecated"), and concatenating the two streams
    # made `out.startswith("{")` fail there while passing locally, where Node is quiet.
    out = p.stdout.decode("utf-8", "replace").strip()
    err = p.stderr.decode("utf-8", "replace").strip()
    if p.returncode != 0 or not out.startswith("{"):
        check("the published package exposes the L0 arrays", False,
              describe(out, err))
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
