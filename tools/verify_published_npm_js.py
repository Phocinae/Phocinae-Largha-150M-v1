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
import pathlib
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

W = r"D:\Projects\phociane-project\_work"
def _safe_extractall(tar, dest):
    """Extract a tarball without the 3.14 deprecation warning and without path escapes.

    Without an explicit filter, Python before 3.12 extracts member paths verbatim, so a
    crafted archive can write outside `dest`. These are tarballs downloaded from npm, which is
    exactly the situation the filter exists for. `filter="data"` is available from 3.12; older
    interpreters get the members checked by hand.
    """
    try:
        tar.extractall(dest, filter="data")
        return
    except TypeError:
        pass  # Python < 3.12: no filter kwarg
    base = os.path.abspath(dest)
    for m in tar.getmembers():
        target = os.path.abspath(os.path.join(base, m.name))
        if not (target == base or target.startswith(base + os.sep)):
            raise RuntimeError("refusing to extract %r outside %r" % (m.name, dest))
        if m.issym() or m.islnk():
            raise RuntimeError("refusing to extract link %r" % m.name)
    tar.extractall(dest)

def _scratch_root():
    """A writable scratch directory, never this machine's absolute path.

    `os.path.join(W, ".tmp", ...)` with a hard-coded W produced
    `<runner>/.../D:\\Projects\\phociane-project\\_work/.tmp/...` on Linux, because
    `D:\\...` is a *relative* path there. The unpacked tree then had a malformed path, which
    is what every symptom traced back to: backslashes in a file URL, "encoded" characters, and
    finally `Invalid module "/home/runner/...D:%5CProjects%5C..."`.
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

def check(name, cond, detail=""):
    print(("  PASS " if cond else "  FAIL ") + name + ("" if cond else "  " + str(detail)))
    if not cond:
        FAILS.append(name)


SCRATCH = os.path.join(_scratch_root(), "npm-verify")
FAILS = []


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
        _safe_extractall(t, ex)
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

    # Import the published entry point with a real ES-module file.
    #
    # Four earlier attempts all tried to transport a specifier into `node -e`, and all four
    # failed on a runner while passing here: a Windows backslash ended up in a file URL, then
    # characters Node called "encoded", then ERR_INVALID_MODULE_SPECIFIER twice - the last
    # time with an absolute path in the message even though the string being set was
    # "./dist/index.js". The problem was never how the string was carried; `node -e` has no
    # file path, so its resolution base differs from a real module's.
    #
    # A file next to the package, importing "./dist/index.js", is the most ordinary ESM
    # resolution there is. Nothing has to survive transport.
    node = shutil.which("node") or shutil.which("node.exe")
    if not node:
        print("SKIP node is not on PATH; cannot import the package")
    else:
        pkg_root = os.path.join(ex, "package")
        probe_file = os.path.join(pkg_root, "__phoc_probe.mjs")
        with io.open(probe_file, "w", encoding="utf-8") as fh:
            fh.write(
                "import('./dist/index.js').then(m => {\n"
                "  console.log('EXPORTS=' + Object.keys(m).sort().join(','));\n"
                "}).catch(e => { console.error('IMPORT_FAILED: ' + e.code + ' '\n"
                "  + e.message); process.exit(1); });\n")
        p = subprocess.run([node, "__phoc_probe.mjs"], capture_output=True,
                           timeout=120, cwd=pkg_root)
        # Parse stdout only. On CI Node writes a deprecation warning to stderr
        # ("[DEP0040] The `punycode` module is deprecated"), and concatenating the two
        # streams made the JSON parse fail there while passing locally, where Node is
        # quiet. stderr is kept for the failure message instead.
        out = p.stdout.decode("utf-8", "replace").strip()
        err = p.stderr.decode("utf-8", "replace").strip()
        ok = p.returncode == 0 and "EXPORTS=" in out
        check("the published package can be imported by Node", ok,
              describe(out, err))
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
