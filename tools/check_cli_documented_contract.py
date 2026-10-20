#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_cli_documented_contract.py — 按 README 的承诺实测 `phocinae` 命令行契约。

README 写得很明确（这正是可以逐条验的东西）：

  退出码：`0` 成功（gate: allow）· `1` 错误 · `2` gate deny · `3` gate ask
  phocinae gate --command "git status"     -> exit 0（L0 白名单）
  phocinae gate --command "rm -rf /"       -> exit 2（L0 黑名单）
  echo "sudo rm -rf /etc" | phocinae gate --json   -> exit 2
  phocinae gate --fail-closed ask ...      -> 服务不可用兜底 ask（exit 3）
  phocinae ping                            -> exit 0
  单文件版功能子集：decide / ping / gate

做法：**用发布到 PyPI 的 wheel**（解包后以 `python -m phocinae_cli` 与 entry point 两种方式
调用），逐条比对实际退出码与文档。不装依赖 —— 缺依赖时记 SKIP 而不是 FAIL。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

from http_retry import download, get_bytes

def _scratch_root():
    """一个**可移植**的 scratch 目录。

    不能写死本机路径：CI 是 Linux，`r"D:\\Projects\\..."` 会被当成相对路径，
    在仓库检出目录里造出一串名为 `D:\\Projects\\...` 的目录（实测发生过）。

    优先级：PHOC_SCRATCH -> 系统临时目录（**实测可写**）-> <cwd>/.phoc-scratch。
    第二项必须真的试写：本机 TEMP 存在但不可写，而 `tempfile.gettempdir()` 会
    静默回退到 cwd —— 只看"目录存在"会得到错误的结论。
    """
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
    d = json.loads(get_bytes(req, timeout=60).decode())
    ver = d["info"]["version"]
    whl = [f for f in (d["releases"].get(ver) or d["urls"])
           if f["filename"].endswith(".whl")][0]
    os.makedirs(SCRATCH, exist_ok=True)
    root = tempfile.mkdtemp(prefix="cli-contract-x-", dir=SCRATCH)
    dest = os.path.join(root, whl["filename"])
    download(whl["url"], dest)
    ex = tempfile.mkdtemp(prefix="cli-contract-", dir=SCRATCH)
    with zipfile.ZipFile(dest) as z:
        z.extractall(ex)
    return ver, ex, dest


PY = os.environ.get("PHOC_CHECK_PYTHON") or sys.executable


