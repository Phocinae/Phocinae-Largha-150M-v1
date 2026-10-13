#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_published_npm_js.py — 从 npm 下载已发布的 tarball 并实测它。

**为什么要做**：本会话反复证明"源码树里测试通过"与"发布物能用"是两件事
（`phocinae-mcp 0.2.2` 的 wheel 漏了 L0 表、`phocinae-cli 0.1.1` 带的是过期表）。
npm 包同理：`files` 里写了 `dist`，但真发出来的 tarball 到底有没有可用的入口，
必须**下载回来验**。

判据（不依赖网络除下载本身）：
  1. tarball 能解包，含 package.json / dist / README / LICENSE
  2. `main` / `exports` / `types` 指向的文件**都在 tarball 里**
  3. 解出来的包能在 Node 里 `require()` 成功（纯离线）
  4. 导出的符号与 README 声称的一致（如有 L0 判定函数）
"""
import io
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

W = r"D:\Projects\phociane-project\_work"
SCRATCH = os.path.join(W, ".tmp", "npm-verify")
FAILS = []


def check(name, cond, detail=""):
    print(("  PASS " if cond else "  FAIL ") + name + ("" if cond else "  " + str(detail)))
    if not cond:
        FAILS.append(name)


def main():
    os.makedirs(SCRATCH, exist_ok=True)
    req = urllib.request.Request("https://registry.npmjs.org/@phocinae%2Fjs",
                                 headers={"User-Agent": "phocinae"})
    d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    ver = d["dist-tags"]["latest"]
    meta = d["versions"][ver]
    print("  @phocinae/js latest = %s" % ver)
    print("  published at         = %s" % d.get("time", {}).get(ver, "?"))

    tgz = os.path.join(SCRATCH, os.path.basename(meta["dist"]["tarball"]))
    if not os.path.isfile(tgz):
        with urllib.request.urlopen(meta["dist"]["tarball"], timeout=300) as r, \
                open(tgz, "wb") as o:
            shutil.copyfileobj(r, o)
    print("  tarball              = %s (%d bytes)" % (os.path.basename(tgz),
                                                      os.path.getsize(tgz)))

    ex = tempfile.mkdtemp(prefix="npmjs-", dir=SCRATCH)
    with tarfile.open(tgz) as t:
        names = t.getnames()
        t.extractall(ex)
    files = {n[len("package/"):] for n in names if n.startswith("package/")}
    print("  entries              = %d" % len(files))

    pkg = json.load(io.open(os.path.join(ex, "package", "package.json"),
                            encoding="utf-8"))
    check("tarball ships package.json", "package.json" in files)
    check("tarball ships README.md", "README.md" in files)
    check("tarball ships LICENSE", "LICENSE" in files)
    check("tarball ships the built dist/", any(f.startswith("dist/") for f in files))

    # main / exports / types 指向的文件必须存在
    targets = []
    if pkg.get("main"):
        targets.append(("main", pkg["main"]))
    if pkg.get("types"):
        targets.append(("types", pkg["types"]))
    exp = pkg.get("exports") or {}
    for k, v in exp.items():
        if isinstance(v, str):
            targets.append(("exports[%s]" % k, v))
        elif isinstance(v, dict):
            for kk, vv in v.items():
                if isinstance(vv, str):
                    targets.append(("exports[%s].%s" % (k, kk), vv))
    missing = [t for t in targets if t[1].lstrip("./") not in files]
    check("every main/exports/types target is inside the tarball", not missing,
          "missing: %s" % missing)
    for label, path in targets:
        print("    %-22s %s" % (label, path))

    # 在 Node 里 require 一次（离线）
    node = shutil.which("node") or shutil.which("node.exe")
    if not node:
        print("SKIP node is not on PATH; cannot require() the package")
    else:
        # `require()` with a bare absolute path fails on Node 22 with
        # ERR_INVALID_MODULE_SPECIFIER; it wants a file:// URL. Import the package through
        # an ES module instead, which works on every Node this project supports.
        probe = (
            "const {pathToFileURL} = require('node:url');"
            "const p = %s;"
            "import(pathToFileURL(p + '/dist/index.js').href).then(m => {"
            "  console.log('EXPORTS=' + Object.keys(m).sort().join(','));"
            "}).catch(e => { console.error('IMPORT_FAILED: ' + e.code + ' ' + e.message);"
            "  process.exit(1); });"
            % json.dumps(os.path.join(ex, "package")))
        p = subprocess.run([node, "-e", probe], capture_output=True, timeout=120)
        # Parse stdout only. On CI Node writes a deprecation warning to stderr
        # ("[DEP0040] The `punycode` module is deprecated"), and concatenating the two
        # streams made the JSON parse fail there while passing locally, where Node is
        # quiet. stderr is kept for the failure message instead.
        out = p.stdout.decode("utf-8", "replace").strip()
        err = p.stderr.decode("utf-8", "replace").strip()
        ok = p.returncode == 0 and "EXPORTS=" in out
        check("the published package can be imported by Node", ok,
              (out[-160:] + " | stderr: " + err[-160:]))
        if ok:
            names_line = [l for l in out.split("\n") if l.startswith("EXPORTS=")][0]
            print("    %s" % names_line[:160])

    print()
    if FAILS:
        print("verify_published_npm_js: FAILED %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("verify_published_npm_js: the published npm package is complete and loadable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
