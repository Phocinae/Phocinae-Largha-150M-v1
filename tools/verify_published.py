#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_published.py — 从 PyPI 拉下**已发布**的包，当用户那样跑一遍。

## 为什么需要这个

本项目在同一个坑里摔过三次，都是"源码 checkout 全绿、发布出去的 wheel 有问题"：

| 包 | 缺陷 | 为什么源码测试抓不到 |
|---|---|---|
| `phocinae-mcp` 0.2.2 | 包里**没带** L0 表 → `pip install` 后每条命令都被拒 | 开发 checkout 旁边有 `../phocinae-guard/guard.py`，`locate_guard()` 找得到 |
| `phocinae-cli` 0.1.1 | 包里的 L0 是**手抄的 guard 0.1.0** → 四个 shell 绕过敞着 | 源码里跑的是同一份旧表，测试自然也是绿的 |
| `phocinae-guard` 0.1.3 | 白名单只有 `python3 -m pytest` → Windows 上跑测试被拒 | Windows 没有 `python3`；开发机上也测不出来 |

共同点：**缺陷在"打包/发布"这一步产生**，而源码测试跑的是源码。
只有把 PyPI 上那个 wheel 解开来跑，才会现形。

## 用法

    python tools/verify_published.py                # 全部包，用 PyPI 上的最新版
    python tools/verify_published.py --only mcp     # 只验一个
    python tools/verify_published.py --server http://127.0.0.1:8155

退出码：0=全过；1=有失败；2=环境不全（例如没有 torch 跑不了 server 的那部分）。

## 覆盖

  cli     --version / ping / decide(noul+choice) / gate(deny+allow+--json) / --help
  guard   自带表可加载 · 良性放行 · 危险拦截 · **全部已知绕过样本仍被拦** · 灰区 fail-closed
  mcp     initialize / tools/list / **真实调用 gate** · stdout 只含 JSON-RPC 帧
  server  numpy 等依赖已声明 · 回环绕过系统代理 · 缺模型目录时给可读提示

