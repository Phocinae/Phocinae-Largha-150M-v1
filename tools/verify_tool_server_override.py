#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_tool_server_override.py — 实测四个工具是否都接受 `server` 覆盖。

schema 里有 `server` 不等于行为上支持它：schema 可能是从注册表自动生成的，而
`_opt_server()` 是否真的被每个工具调用、调用后是否生效，要看**实际行为**。

做法：起一个 mock 决策服务（A），再起第二个（B），把工具级 `server` 指向 B，
看请求打到哪一个。若 `server` 被忽略，请求会落到进程级默认的 A。

判据：四个工具都必须把请求发到 B。
"""
import json
import os
import subprocess
import sys
import threading
import http.server
import socketserver
import socket
import zipfile

# Import the sibling helper from this file's own directory. The absolute path that
# used to be here only resolved on the machine where it was written, which is why this
# check never ran anywhere else.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_mcp_host_refusal import fetch_wheel  # noqa: E402

HITS = {"a": 0, "b": 0}


def make_mock(tag):
    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n)
            HITS[tag] += 1
            # 按请求里的题型回**对应的字段名**，否则会被判成"服务应答缺少字段"。
            try:
                req = json.loads(raw.decode("utf-8", "replace"))
                qt = ((req.get("questions") or [{}])[0]).get("type", "choice")
            except ValueError:
                qt = "choice"
            key = {"choice": "choice_choice", "noul": "noul_bool",
                   "score": "score_score"}.get(qt, "choice_choice")
            out = {"answers": {"v": 0 if qt == "choice" else 5},
                   "option_scores": {"v": [0.9, 0.1]},
                   "answer_confidence": {"v": 0.9},
                   "usage": {"input_tokens": 1, "output_tokens": 0}}
            out["answers"] = out["answers"]
            data = json.dumps(out).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            data = b'{"status":"ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), H)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]


def parse_response(out, rid=2):
    """返回 (kind, payload)：kind 是 'result' / 'error' / 'none'。

    第一版只找 `result`，于是**服务端明确报错**与**没有应答**在我眼里一样 ——
    我据此把 score 报成"override 被忽略"，而真实原因是参数类型不对。
    """
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if o.get("id") != rid:
            continue
        if "error" in o:
            return "error", o["error"]
        return "result", o.get("result")
    return "none", None


def call(root, default_server, tool, args):
    boot = ("import sys; sys.path.insert(0, %r); "
            "from phocinae_mcp.server import main; sys.exit(main())") % root
    reqs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "srv-override", "version": "1"}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": tool, "arguments": args}},
    ]
    payload = ("\n".join(json.dumps(r) for r in reqs) + "\n").encode()
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    p = subprocess.run([sys.executable, "-c", boot, "--server", default_server,
                        "--timeout", "3"],
                       input=payload, capture_output=True, timeout=120, env=env)
    return p.stdout.decode("utf-8", "replace")


# 参数类型必须按 schema：
#   gate.command      string
#   classify.labels   array<string>
#   route.tools       array<string>
#   score.criteria    array<string>      <-- 我曾经传成字符串，被 -32602 正确拒绝
#
# `gate` 用**灰区命令**：`git status` 由 L0 离线放行，本来就不调用服务，
# 用它验证 `server` 覆盖什么也证明不了（我第一版就是这么误报的）。
CASES = [
    ("gate", {"command": "pip install requests"}),
    ("classify", {"state": "the build failed", "labels": ["bug", "feature"]}),
    ("route", {"state": "read a file", "tools": ["read_file", "write_file"]}),
    ("score", {"state": "risk of data loss", "criteria": ["risk", "impact"]}),
]

def main():
    ver, root, wheel = fetch_wheel("phocinae-mcp")
    a, url_a = make_mock("a")
    b, url_b = make_mock("b")
    print("phocinae-mcp %s" % ver)
    print("  process default server : %s (mock A)" % url_a)
    print("  tool-level override    : %s (mock B)\n" % url_b)

    fails = []
    for tool, args in CASES:
        HITS["a"] = HITS["b"] = 0
        call(root, url_a, tool, dict(args, server=url_b))
        ok = HITS["b"] > 0 and HITS["a"] == 0
        print("  [%s] %-9s -> A=%d B=%d  %s"
              % ("ok  " if ok else "FAIL", tool, HITS["a"], HITS["b"],
                 "override honoured" if ok else "override IGNORED or wrong target"))
        if not ok:
            fails.append(tool)

    a.shutdown()
    b.shutdown()
    print()
    if fails:
        print("verify_tool_server_override: FAILED for %s" % fails)
        return 1
    print("verify_tool_server_override: all four tools honour a per-call `server`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
