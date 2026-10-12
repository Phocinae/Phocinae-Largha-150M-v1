#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""measure_failclosed.py — 测 G27「服务不可达默认不放行」。

gallery 标注：服务挂掉 → 默认拒绝，绝不静默放行。

这是剩余未测演示里**唯一与安全直接相关**的一条，而且它的判据与前面各族的
"准确率"完全不同：它不关心判得对不对，只关心**服务不可用时会不会静默放行**。
这一类主张用"端口指向一个没人监听的地址"就能干净地测，不需要标注集。

本脚本对**发布到 PyPI 的 wheel**逐个验证三种降级情形：

  1. **服务不可达**（端口无人监听）—— 必须 deny / 非零退出码，且理由可读
  2. **服务回 5xx**（起一个只回 500 的假服务）—— 同样必须 deny
  3. **服务可用但应答缺字段** —— 必须 deny，而不是把缺失当成"没问题"

每个被测面都断言两件事：(a) 不放行；(b) 给出的是一条**可读的理由**，
而不是空拒绝或裸 traceback —— 后者会让使用者以为工具坏了而不是服务挂了。

用法：python tools/measure_failclosed.py <python-with-deps> [--extra-path DIR]
"""
import argparse
import http.server
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile


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


# 显式的 scratch 目录，不用 tempfile.gettempdir()。
#
# 这个环境里系统 TEMP 不可写（Permission denied），于是 Python 的 gettempdir()
# **回退到当前工作目录** —— 实测 `tempfile.gettempdir() == os.getcwd()`。因此
# `dir=tempfile.gettempdir()` 并不能把文件移出仓库，只是让泄漏看起来被修好了。
# 这里用一个绝对路径，与 cwd 无关，且位于 _work/ 之下（不属于任何仓库）。
SCRATCH = _wp(".tmp")


def _scratch(prefix):
    """在 SCRATCH 下建一个临时目录；SCRATCH 不可用时才退回 gettempdir()。"""
    try:
        os.makedirs(SCRATCH, exist_ok=True)
        return tempfile.mkdtemp(prefix=prefix, dir=SCRATCH)
    except OSError:
        return tempfile.mkdtemp(prefix=prefix)
import threading
import urllib.request
import zipfile
FAILS = []


def check(name, cond, detail=""):
    print(("  PASS " if cond else "  FAIL ") + name + ("" if cond else "  " + str(detail)))
    if not cond:
        FAILS.append(name)
    return bool(cond)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Handler(http.server.BaseHTTPRequestHandler):
    """可控的假服务：按 mode 决定回什么。"""
    mode = "500"

    def log_message(self, *a):
        pass

    def _send(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(n)
        if Handler.mode == "500":
            self._send(500, b'{"detail":"internal error"}')
        elif Handler.mode == "empty":
            self._send(200, b'{"answers":{},"usage":{}}')     # 缺 option_scores 等
        else:
            self._send(200, b'{}')


def start_fake(mode):
    Handler.mode = mode
    port = free_port()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % port


def download_wheel(project):
    req = urllib.request.Request("https://pypi.org/pypi/%s/json" % project,
                                 headers={"User-Agent": "phocinae-failclosed",
                                          "Cache-Control": "no-cache"})
    d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    files = d["releases"].get(d["info"]["version"]) or d["urls"]
    whl = [f for f in files if f["filename"].endswith(".whl")][0]
    dest = os.path.join(_scratch("failclosed-"),
                        whl["filename"])
    with urllib.request.urlopen(whl["url"], timeout=300) as r, open(dest, "wb") as o:
        shutil.copyfileobj(r, o)
    return d["info"]["version"], dest


def extract(wheel):
    root = _scratch("failclosed-x-")
    with zipfile.ZipFile(wheel) as z:
        z.extractall(root)
    return root


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("python")
    ap.add_argument("--extra-path", default="")
    args = ap.parse_args()
    py = args.python

    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    if args.extra_path:
        env["PHOC_EXTRA_PATH"] = args.extra_path

    print("python: %s\n" % py)

    # ---------- 1) phocinae-guard ----------
    ver, wheel = download_wheel("phocinae-guard")
    print("phocinae-guard %s" % ver)
    root = extract(wheel)
    dead = "http://127.0.0.1:%d" % free_port()
    boot = ("import sys; sys.path.insert(0, %r); "
            "from phocinae_guard.guard import main; sys.exit(main())" % root)
    for label, server in (("service unreachable", dead),):
        e = dict(env)
        e["PHOCINAE_GUARD_SERVER"] = server
        e["PHOCINAE_GUARD_AUDIT"] = "off"
        e["HOME"] = e["USERPROFILE"] = _scratch("home-")
        p = subprocess.run([py, "-c", boot, "--command", "pip install requests"],
                           capture_output=True, timeout=180, env=e)
        out = (p.stdout + p.stderr).decode("utf-8", "replace")
        check("guard: %s -> not allowed (exit != 0)" % label, p.returncode != 0,
              "rc=%s" % p.returncode)
        check("guard: %s -> gives a readable reason" % label,
              len(out.strip()) > 20 and "Traceback" not in out[-400:], out[-200:])

    # ---------- 2) phocinae-mcp（真实 MCP 会话）----------
    ver, wheel = download_wheel("phocinae-mcp")
    print("\nphocinae-mcp %s" % ver)
    root = extract(wheel)
    boot = ("import sys; sys.path.insert(0, %r); "
            "from phocinae_mcp.server import main; sys.exit(main())" % root)
    reqs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "failclosed", "version": "1"}}},
        # 灰区命令：L0 判不了，必须走模型
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "gate", "arguments": {"command": "pip install requests"}}},
        # 白名单命令：L0 应离线放行，与服务无关
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "gate", "arguments": {"command": "git status"}}},
    ]
    payload = ("\n".join(json.dumps(r) for r in reqs) + "\n").encode()

    for mode, label in (("dead", "service unreachable"), ("500", "service returns 500"),
                        ("empty", "service answers with missing fields")):
        srv = None
        if mode == "dead":
            server = "http://127.0.0.1:%d" % free_port()
        else:
            srv, server = start_fake(mode)
        try:
            e = dict(env)
            e["PHOCINAE_MCP_SERVER"] = server
            e["PHOCINAE_MCP_L1_ENABLED"] = "0"
            e.pop("PHOCINAE_MCP_GUARD_PATH", None)
            e.pop("PHOCINAE_GUARD_PATH", None)
            p = subprocess.run([py, "-c", boot], input=payload,
                               capture_output=True, timeout=240, env=e)
            out = p.stdout.decode("utf-8", "replace")
            frames = {}
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("{"):
                    try:
                        o = json.loads(line)
                    except ValueError:
                        continue
                    if "id" in o:
                        frames[o["id"]] = o

            def decision(fid):
                r = (frames.get(fid, {}).get("result") or {})
                txt = "".join(b.get("text", "") for b in (r.get("content") or [])
                              if isinstance(b, dict))
                try:
                    return json.loads(txt)
                except ValueError:
                    return {"_raw": txt[:160]}

            d2 = decision(2)
            check("mcp: grey-zone gate with %s -> deny" % label,
                  d2.get("decision") == "deny", json.dumps(d2, ensure_ascii=False)[:220])
            check("mcp: %s -> the reason names the failure" % label,
                  bool(d2.get("reason")) and len(str(d2.get("reason"))) > 15,
                  str(d2.get("reason"))[:160])

            # 白名单命令应当仍能离线放行 —— fail-closed 不该把 L0 也拖下水
            d3 = decision(3)
            check("mcp: whitelisted 'git status' still allowed offline (%s)" % label,
                  d3.get("decision") == "allow", json.dumps(d3, ensure_ascii=False)[:200])
        finally:
            if srv:
                srv.shutdown()

    print()
    if FAILS:
        print("measure_failclosed: FAILED %d assertion(s)" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("measure_failclosed: fail-closed holds on every surface tested")
    return 0


if __name__ == "__main__":
    sys.exit(main())