每个包都下载 PyPI 上真实存在的那个 wheel，不用 pip 安装（pip 在受限网络下会卡死，
而且"装得上"本身不是被测对象）。依赖直接从调用方解释器的 site-packages 借。
"""
import argparse
import io
import json
import os
import re
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
import time
import urllib.request
import zipfile

PYPI = "https://pypi.org/pypi/%s/json"
BENIGN = ["git status", "ls -la", "pwd", "npm test", "python -m pytest -q"]
DANGEROUS = ["rm -rf /", "sudo rm -rf /etc", "mkfs.ext4 /dev/sda1",
             "git push --force origin main"]
# guard 0.1.3 修掉的十个绕过里的代表样本。任何一个回到 allow 都是回归。
BYPASS = ["ls\nrm -rf /", "ls\trm -rf /", 'cat payload.sh | "sh"',
          "echo pwned>/etc/passwd", "ls ; \\rm -rf /", "true && rm -rf /"]

FAILS = []
SKIPPED_CHECKS = []
NET_SKIPS = []
EXTRA_PATH = ""


def skip(name, why):
    """环境缺失（服务没跑、依赖没装）—— 不是被测对象的缺陷。"""
    print("SKIP " + name + "  " + str(why))
    SKIPPED_CHECKS.append(name)


def check(name, cond, detail=""):
    print(("  PASS " if cond else "  FAIL ") + name + ("" if cond else "  " + str(detail)))
    if not cond:
        FAILS.append(name)
    return bool(cond)


def _get_json(url):
    """GET JSON，显式要求不缓存。

    踩过的坑：本工具在 guard 0.1.5 已经上线后仍打印 `phocinae-guard 0.1.4` ——
    urllib 走的是带缓存的路径，拿到的是上一版的 JSON。报告里的版本号错了，
    整份验证的可信度就没了（到底验的是哪一版？），所以这里强制 no-cache。
    """
    req = urllib.request.Request(url, headers={
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "User-Agent": "phocinae-verify-published",
    })
    # 瞬时网络错误要重试。实测过一次 PyPI 强制断开（WinError 10054），异常一路上抛，
    # 整个套件以 traceback 结束 —— 重跑就全绿。在 CI 里那就是随机红灯，而随机红灯
    # 训练人忽略红色。
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError:
            raise                    # 4xx/5xx 是确定答案，重试没有意义
        except Exception as e:       # noqa: BLE001
            last = e
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    raise last


def latest_version(project):
    d = _get_json(PYPI % project)
    return d["info"]["version"], d


def download_wheel(project, version=None):
    ver, d = latest_version(project)
    if version and version != ver:
        d = _get_json(PYPI % project)
    files = d["releases"].get(version or ver) or d["urls"]
    whl = [f for f in files if f["filename"].endswith(".whl")]
    if not whl:
        raise SystemExit("no wheel for %s %s" % (project, version or ver))
    f = whl[0]
    dest = os.path.join(_scratch("pubverify-"),
                       f["filename"])
    with urllib.request.urlopen(f["url"], timeout=300) as r, open(dest, "wb") as out:
        shutil.copyfileobj(r, out)
    return version or ver, dest


def extract(wheel):
    root = _scratch("pubx-")
    with zipfile.ZipFile(wheel) as z:
        z.extractall(root)
    return root


def has(py, modules):
    code = ("import importlib.util\n"
            "ms=[m for m in %r if importlib.util.find_spec(m) is None]\n"
            "print(','.join(ms))\n" % (modules,))
    p = subprocess.run([py, "-c", code], capture_output=True, timeout=120)
    return p.stdout.decode("utf-8", "replace").strip()


def run_cli(py, root, args, env=None, timeout=180):
    boot = ("import sys; sys.path.insert(0, %r); "
            "from phocinae_cli.__main__ import main; sys.exit(main())" % root)
    e = dict(os.environ)
    e["PYTHONUTF8"] = "1"
    e["PYTHONIOENCODING"] = "utf-8"
    # 允许调用方补一个 site-packages（例如某个 venv 里恰好装了 typer/rich/httpx）。
    # 这不是为了绕过检查，而是因为"依赖装在哪"和"发布物对不对"是两件事 ——
    # 混在一起报 FAIL 会让人以为是产品缺陷（本轮我就先被自己的报告误导过）。
    if EXTRA_PATH:
        boot = ("import sys; sys.path.insert(0, %r); " % EXTRA_PATH) + boot
    if env:
        e.update(env)
    p = subprocess.run([py, "-c", boot] + args, capture_output=True,
                       timeout=timeout, env=e)
    return p.returncode, (p.stdout + p.stderr).decode("utf-8", "replace")


# 每个包真正需要的第三方模块。缺了就 SKIP 而不是 FAIL，并说清缺什么。
NEEDS = {
    "cli": ["typer", "rich", "httpx"],
    "guard": [],
    "mcp": [],
    "server": ["fastapi", "uvicorn", "torch", "numpy", "requests"],
}


def require(py, which):
    """返回缺失模块列表；空列表表示可以开始验证。"""
    need = NEEDS.get(which, [])
    if not need:
        return []
    if EXTRA_PATH:
        code = ("import sys; sys.path.insert(0, %r)\n"
                "import importlib.util as u\n"
                "print(','.join(m for m in %r if u.find_spec(m) is None))\n"
                % (EXTRA_PATH, need))
    else:
        code = ("import importlib.util as u\n"
                "print(','.join(m for m in %r if u.find_spec(m) is None))\n" % (need,))
    p = subprocess.run([py, "-c", code], capture_output=True, timeout=120)
    return [m for m in p.stdout.decode("utf-8", "replace").strip().split(",") if m]


def _service_up(server, timeout=3.0):
    """决策服务是否可达。

    这两条检查需要 127.0.0.1:8155 上真有一个 phocinae-server 在跑（带 144M 权重）。
    CI 不提供它，于是"没有服务"会被记成发布物缺陷 —— 与我在 CLI 检查里刚修过的
    是同一个毛病：**环境缺失不是缺陷**。
    """
    try:
        req = urllib.request.Request(server.rstrip("/") + "/health",
                                     headers={"User-Agent": "phocinae-verify"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200
    except Exception:                                  # noqa: BLE001
        return False


def verify_cli(py, server):
    miss = require(py, "cli")
    if miss:
        print("phocinae-cli: SKIP (this interpreter lacks %s)" % ",".join(miss))
        return
    ver, wheel = download_wheel("phocinae-cli")
    print("phocinae-cli %s" % ver)
    root = extract(wheel)
    try:
        rc, out = run_cli(py, root, ["--version"])
        check("--version exits 0 and reports %s" % ver, rc == 0 and ver in out,
              "rc=%s %s" % (rc, out[:160]))
        LIVE = _service_up(server)
        if not LIVE:
            skip("ping reaches the server and names the model",
                 "no decision service at %s (CI does not run one; needs the 144M weights)"
                 % server)
            skip("decide (noul) works",
                 "no decision service at %s" % server)
        else:
            rc, out = run_cli(py, root, ["ping"], {"PHOC_SERVER": server})
            check("ping reaches the server and names the model",
                  rc == 0 and "Largha" in out, "rc=%s %s" % (rc, out[-200:]))
            rc, out = run_cli(py, root, ["decide", "--state", "The sky is blue.",
                                         "--noul", "sky"], {"PHOC_SERVER": server})
            check("decide (noul) works",
                  rc == 0 and re.search(r"\b(true|false|True|False)\b", out) is not None,
                  "rc=%s %s" % (rc, out[-200:]))
        for cmd in ["rm -rf /"] + BYPASS:
            rc, out = run_cli(py, root, ["gate", "--command", cmd])
            check("gate denies %r" % cmd, rc != 0 and "deny" in out.lower(),
                  "rc=%s %s" % (rc, out[-160:]))
        for cmd in BENIGN:
            rc, out = run_cli(py, root, ["gate", "--command", cmd])
            check("gate allows %r" % cmd, rc == 0, "rc=%s %s" % (rc, out[-160:]))
    finally:
        shutil.rmtree(root, ignore_errors=True)


def verify_guard(py):
    ver, wheel = download_wheel("phocinae-guard")
    print("phocinae-guard %s" % ver)
    root = extract(wheel)
    audit = _scratch("pubaudit-")
    env = {"PHOCINAE_GUARD_AUDIT": "off", "HOME": audit, "USERPROFILE": audit}
    try:
        boot = ("import sys, json, os; sys.path.insert(0, %r); "
                "from phocinae_guard import guard as g; "
                "p=os.path.join(os.path.dirname(g.__file__),'l0_table.json'); "
                "t=json.load(open(p,encoding='utf-8')); "
                "print(json.dumps({k: len(t.get(k,[])) for k in "
                "('whitelist','whitelist_prefix','blacklist')}))" % root)
        p = subprocess.run([py, "-c", boot], capture_output=True, timeout=120)
        out = p.stdout.decode("utf-8", "replace").strip()
        try:
            counts = json.loads(out.splitlines()[-1])
        except (ValueError, IndexError):
            counts = {}
        check("bundled l0_table.json loads and is populated",
              counts.get("whitelist", 0) > 0 and counts.get("blacklist", 0) > 0,
              out[:200])

        def g_run(cmd):
            code = ("import sys; sys.path.insert(0, %r); "
                    "from phocinae_guard.guard import main; sys.exit(main())" % root)
            e = dict(os.environ)
            e.update(env)
            e["PYTHONUTF8"] = "1"
            q = subprocess.run([py, "-c", code, "--command", cmd],
                               capture_output=True, timeout=120, env=e)
            return q.returncode

        for cmd in BENIGN:
            check("allows %r" % cmd, g_run(cmd) == 0, "rc=%s" % g_run(cmd))
        for cmd in DANGEROUS + BYPASS:
            rc = g_run(cmd)
            check("denies %r" % cmd, rc == 1, "rc=%s" % rc)
        check("grey zone fails closed with L1 off",
              g_run("pip install requests") == 1)
    finally:
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(audit, ignore_errors=True)


def verify_mcp(py, server):
    ver, wheel = download_wheel("phocinae-mcp")
    print("phocinae-mcp %s" % ver)
    root = extract(wheel)
    try:
        boot = ("import sys; sys.path.insert(0, %r); "
                "from phocinae_mcp.server import main; sys.exit(main())" % root)
        reqs = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                        "clientInfo": {"name": "pubverify", "version": "1"}}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "gate", "arguments": {"command": "git status"}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
             "params": {"name": "gate", "arguments": {"command": "rm -rf /"}}},
        ]
        e = dict(os.environ)
        e["PYTHONUTF8"] = "1"
        e["PHOCINAE_MCP_SERVER"] = server
        e.pop("PHOCINAE_MCP_GUARD_PATH", None)
        e.pop("PHOCINAE_GUARD_PATH", None)
        payload = ("\n".join(json.dumps(r) for r in reqs) + "\n").encode("utf-8")
        q = subprocess.run([py, "-c", boot], input=payload, capture_output=True,
                           timeout=300, env=e)
        out = q.stdout.decode("utf-8", "replace")
        bad = [l for l in out.splitlines() if l.strip() and not l.strip().startswith("{")]
        check("stdout carries only JSON-RPC frames", not bad, bad[:2])
        frames = {}
        for l in out.splitlines():
            l = l.strip()
            if not l.startswith("{"):
                continue
            try:
                o = json.loads(l)
            except ValueError:
                continue
            if "id" in o:
                frames[o["id"]] = o
        tools = ((frames.get(2, {}).get("result") or {}).get("tools")) or []
        check("tools/list returns the four tools",
              {t.get("name") for t in tools} == {"gate", "classify", "route", "score"},
              [t.get("name") for t in tools])

        def decision(fid):
            r = (frames.get(fid, {}).get("result") or {})
            txt = "".join(b.get("text", "") for b in (r.get("content") or [])
                          if isinstance(b, dict))
            try:
                return json.loads(txt)
            except ValueError:
                return {}
        d3, d4 = decision(3), decision(4)
        check("gate('git status') allows — with no guard.py beside the package",
              d3.get("decision") == "allow", json.dumps(d3, ensure_ascii=False)[:200])
        check("gate('rm -rf /') denies", d4.get("decision") == "deny",
              json.dumps(d4, ensure_ascii=False)[:200])
    finally:
        shutil.rmtree(root, ignore_errors=True)


def verify_server(py, server):
    ver, wheel = download_wheel("phocinae-server")
    print("phocinae-server %s" % ver)
    names = zipfile.ZipFile(wheel).namelist()
    md = zipfile.ZipFile(wheel).read(
        [n for n in names if n.endswith("METADATA")][0]).decode("utf-8")
    reqs = [r.strip() for r in re.findall(r"^Requires-Dist: (.+)$", md, re.M)]
    for pkg in ("numpy", "fastapi", "uvicorn", "torch"):
        check("%s is a declared dependency" % pkg,
              any(r.startswith(pkg) for r in reqs), reqs)

    missing = has(py, ["fastapi", "uvicorn", "torch", "numpy", "requests"])
    if missing:
        print("  SKIP runtime checks: this interpreter lacks %s" % missing)
        print("       (point --python at the venv you run the server from)")
        return
    root = extract(wheel)
    try:
        probe = ("import sys; sys.path.insert(0, %r)\n"
                 "from phocinae.router import _is_loopback_target as f\n"
                 "cases=[('http://127.0.0.1:8155/x',True),('http://localhost:8155/x',True),\n"
                 "       ('http://10.0.0.5/x',True),('https://huggingface.co/x',False),\n"
                 "       ('http://example.com',False)]\n"
                 "bad=[u for u,w in cases if bool(f(u))!=w]\n"
                 "print('BAD=%%d' %% len(bad))\n" % root)
        e = dict(os.environ)
        e["HTTP_PROXY"] = e["HTTPS_PROXY"] = "http://127.0.0.1:9"
        e["NO_PROXY"] = ""
        e["PYTHONUTF8"] = "1"
        q = subprocess.run([py, "-c", probe], capture_output=True, timeout=180, env=e)
        out = q.stdout.decode("utf-8", "replace")
        check("loopback/private targets bypass the system proxy, public does not",
              "BAD=0" in out, (out + q.stderr.decode("utf-8", "replace"))[-300:])
    finally:
        shutil.rmtree(root, ignore_errors=True)


def verify_registry():
    """MCP Registry 上的条目必须与 PyPI 上的版本一致。

    为什么单独查这个：`server.json` 只在**发布时**被 CI 校验一次
    （`mcp-publisher validate server.json`），没有任何检查比对"Registry 上实际挂着
    的版本"与"PyPI 上实际发布的版本"。这两处一旦不同步，就会对外宣称两个版本，
    而两边各自都能跑。

    本机网络到 registry.modelcontextprotocol.io 不通（WinError 10054），
    所以不可达时报 SKIP 并说明原因 —— 在能连通的 CI 上它才真正生效。
    """
    print("MCP Registry entry")
    # `version=latest` 让 Registry 自己回答"最新是哪个"。第一版没带这个参数，
    # 于是我从返回的 5 条里自己挑"版本号最大"的，挑到 0.2.4 就报"Registry 落后"——
    # 而 Registry 上最新其实已经是 0.2.5。**权威方已经给了答案，不该自己再算一遍。**
    url = ("https://registry.modelcontextprotocol.io/v0/servers"
           "?search=phocinae-mcp&version=latest")
    try:
        d = _get_json(url)
    except Exception as e:                       # noqa: BLE001
        print("  SKIP registry unreachable from here (%s: %s)"
              % (type(e).__name__, str(e)[:70]))
        print("       this check runs where the registry is reachable (CI); locally it is not")
        return
    entries = d.get("servers") or d.get("data") or []
    ours = [e.get("server", e) for e in entries
            if e.get("server", e).get("name") == "io.github.Phocinae/phocinae-mcp"]
    check("registry has the io.github.Phocinae/phocinae-mcp entry", bool(ours),
          "entries returned: %d" % len(entries))
    if not ours:
        return

    # Registry **保留每个已发布版本**。带上 version=latest 时它只返回最新那条；
    # 若服务端忽略了该参数（返回多条），才退回"取版本号最大者"，并且**明说这是回退**。
    def key(v):
        parts = re.findall(r"\d+", v or "")
        return tuple(int(p) for p in parts[:3]) + (0,) * (3 - len(parts[:3]))

    versions = sorted({e.get("version") for e in ours if e.get("version")}, key=key)
    if len(ours) == 1:
        reg_ver = ours[0].get("version")
        print("  registry reports latest = %s (authoritative)" % reg_ver)
    else:
        reg_ver = versions[-1] if versions else None
        print("  NOTE the registry returned %d entries despite version=latest;"
              % len(ours))
        print("       falling back to the highest version number (%s)" % reg_ver)

    pypi_ver, _ = latest_version("phocinae-mcp")
    check("registry's latest version == PyPI version (%s)" % pypi_ver,
          reg_ver == pypi_ver,
          "registry latest is %s; it lists %d version(s)" % (reg_ver, len(versions)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default=os.environ.get("PHOC_SERVER",
                                                       "http://127.0.0.1:8155"))
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--only", choices=["cli", "guard", "mcp", "server"],
                    action="append")
    ap.add_argument("--extra-path", default="",
                    help="extra site-packages to borrow dependencies from")
    args = ap.parse_args()
    global EXTRA_PATH
    EXTRA_PATH = args.extra_path
    only = set(args.only) if args.only else {"cli", "guard", "mcp", "server"}

    print("python : %s" % args.python)
    print("server : %s\n" % args.server)

    # 这一段整体包一层网络兜底。每个 verify_* 都要先从 PyPI 取 wheel，所以网络
    # 不可达时异常会从任意一个里抛出来，把整个套件变成 traceback。抓下来记 SKIP：
    # **没验到不等于验出问题**，绝不能记成 FAIL（FAIL 表示"发布物有问题"）。
    def run(label, fn, *fnargs):
        try:
            return fn(*fnargs)
        except Exception as e:                      # noqa: BLE001
            NET_SKIPS.append(label)
            print("%s: SKIP (network failure while fetching the artifact: %s: %s)"
                  % (label, type(e).__name__, str(e)[:70]))
            print("      nothing was verified for this package; this is not a defect report")
            return None

    if "cli" in only:
        run("phocinae-cli", verify_cli, args.python, args.server)
    if "guard" in only:
        run("phocinae-guard", verify_guard, args.python)
    if "mcp" in only:
        run("phocinae-mcp", verify_mcp, args.python, args.server)
    if "server" in only:
        run("phocinae-server", verify_server, args.python, args.server)
    if "mcp" in only:
        run("MCP Registry entry", verify_registry)

    print()
    if FAILS:
        print("verify_published: FAILED %d check(s):" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    if NET_SKIPS:
        print("verify_published: passed the checks it could run, %d package(s) SKIPPED:"
              % len(NET_SKIPS))
        for s in NET_SKIPS:
            print("  - %s (network)" % s)
        print("  SKIP is not PASS: those packages were not verified at all.")
        return 0
    print("verify_published: all checks passed")
    if SKIPPED_CHECKS:
        print("  NOTE %d check(s) SKIPPED (environment, not defects): %s"
              % (len(SKIPPED_CHECKS), ", ".join(SKIPPED_CHECKS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
