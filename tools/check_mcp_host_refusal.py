#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_mcp_host_refusal.py — 验证 MCP README 承诺的"非回环地址拒绝启动（exit 2）"。

**为什么查这个**：`audit_doc_claims_have_tests.py` 发现四个已发布包里**唯一**一条
"文档写了、测试没验"的断言就是它 —— MCP README L63：

    `--host` 只允许 `127.0.0.1` / `localhost` / `::1`；其他地址直接拒绝启动（exit 2）

这条是**安全属性**（防止把本地决策服务绑到公网），恰恰最不该没有测试。

做法：对**发布到 PyPI 的 wheel**（解包后直接跑，不安装）逐个试 5 个主机名：

  * 三个回环地址  -> 应当**开始监听**（用超时杀掉即为"启动了"）
  * 两个非回环地址 -> 应当**立即 exit 2**

判据：回环必须启动、非回环必须 exit 2。任一条不符就是文档或实现的缺陷。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

# 显式的 scratch 目录，不用 tempfile.gettempdir()。
#
# 这个环境里系统 TEMP 不可写（Permission denied），于是 Python 的 gettempdir()
# **回退到当前工作目录** —— 实测 `tempfile.gettempdir() == os.getcwd()`。因此
# `dir=tempfile.gettempdir()` 并不能把文件移出仓库，只是让泄漏看起来被修好了。
# 这里用一个绝对路径，与 cwd 无关，且位于 _work/ 之下（不属于任何仓库）。
SCRATCH = r"D:\Projects\phociane-project\_work\.tmp"


def _scratch(prefix):
    """在 SCRATCH 下建一个临时目录；SCRATCH 不可用时才退回 gettempdir()。"""
    try:
        os.makedirs(SCRATCH, exist_ok=True)
        return tempfile.mkdtemp(prefix=prefix, dir=SCRATCH)
    except OSError:
        return tempfile.mkdtemp(prefix=prefix)
import urllib.request
import zipfile

BOOT = ("import sys; sys.path.insert(0, %r); "
        "from phocinae_mcp.server import main; sys.exit(main())")


def fetch_wheel(project):
    req = urllib.request.Request("https://pypi.org/pypi/%s/json" % project,
                                 headers={"User-Agent": "phocinae",
                                          "Cache-Control": "no-cache"})
    d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    ver = d["info"]["version"]
    whl = [f for f in (d["releases"].get(ver) or d["urls"])
           if f["filename"].endswith(".whl")][0]
    root = _scratch("hostrefuse-x-")
    dest = os.path.join(root, whl["filename"])
    with urllib.request.urlopen(whl["url"], timeout=300) as r, open(dest, "wb") as o:
        shutil.copyfileobj(r, o)
    ex = _scratch("hostrefuse-")
    with zipfile.ZipFile(dest) as z:
        z.extractall(ex)
    # 同时返回 wheel 路径：调用方需要它来读 METADATA 里的文档正文
    # （wheel 的文件列表里没有 README.md）。
    return ver, ex, dest


LOOPBACK = ("127.0.0.1", "localhost", "::1")
OTHER = ("0.0.0.0", "192.168.1.5")
FAILS = []


def main():
    ver, root, wheel = fetch_wheel("phocinae-mcp")
    print("phocinae-mcp %s (from PyPI, unpacked not installed)\n" % ver)
    cmd = [sys.executable, "-c", BOOT % root, "--transport", "http", "--port", "0"]

    print("=== loopback hosts: must start listening ===")
    for host in LOOPBACK:
        try:
            p = subprocess.run(cmd + ["--host", host], capture_output=True, timeout=12)
            # 立即退出说明它没有开始服务
            out = (p.stdout + p.stderr).decode("utf-8", "replace")
            ok = False
            detail = "exited with %d: %s" % (p.returncode, out.strip()[-120:])
        except subprocess.TimeoutExpired:
            ok = True                     # 一直在跑 == 正在监听
            detail = "still listening after 12s (expected)"
        print("  [%s] --host %-10s %s" % ("ok  " if ok else "FAIL", host, detail))
        if not ok:
            FAILS.append("loopback host %s did not start" % host)

    print("\n=== non-loopback hosts: must refuse with exit 2 ===")
    for host in OTHER:
        try:
            p = subprocess.run(cmd + ["--host", host], capture_output=True, timeout=12)
            out = (p.stdout + p.stderr).decode("utf-8", "replace").strip()
            ok = p.returncode == 2
            detail = "exit %d%s" % (p.returncode, ("  " + out[-90:]) if out else "")
        except subprocess.TimeoutExpired:
            ok = False
            detail = "STILL LISTENING -- bound to a non-loopback address"
        print("  [%s] --host %-12s %s" % ("ok  " if ok else "FAIL", host, detail))
        if not ok:
            FAILS.append("non-loopback host %s was not refused with exit 2" % host)

    print()
    if FAILS:
        print("check_mcp_host_refusal: FAILED (%d)" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("check_mcp_host_refusal: the documented exit-2 refusal holds on the published wheel")
    return 0


if __name__ == "__main__":
    sys.exit(main())
