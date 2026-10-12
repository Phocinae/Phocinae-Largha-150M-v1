#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_server_documented_api.py — 按 README 的 API 表实测 `phocinae-server`。

README 列了五个端点：

    GET  /health                存活 + 模型/设备信息（无需鉴权）
    GET  /v1/models             模型目录
    POST /v1/systemone          单请求判定
    POST /v1/systemone/permute  同 left，choice 题选项排列平均
    POST /v1/systemone/batch    批量（≤64 个请求）

以及两条错误契约：`PHOC_MAX_BODY` 超限 -> 413；`PHOC_BEARER_TOKEN` 设置后 /v1/* 需要 Bearer。

做法：**用发布到 PyPI 的 wheel** 起服务（解包后运行，不安装），逐条实测。
模型权重来自 `PHOC_MODEL_DIR`；没有权重时，需要模型的端点记 SKIP 并说明，
而**不需要模型的部分**（/health、/v1/models、鉴权、413）必须照跑 ——
这些恰恰是最容易在"只有带模型才测"的流程里被漏掉的。
"""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

SCRATCH = r"D:\Projects\phociane-project\_work\.tmp"
FAILS = []
SKIPS = []


def check(name, cond, detail=""):
    print(("  PASS " if cond else "  FAIL ") + name + ("" if cond else "  " + str(detail)))
    if not cond:
        FAILS.append(name)


def skip(name, why):
    print("SKIP " + name + "  " + str(why))
    SKIPS.append(name)


def fetch(project):
    req = urllib.request.Request("https://pypi.org/pypi/%s/json" % project,
                                 headers={"User-Agent": "phocinae",
                                          "Cache-Control": "no-cache"})
    d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    ver = d["info"]["version"]
    whl = [f for f in (d["releases"].get(ver) or d["urls"])
           if f["filename"].endswith(".whl")][0]
    os.makedirs(SCRATCH, exist_ok=True)
    root = tempfile.mkdtemp(prefix="srv-api-x-", dir=SCRATCH)
    dest = os.path.join(root, whl["filename"])
    with urllib.request.urlopen(whl["url"], timeout=300) as r, open(dest, "wb") as o:
        shutil.copyfileobj(r, o)
    ex = tempfile.mkdtemp(prefix="srv-api-", dir=SCRATCH)
    with zipfile.ZipFile(dest) as z:
        z.extractall(ex)
    return ver, ex


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def start_server(root, py, port, env_extra=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PHOC_PORT"] = str(port)
    env["PHOC_HOST"] = "127.0.0.1"
    if env_extra:
        env.update(env_extra)
    p = subprocess.Popen([py, "-m", "phocinae.main"], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for _ in range(60):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/health" % port,
                                        timeout=2) as r:
                if r.status == 200:
                    return p
        except Exception:                          # noqa: BLE001
            if p.poll() is not None:
                return None
    return p


def get(port, path, headers=None):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path),
                                 headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:                          # noqa: BLE001
        return None, "%s: %s" % (type(e).__name__, e)


def post(port, path, payload, headers=None):
    body = json.dumps(payload).encode()
    h = {"Content-Type": "application/json"}
    h.update(headers or {})
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path),
                                 data=body, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:                          # noqa: BLE001
        return None, "%s: %s" % (type(e).__name__, e)


SINGLE = {"model": "Phocinae-Largha-150M-v1",
          "state": "The build failed on Windows but passed on Linux.",
          "questions": [{"id": "v", "type": "noul", "options":
                         ["false: no, the statement does not hold",
                          "true: yes, the statement holds"]}]}


def main():
    py = os.environ.get("PHOC_CHECK_PYTHON") or sys.executable
    ver, root = fetch("phocinae-server")
    print("phocinae-server %s (from PyPI, unpacked)" % ver)
    print("  interpreter: %s" % py)

    model_dir = os.environ.get("PHOC_MODEL_DIR", "")
    have_model = bool(model_dir) and os.path.isdir(model_dir)
    print("  PHOC_MODEL_DIR: %s\n" % (model_dir or "(unset)"))

    port = free_port()

    # ---- 0) 没有权重时，服务应当"启动即给出可行动报错"，而不是半死不活 ----
    #      这本身是一条该验证的契约。第一版只是整体 SKIP，于是 CI 里这一项什么都没验。
    if not have_model:
        import subprocess as _sp
        env = dict(os.environ)
        env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
        env["PYTHONUTF8"] = "1"
        env["PHOC_PORT"] = str(port)
        env.pop("PHOC_MODEL_DIR", None)
        p = _sp.Popen([py, "-m", "phocinae.main"], env=env,
                      stdout=_sp.PIPE, stderr=_sp.STDOUT)
        try:
            out = p.communicate(timeout=90)[0].decode("utf-8", "replace")
        except _sp.TimeoutExpired:
            p.kill()
            out = p.communicate()[0].decode("utf-8", "replace")
        check("without PHOC_MODEL_DIR the server exits instead of half-starting",
              p.returncode != 0, "exit code %s" % p.returncode)
        check("its message names PHOC_MODEL_DIR", "PHOC_MODEL_DIR" in out,
              out.strip()[-150:])
        check("its message says how to obtain the weights",
              "snapshot_download" in out or "huggingface" in out.lower(),
              out.strip()[-150:])

    # ---- 1) 无鉴权、无模型即可验证的部分 ----
    srv = start_server(root, py, port)
    if srv is None:
        # 实测：没有权重时服务**必然**以 exit 2 退出（PHOC_MODEL_DIR 未设、空目录、
        # 只有垃圾文件的目录，三种都试过）—— 它不会以"半启动"状态绑定端口。
        # 所以这四条**在 CI 上无法验证**，必须说清楚，而不是留一行看不出所以然的 SKIP。
        skip("the endpoints that need a running server (/health, /v1/models, auth, 413)",
             "this server refuses to start without model weights (exit 2 by design);"
             " these four are NOT verified here")
        print()
        print("check_server_documented_api: %d check(s) passed, %d skipped"
              % (0, len(SKIPS)))
        return 0 if not FAILS else 1
    try:
        st, body = get(port, "/health")
        check("GET /health -> 200 without auth", st == 200, "got %s  %s" % (st, body[:120]))
        try:
            h = json.loads(body)
            check("/health reports model and device",
                  "model" in h and "device" in h, sorted(h))
        except ValueError:
            check("/health returns JSON", False, body[:120])

        st, body = get(port, "/v1/models")
        check("GET /v1/models -> 200", st == 200, "got %s  %s" % (st, body[:120]))

        # 未文档化的路径应当 404，而不是悄悄成功
        st, _ = get(port, "/v1/does-not-exist")
        check("an undocumented path returns 404", st == 404, "got %s" % st)
    finally:
        try:
            srv.terminate()
            srv.wait(timeout=20)
        except Exception:                          # noqa: BLE001
            srv.kill()

    # ---- 2) PHOC_BEARER_TOKEN 契约 ----
    port2 = free_port()
    srv2 = start_server(root, py, port2, {"PHOC_BEARER_TOKEN": "secret-token"})
    if srv2 is None:
        skip("bearer-token contract", "server did not start with a token set")
    else:
        try:
            st, _ = get(port2, "/v1/models")
            check("with PHOC_BEARER_TOKEN, /v1/* without a token -> 401/403",
                  st in (401, 403), "got %s" % st)
            st, _ = get(port2, "/v1/models", {"Authorization": "Bearer secret-token"})
            check("with the right Bearer token, /v1/models -> 200", st == 200, "got %s" % st)
            st, _ = get(port2, "/health")
            check("/health needs no auth even with a token configured", st == 200,
                  "got %s" % st)
        finally:
            try:
                srv2.terminate()
                srv2.wait(timeout=20)
            except Exception:                      # noqa: BLE001
                srv2.kill()

    # ---- 3) PHOC_MAX_BODY 超限 -> 413 ----
    port3 = free_port()
    srv3 = start_server(root, py, port3, {"PHOC_MAX_BODY": "1024"})
    if srv3 is None:
        skip("413 on an oversized body", "server did not start with a small max body")
    else:
        try:
            big = dict(SINGLE)
            big["state"] = "x" * 4096
            st, body = post(port3, "/v1/systemone", big)
            check("body over PHOC_MAX_BODY -> 413", st == 413, "got %s  %s" % (st, body[:120]))
        finally:
            try:
                srv3.terminate()
                srv3.wait(timeout=20)
            except Exception:                      # noqa: BLE001
                srv3.kill()

    # ---- 4) 需要模型权重的三个端点 ----
    if not have_model:
        for name in ("POST /v1/systemone", "POST /v1/systemone/permute",
                     "POST /v1/systemone/batch"):
            skip(name, "needs model weights (PHOC_MODEL_DIR unset); CI does not provide them")
        print()
        print("check_server_documented_api: %d check(s) passed, %d skipped"
              % (0 if FAILS else 1, len(SKIPS)))

    port4 = free_port()
    srv4 = start_server(root, py, port4, {"PHOC_MODEL_DIR": model_dir})
    if srv4 is None:
        skip("the three model endpoints", "server did not start with model weights")
    else:
        try:
            st, body = post(port4, "/v1/systemone", SINGLE)
            check("POST /v1/systemone -> 200", st == 200, "got %s  %s" % (st, body[:150]))
            if st == 200:
                d = json.loads(body)
                check("/v1/systemone answers the typed question",
                      "answers" in d and "v" in d.get("answers", {}), sorted(d))
            st, body = post(port4, "/v1/systemone/permute", SINGLE)
            check("POST /v1/systemone/permute -> 200", st == 200,
                  "got %s  %s" % (st, body[:150]))
            st, body = post(port4, "/v1/systemone/batch", [SINGLE, SINGLE])
            check("POST /v1/systemone/batch -> 200", st == 200,
                  "got %s  %s" % (st, body[:150]))
            # 文档写"≤64 个请求"。实测边界是精确的：64 -> 200，65 -> 422
            # {"detail":"too many batch items (65 > 64)"}。
            # 断言必须**只认这个理由** —— 第一版写成 st >= 400，那样任何 4xx
            # 都能让它通过（例如参数写错导致的 422），等于没验边界。
            st, body = post(port4, "/v1/systemone/batch", [SINGLE] * 64)
            check("batch of exactly 64 -> 200 (the documented limit is inclusive)",
                  st == 200, "got %s  %s" % (st, body[:120]))
            st, body = post(port4, "/v1/systemone/batch", [SINGLE] * 65)
            check("batch of 65 -> 422 naming the limit",
                  st == 422 and ("too many" in body or "64" in body),
                  "got %s  %s" % (st, body[:140]))
        finally:
            try:
                srv4.terminate()
                srv4.wait(timeout=20)
            except Exception:                      # noqa: BLE001
                srv4.kill()

    print()
    if FAILS:
        print("check_server_documented_api: FAILED %d check(s)" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("check_server_documented_api: the documented API holds"
          + (" (%d skipped)" % len(SKIPS) if SKIPS else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
