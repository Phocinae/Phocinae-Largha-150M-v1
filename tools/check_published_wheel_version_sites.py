#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_published_wheel_version_sites.py — 已发布的 wheel 里，版本号是否自洽。

**这条检查来自一次真实事故**：`phocinae-guard 0.1.6` 已发布到 PyPI，而它的
`phocinae_guard/guard.py` 里 `VERSION` 仍是 `0.1.5`（元数据是 0.1.6）。
于是 `phocinae-guard --version` 报的**不是这个包的版本**。

原因是本仓有**五个**版本位点，而 `guard.py` 的常量名是 `VERSION` 而不是 `__version__`，
升版本时漏了它。现在每个包的 `tools/verify_wheel_contents.py` 会在**上传前**检查这一点；
本脚本做的是**同一件事的发布后版本** —— 从 PyPI 下载**已经发出去的** wheel 再验一遍，
因为"上传前检查过了"与"PyPI 上那个文件是对的"是两件事。

判据：wheel 里**每一个**模块级 `VERSION` / `__version__` 常量都必须等于 METADATA 的 Version。
"""
import io
import json
import os
import re
import shutil
import sys
import tempfile
import ast
import urllib.request
import zipfile

from http_retry import download, get_bytes

PROJECTS = ["phocinae-guard", "phocinae-mcp", "phocinae-server", "phocinae-cli"]
FAILS = []


def _scratch_root():
    cands = []
    if os.environ.get("PHOC_SCRATCH"):
        cands.append(os.environ["PHOC_SCRATCH"])
    cands.append(os.path.join(tempfile.gettempdir(), ".phocinae-verify"))
    cands.append(os.path.join(os.getcwd(), ".phoc-scratch"))
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


SCRATCH = _scratch_root()


def internal_versions(zf):
    found = {}
    for n in zf.namelist():
        if not n.endswith(".py"):
            continue
        try:
            tree = ast.parse(zf.read(n).decode("utf-8", "replace"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        hits = []
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and t.id in ("VERSION", "__version__"):
                        v = getattr(node.value, "value", None)
                        if isinstance(v, str):
                            hits.append((t.id, v))
        if hits:
            found[n] = hits
    return found


def main():
    checked = 0
    for project in PROJECTS:
        try:
            req = urllib.request.Request("https://pypi.org/pypi/%s/json" % project,
                                         headers={"User-Agent": "phocinae",
                                                  "Cache-Control": "no-cache"})
            d = json.loads(get_bytes(req, timeout=60).decode())
        except Exception as e:                          # noqa: BLE001
            print("SKIP %-18s PyPI unreachable (%s)" % (project, type(e).__name__))
            continue
        ver = d["info"]["version"]
        files = [x for x in (d["releases"].get(ver) or d["urls"])
                 if x["filename"].endswith(".whl")]
        if not files:
            print("SKIP %-18s no wheel published for %s" % (project, ver))
            continue
        f = files[0]
        os.makedirs(SCRATCH, exist_ok=True)
        p = os.path.join(SCRATCH, f["filename"])
        if not os.path.isfile(p):
            try:
                download(f["url"], p)
            except Exception as e:                      # noqa: BLE001
                print("SKIP %-18s could not download the wheel (%s)" % (project, type(e).__name__))
                continue

        with zipfile.ZipFile(p) as z:
            metas = [n for n in z.namelist() if n.endswith("dist-info/METADATA")]
            meta = z.read(metas[0]).decode("utf-8", "replace")
            found = internal_versions(z)
        mv = re.search(r"^Version: (.+)$", meta, re.M)
        mv = mv.group(1).strip() if mv else "?"
        hits = [(k, c, v) for k, hs in found.items() for c, v in hs]
        bad = [(k, c, v) for k, c, v in hits if v != mv]
        checked += 1
        if not hits:
            print("  NOTE %-18s %s — no version constant found inside the wheel"
                  % (project, ver))
        for k, c, v in hits:
            print("  [%s] %-18s %s  %s:%s = %s"
                  % ("ok  " if v == mv else "FAIL", project, mv, k, c, v))
        for k, c, v in bad:
            FAILS.append("%s %s: %s:%s says %s but METADATA says %s"
                         % (project, ver, k, c, v, mv))

    print()
    if not checked:
        print("check_published_wheel_version_sites: FAILED — nothing could be checked")
        return 1
    if FAILS:
        print("check_published_wheel_version_sites: FAILED %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("check_published_wheel_version_sites: every published wheel reports its own"
          " version from every constant inside it (%d package(s))" % checked)
    return 0


if __name__ == "__main__":
    sys.exit(main())