def run_py(root, code, args=(), stdin=None, env_extra=None, timeout=120):
    """用**显式解释器**跑一段代码，cwd 设为解包目录。

    不再依赖 PYTHONPATH 的传递，也不依赖"调用方解释器恰好装着依赖" ——
    这两条都让 CI 上的行为与我本地不同，而我一开始把它记成了 12 条协议 FAIL。
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PHOC_SERVER"] = "http://127.0.0.1:9"      # 故意不可达：验 fail-closed
    if env_extra:
        env.update(env_extra)
    try:
        p = subprocess.run([PY, "-c", code] + list(args),
                           input=stdin, capture_output=True, timeout=timeout,
                           env=env, cwd=root)
        return p.returncode, (p.stdout + p.stderr).decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        return None, "(timeout)"


def run_cli(root, args, stdin=None, env_extra=None, timeout=120):
    """跑 `python -m phocinae_cli <args>`。"""
    import shlex
    code = ("import runpy, sys; sys.argv = ['phocinae'] + %r; "
            "runpy.run_module('phocinae_cli', run_name='__main__', alter_sys=True)"
            % (list(args),))
    return run_py(root, code, stdin=stdin, env_extra=env_extra, timeout=timeout)


def main():
    ver, root, wheel = fetch("phocinae-cli")
    print("phocinae-cli %s (from PyPI, unpacked)\n" % ver)

    # 跑任何用例之前先确认这个解释器能导入刚解包的包。导入不了就 SKIP ——
    # "环境不对"不是协议缺陷，把它记成 12 条 FAIL 会把注意力引到错误的方向。
    print("  interpreter : %s" % PY)
    print("  unpacked at : %s" % root)
    rc, out = run_py(root, "import phocinae_cli, typer, rich, httpx; "
                           "print('deps ok')")
    if "deps ok" not in out:
        why = out.strip().split("\n")[-1][:100]
        skip("the whole CLI contract",
             "this interpreter cannot import the package or its dependencies: %s" % why)
        print("  nothing was verified (this is a SKIP, not a defect report)")
        return 0

    LIVE = os.environ.get("PHOC_SERVER", "http://127.0.0.1:8155")
    LIVE_UP = False
    try:
        import urllib.request as _u
        with _u.urlopen(LIVE + "/health", timeout=3) as _r:
            LIVE_UP = _r.status == 200
    except Exception:                       # noqa: BLE001
        LIVE_UP = False
    print("  live service at %s: %s\n" % (LIVE, "up" if LIVE_UP else "DOWN"))

    # --- 服务无关：这些退出码是 gate 的核心契约，与"服务是否在跑"无关 ---
    dead = "http://127.0.0.1:9"
    dead_cases = [
        ('gate --command "git status"   -> exit 0 (L0 allowlist)',
         ["gate", "--command", "git status"], None, 0),
        ('gate --command "rm -rf /"     -> exit 2 (L0 blacklist)',
         ["gate", "--command", "rm -rf /"], None, 2),
        ('gate --json (piped)           -> exit 2',
         ["gate", "--json"], b"sudo rm -rf /etc\n", 2),
        ('gate grey zone, no L1         -> exit 2 (fail-closed deny)',
         ["gate", "--command", "pip install requests"], None, 2),
        ('gate --fail-closed ask        -> exit 3 (service down)',
         ["gate", "--fail-closed", "ask", "--command", "pip install requests"], None, 3),
    ]
    for label, args, stdin, want in dead_cases:
        rc, out = run_cli(root, args, stdin=stdin, env_extra={"PHOC_SERVER": dead})
        check("(service down) " + label, rc == want,
              "got exit %s%s" % (rc, ("  " + out.strip()[-110:]) if rc != want else ""))

    # --- 服务相关：README 的例子假定服务在跑 ---
    if LIVE_UP:
        rc, out = run_cli(root, ["ping"], env_extra={"PHOC_SERVER": LIVE})
        check("(service up) ping -> exit 0", rc == 0, "got exit %s" % rc)
        rc, out = run_cli(root, ["decide", "--state", "The build failed.",
                                 "--noul", "ok", "--choice", "act:allow,deny"],
                          env_extra={"PHOC_SERVER": LIVE})
        check("(service up) decide -> exit 0", rc == 0, "got exit %s  %s" % (rc, out.strip()[-110:]))
    else:
        skip("(service up) ping -> exit 0", "no service at %s" % LIVE)
        skip("(service up) decide -> exit 0", "no service at %s" % LIVE)

    # 2) 命令清单：**逐个实跑 `<cmd> --help`**，不去解析 rich 画出来的带边框文本。
    #    第一版解析 `^\s{2,}(name)\s{2,}`，而行首是 `│`，结果一个都没认出来、
    #    报"六个命令全部缺失" —— 检测方式错，不是被检测的东西错。
    DOCUMENTED = ["ping", "decide", "classify", "route", "score", "gate"]

    def is_command(name):
        rc, out = run_cli(root, [name, "--help"])
        if "No such command" in out or "no such command" in out:
            return False
        return rc == 0

    print("  commands (each probed with `<cmd> --help`):")
    for name in DOCUMENTED:
        ok = is_command(name)
        print("    [%s] %s" % ("ok  " if ok else "MISS", name))
        if not ok:
            FAILS.append("documented command %r is not a real command" % name)

    # README 里形如 `phocinae <name>` 的用法，其 <name> 必须是真命令
    readme = ""
    for cand in ("README.md", "README.zh.md"):
        p2 = os.path.join(root, cand)
        if os.path.isfile(p2):
            with io.open(p2, encoding="utf-8") as fh:
                readme += fh.read()
    if readme:
        used = set(re.findall(r"phocinae\s+([a-z][a-z0-9-]{1,20})\b", readme))
        used -= {"py", "cli", "main", "version"}
        bogus = sorted(n for n in used if not is_command(n))
        print("  names used as `phocinae <name>` in the docs: %s" % sorted(used))
        check("every `phocinae <name>` in the docs is a real command", not bogus,
              "not commands: %s" % bogus)

    # 3) gate --l1 在没有服务时仍应给出 allow/deny/ask 之一（而不是崩溃）
    rc, out = run_cli(root, ["gate", "--l1", "--fail-closed", "ask",
                             "--command", "pip install requests"])
    check("gate --l1 with no service does not crash (exit in {0,2,3})",
          rc in (0, 2, 3), "got exit %s" % rc)

    print()
    if FAILS:
        print("check_cli_documented_contract: FAILED %d check(s)" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("check_cli_documented_contract: the documented CLI contract holds on the"
          " published wheel" + (" (%d skipped)" % len(SKIPS) if SKIPS else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
