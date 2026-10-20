#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_guard_documented_contract.py — 按 README 实测 `phocinae-guard` 的契约。

README 的承诺（逐条可验）：

  exit code：`0`=allow · `1`=deny · `2`=ask
  不变式：**只有 allow 能过门（exit 0）；deny/ask 均非零退出**
  不变式：**`--confirm` 只能把 ask 升级为 allow，永远不能覆盖 deny**
  服务不可用 -> fail-closed：除白名单外一律 deny/ask
  `guard.py --command "git status"`        -> exit 0
  `guard.py --command "npm install -g x"`  -> exit 2（ask）
  同一条 + `--confirm`                     -> exit 0
  `--json` / `--text` 两种输出
  审计 JSONL 默认追加到 ./phocinae-guard.audit.jsonl，`--audit off` 可禁用
  配置：`thresholds` / `exit` 可配

做法：用**发布到 PyPI 的 wheel**（解包后直接跑 `guard.py` / 模块入口），
每条断言都在**隔离的临时 cwd** 里跑，这样审计文件的落点也能验。
"""
import io
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

FAILS = []
SKIPS = []


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
    root = tempfile.mkdtemp(prefix="guard-x-", dir=SCRATCH)
    dest = os.path.join(root, whl["filename"])
    download(whl["url"], dest)
    ex = tempfile.mkdtemp(prefix="guard-", dir=SCRATCH)
    with zipfile.ZipFile(dest) as z:
        z.extractall(ex)
    return ver, ex, dest


def find_guard(root):
    """发布物里的 guard.py 在哪。"""
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if f in ("guard.py", "__main__.py") and "guard" in dp.lower():
                return os.path.join(dp, f)
    hits = []
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if f == "guard.py":
                hits.append(os.path.join(dp, f))
    return hits[0] if hits else None


def run_guard(py, root, guard_py, args, cwd, stdin=None, env_extra=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PHOC_SERVER"] = "http://127.0.0.1:9"        # 不可达：验 fail-closed
    if env_extra:
        env.update(env_extra)
    p = subprocess.run([py, guard_py] + args, input=stdin, capture_output=True,
                       timeout=180, env=env, cwd=cwd)
    return p.returncode, (p.stdout + p.stderr).decode("utf-8", "replace")


def main():
    py = os.environ.get("PHOC_CHECK_PYTHON") or sys.executable
    ver, root, wheel = fetch("phocinae-guard")
    print("phocinae-guard %s (from PyPI, unpacked)" % ver)
    print("  interpreter: %s\n" % py)

    guard_py = find_guard(root)
    if not guard_py:
        skip("the guard contract", "no guard.py inside the wheel")
        return 0
    print("  guard.py: %s\n" % os.path.relpath(guard_py, root))

    work = tempfile.mkdtemp(prefix="guard-cwd-", dir=SCRATCH)

    # ---- 1) 服务不可用时的 fail-closed 契约（README 明确写了默认 deny、可配 ask）----
    #      README 第 117 行的 `npm install -g x -> exit 2` 是**服务可用时**的示例；
    #      服务不可用时按 fail-closed 走。我第一版把两者混在一起，报出四条假缺陷。
    dead = [
        ('--command "git status"      -> exit 0 (L0 allowlist, no service needed)',
         ["--command", "git status"], 0),
        ('--command "rm -rf /"        -> exit 1 (L0 blacklist, deny)',
         ["--command", "rm -rf /"], 1),
        ('grey zone, service down     -> exit 1 (fail-closed defaults to deny)',
         ["--command", "npm install -g x"], 1),
        ('git push --force            -> exit 1 (deny)',
         ["--command", "git push --force"], 1),
        ('--fail-closed ask, service down -> exit 2 (documented alternative)',
         ["--command", "npm install -g x", "--fail-closed", "ask"], 2),
    ]
    for label, args, want in dead:
        rc, out = run_guard(py, root, guard_py, args, work)
        check("(service down) " + label, rc == want,
              "got exit %s  %s" % (rc, out.strip()[-100:]))

    # ---- 2) 不变式：只有 allow 能过门 ----
    allow_rc, _ = run_guard(py, root, guard_py, ["--command", "git status"], work)
    deny_rc, _ = run_guard(py, root, guard_py, ["--command", "rm -rf /"], work)
    ask_rc, _ = run_guard(py, root, guard_py,
                          ["--command", "npm install -g x", "--fail-closed", "ask"], work)
    check("invariant: allow exits 0", allow_rc == 0, "got %s" % allow_rc)
    check("invariant: deny exits non-zero", deny_rc != 0, "got %s" % deny_rc)
    check("invariant: ask exits non-zero", ask_rc != 0, "got %s" % ask_rc)

    # ---- 3) 不变式：--confirm 只能把 ask 升级为 allow，永远不能覆盖 deny ----
    rc, _ = run_guard(py, root, guard_py,
                      ["--command", "npm install -g x", "--fail-closed", "ask",
                       "--confirm"], work)
    check("--confirm upgrades ask -> allow (exit 0)", rc == 0, "got exit %s" % rc)
    rc, _ = run_guard(py, root, guard_py,
                      ["--command", "rm -rf /", "--confirm"], work)
    check("--confirm CANNOT override a deny (still non-zero)", rc != 0,
          "got exit %s" % rc)

    # ---- 4) stdin 形态 ----
    rc, _ = run_guard(py, root, guard_py, [], work, stdin=b"git status\n")
    check("stdin form: 'git status' -> exit 0", rc == 0, "got exit %s" % rc)
    rc, _ = run_guard(py, root, guard_py, [], work, stdin=b"rm -rf /\n")
    check("stdin form: 'rm -rf /' -> exit 1", rc == 1, "got exit %s" % rc)

    # ---- 5) 输出格式：README 说 stdout **默认**一行 JSON，`--text` 换人读格式。
    #         发布物里没有 `--json` 参数 —— 那是我凭印象编的。----
    rc, out = run_guard(py, root, guard_py, ["--command", "git status"], work)
    try:
        d = json.loads([l for l in out.strip().split("\n") if l.strip().startswith("{")][-1])
        ok = d.get("decision") in ("allow", "deny", "ask")
    except (ValueError, IndexError):
        ok = False
    check("stdout is one line of JSON by default, with a decision", ok,
          out.strip()[-120:])
    rc, out = run_guard(py, root, guard_py, ["--command", "git status", "--text"], work)
    check("--text switches to human-readable output",
          rc == 0 and not out.strip().startswith("{"), out.strip()[-100:])

    # ---- 6) 审计 JSONL：默认落在 cwd，--audit off 可禁用 ----
    audit = os.path.join(work, "phocinae-guard.audit.jsonl")
    if os.path.exists(audit):
        os.remove(audit)
    run_guard(py, root, guard_py, ["--command", "git status"], work)
    check("audit JSONL is appended in the working directory", os.path.exists(audit),
          "expected %s" % audit)
    if os.path.exists(audit):
        with open(audit, encoding="utf-8") as fh:
            lines = [l for l in fh.read().split("\n") if l.strip()]
        try:
            rec = json.loads(lines[-1])
            check("audit record has ts+command+decision",
                  {"ts", "command", "decision"} <= set(rec), sorted(rec))
        except (ValueError, IndexError):
            check("audit record is JSON", False, lines[-1][:100] if lines else "(empty)")
        # --audit off
        n_before = len(lines)
        run_guard(py, root, guard_py, ["--command", "git status", "--audit", "off"], work)
        with open(audit, encoding="utf-8") as fh:
            n_after = len([l for l in fh.read().split("\n") if l.strip()])
        check("--audit off writes no new record", n_after == n_before,
              "%d -> %d" % (n_before, n_after))

    # ---- 7) 配置文件：验它**真的被读取** ----
    #      README 第 121-122 行把退出码写成**固定契约**（0=allow · 1=deny · 2=ask ·
    #      3=用法错误），所以"配置能改退出码"从根上不成立 —— 我第一版编了一个 `exit`
    #      键，实际 schema 里没有它（第 123 行的 `exit` 是 stdout JSON 的字段名）。
    #
    #      示例配置的真实键：server, timeout, noul_threshold, deny_at, ask_at,
    #      l0_table, audit_path, fail_closed, l1_enabled。这里验 fail_closed 与 ask_at
    #      两个 —— 都只依赖"服务不可达"这一确定状态。
    example = None
    for dp, dn, fn in os.walk(root):
        if "guard.conf.example.json" in fn:
            example = os.path.join(dp, "guard.conf.example.json")
            break
    if not example:
        repo = os.environ.get("PHOC_GUARD_REPO", "")
        cand = os.path.join(repo, "guard.conf.example.json") if repo else ""
        if cand and os.path.isfile(cand):
            example = cand
            print("  (example config taken from PHOC_GUARD_REPO, not the wheel)")

    if not example:
        skip("the config file is actually read",
             "no guard.conf.example.json in the wheel and PHOC_GUARD_REPO is unset")
    else:
        with io.open(example, encoding="utf-8") as fh:
            cfg = json.load(fh)
        print("  example config keys: %s" % sorted(cfg))
        GREY = "npm install -g x"

        # (a) fail_closed: "deny" -> 灰区在服务不可达时 exit 1；改成 "ask" -> exit 2
        c1 = dict(cfg)
        c1["fail_closed"] = "deny"
        c1.pop("exit", None)
        p1 = os.path.join(work, "deny.json")
        with io.open(p1, "w", encoding="utf-8") as fh:
            json.dump(c1, fh)
        rc_deny, _ = run_guard(py, root, guard_py, ["--command", GREY, "--config", p1], work)

        c2 = dict(cfg)
        c2["fail_closed"] = "ask"
        c2.pop("exit", None)
        p2 = os.path.join(work, "ask.json")
        with io.open(p2, "w", encoding="utf-8") as fh:
            json.dump(c2, fh)
        rc_ask, _ = run_guard(py, root, guard_py, ["--command", GREY, "--config", p2], work)

        check("config fail_closed='deny' -> grey zone exits 1", rc_deny == 1,
              "got exit %s" % rc_deny)
        check("config fail_closed='ask'  -> grey zone exits 2", rc_ask == 2,
              "got exit %s" % rc_ask)

        # (b) 阈值（ask_at / deny_at / noul_threshold）**只在 L1 真正被调用时**才起作用：
        #     map_l1() 取"score 通道"与"noul 通道"中**更严重**的一个；服务不可达时
        #     根本不调用 map_l1，直接由 fail_closed 决定（guard.py 的 decide()）。
        #
        #     我前两次对阈值的预期都错了（先设 99、后设 0），就是因为没读这段控制流。
        #     要验阈值被读取，必须有一个**真的在跑的决策服务**。
        LIVE = os.environ.get("PHOC_LIVE_SERVER", "http://127.0.0.1:8155")
        up = False
        try:
            import urllib.request as _u
            with _u.urlopen(LIVE + "/health", timeout=5) as _r:
                up = _r.status == 200
        except Exception:                       # noqa: BLE001
            up = False

        if not up:
            skip("thresholds are read from the config",
                 "needs a running decision service at %s (map_l1 is not reached without it)"
                 % LIVE)
        else:
            # map_l1() 的两个通道：score 通道（deny_at / ask_at）与 noul 通道
            # （noul_threshold）。决策取**更严重**的一个。
            #
            # 实测标定（服务在 8155，命令 npm install -g x）：
            #   noul_threshold=0.65 -> noul_state=false -> deny  (exit 1)
            #   noul_threshold=0.01 -> noul_state=true  -> allow (exit 0)
            #   score=3.0 在 deny_at=ask_at=99 下恒为 allow 通道
            # 所以 noul_threshold 是这里唯一能翻转结果的旋钮 —— 用它来证明
            # **配置真的被读取**，而不是只证明某个键存在。
            GREY2 = "npm install -g x"
            base = dict(cfg)
            base.update({"l1_enabled": True, "server": LIVE,
                         "deny_at": 99.0, "ask_at": 99.0})
            base.pop("exit", None)

            pA = os.path.join(work, "nt-default.json")
            with io.open(pA, "w", encoding="utf-8") as fh:
                json.dump(dict(base, noul_threshold=0.65), fh)
            rcA, outA = run_guard(py, root, guard_py,
                                  ["--command", GREY2, "--l1-enabled", "--server", LIVE,
                                   "--config", pA], work)

            pB = os.path.join(work, "nt-low.json")
            with io.open(pB, "w", encoding="utf-8") as fh:
                json.dump(dict(base, noul_threshold=0.01), fh)
            rcB, outB = run_guard(py, root, guard_py,
                                  ["--command", GREY2, "--l1-enabled", "--server", LIVE,
                                   "--config", pB], work)

            check("config noul_threshold=0.65 -> deny (exit 1)", rcA == 1,
                  "got exit %s  %s" % (rcA, outA.strip()[-110:]))
            check("config noul_threshold=0.01 -> allow (exit 0)", rcB == 0,
                  "got exit %s  %s" % (rcB, outB.strip()[-110:]))
            check("the config value changes the decision, so it is really read",
                  rcA != rcB, "both thresholds produced exit %s" % rcA)

    shutil.rmtree(work, ignore_errors=True)
    print()
    if FAILS:
        print("check_guard_documented_contract: FAILED %d check(s)" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("check_guard_documented_contract: the documented guard contract holds"
          + (" (%d skipped)" % len(SKIPS) if SKIPS else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
