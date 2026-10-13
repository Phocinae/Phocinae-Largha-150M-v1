#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_all.py — 一条命令跑完发布前的全部核对。

**为什么做这个**：这十几天里我修过的缺陷，几乎都属于同一类 ——
**"检查写了，但没在正确的地方跑"**：

  * 本地全绿、CI 红（Windows-only shell、缺依赖、缺 torch）
  * 检查在 `publish` job 里，而那个 job 没有 checkout
  * 检查的 glob 指向旧版本目录
  * 只读命令的顶层 `--help`，漏掉子命令选项

所以"发布前跑全套"不能靠我记得有哪些套件 —— 得有一条命令、一张表、一个退出码。

设计要点（都是为了避免**假绿**）：

  * 每个套件声明它**需要什么**（哪个解释器、哪些环境变量、哪些同级 checkout）
  * 缺依赖 -> **SKIP 并写原因**，绝不算通过；SKIP 在汇总里单独计数
  * 0 个套件真正跑过 -> **整体失败**（"什么都没验"不是成功）
  * 每个套件的**完整输出**落盘到 `<scratch>/verify_all_logs/<name>.log`，
    汇总里只给判定 —— 出问题时去看日志，而不是重跑
  * 一次跑完所有套件（不提前退出），这样一轮就能看到**全部**问题

解释器：本机没有哪个 venv 同时装得下 typer 与 torch，所以两个键：
`cli` -> 跑 CLI/文档类套件；`server` -> 跑需要 fastapi/torch 的套件。
可用 `--cli-python` / `--server-python` 覆盖。
"""
import argparse
import io
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                       # 模型仓根
# Our scratch tree, where the sibling checkouts and the shared tools live. Configurable so
# this file is not tied to one machine's layout: on a runner PHOC_WORK can point at the
# directory holding whatever checkouts that job made available.
def _locate_work():
    """The directory holding the sibling checkouts.

    `PHOC_WORK` if set, else walk up looking for one that contains both `repos/` and
    `staging/`, else this repository's parent (the shape a CI job has when it checks the
    repositories out side by side). A default that only makes sense on the machine where it
    was written is a latent failure everywhere else.
    """
    env = os.environ.get("PHOC_WORK")
    if env and os.path.isdir(env):
        return env
    d = HERE
    for _ in range(6):
        if os.path.isdir(os.path.join(d, "repos")) and \
                os.path.isdir(os.path.join(d, "staging")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return os.path.dirname(ROOT)


WORK = _locate_work()
REPOS = os.path.join(WORK, "repos")
STAGING = os.path.join(WORK, "staging")

def _pick_python(preferred, role):
    """选解释器：显式 env > 本机 venv（存在才用）> 当前解释器。

    On a runner the workflow sets PHOC_CLI_PYTHON/PHOC_SERVER_PYTHON. When it does not — a
    shell that loses the step env, or a plain checkout — falling back to this machine's
    virtualenv paths produces twelve "interpreter not found" skips and a confusing failure.
    Falling back to the interpreter that is running this file is the sane default: it is by
    definition present, and on CI it is the one the workflow just installed into.
    """
    explicit = os.environ.get("PHOC_" + role.upper() + "_PYTHON")
    if explicit:
        return explicit
    if os.path.isfile(preferred):
        return preferred
    return sys.executable


DEFAULT_CLI_PY = _pick_python(
    os.path.join(WORK, "verify-cli", "Scripts", "python.exe"), "cli")
DEFAULT_SRV_PY = _pick_python(
    os.path.join(WORK, "srvvenv", "Scripts", "python.exe"), "server")

# ---------------------------------------------------------------------------
# 套件表。字段：
#   script  : 相对模型仓的路径
#   py      : "cli" | "server"（选用哪个解释器）
#   args    : 额外参数
#   env     : 额外环境变量
#   needs   : 需要存在的路径；缺了记 SKIP（而不是 FAIL）
#   why     : 这个套件在验什么（写进汇总，便于判断"没跑"意味着什么）
# ---------------------------------------------------------------------------
SUITES = [
    dict(name="published-artifacts", py="server", script="tools/verify_published.py",
         args=lambda A: ["--python", A.server_python],
         env={"PHOC_SCREEN_DOCS": os.path.join(STAGING, "dsh-phocinae-screen", "docs"),
              "PHOC_GUARD_REPO": os.path.join(REPOS, "phocinae-guard")},
         needs=[os.path.join(REPOS, "phocinae-guard")],
         why="已发布的 wheel 装出来是否真能用（这一条抓到过三个只在发布物里存在的缺陷）"),

    dict(name="guard-contract", py="server",
         script="tools/check_guard_documented_contract.py",
         env={"PHOC_GUARD_REPO": os.path.join(REPOS, "phocinae-guard")},
         needs=[os.path.join(REPOS, "phocinae-guard", "guard.conf.example.json")],
         why="guard 的退出码契约与两条不变式"),

    dict(name="cli-contract", py="cli",
         script="tools/check_cli_documented_contract.py",
         why="CLI 的退出码契约（allow 0 / deny 2 / ask 3 / fail-closed）"),

    dict(name="server-api", py="server",
         script="tools/check_server_documented_api.py",
         why="服务端五个端点与错误码（无权重时验启动诊断）"),

    dict(name="mcp-host-contract", py="server",
         script="tools/check_mcp_host_refusal.py",
         why="MCP 的 --host 契约（::1 曾经一直坏着）"),

    dict(name="mcp-schemas-vs-docs", py="server",
         script="tools/audit_mcp_tool_schemas_vs_docs.py",
         why="MCP 工具 schema 与 README 工具表是否逐字段一致"),

    dict(name="published-npm-js", py="server",
         script="tools/verify_published_npm_js.py",
         why="从 npm 下载已发布的 @phocinae/js，检查入口齐全且能被 Node require()"),

    dict(name="published-js-l0-parity", py="server",
         script="tools/verify_published_js_l0_parity.py",
         why="已发布的 JS 包里 L0 三张表是否与 guard 逐条一致（手抄表出过两次事故）"),

    dict(name="readme-examples", py="cli",
         script="tools/audit_readme_examples.py",
         why="四个包 README 示例里的每个 --flag 是否真实存在"),

    dict(name="readme-trees-and-images", py="server",
         script="tools/audit_readme_trees_and_images.py",
         needs=[os.path.join(REPOS, "phocinae-guard"),
                os.path.join(REPOS, "phocinae-mcp"),
                os.path.join(REPOS, "phocinae-server"),
                os.path.join(STAGING, "phocinae-cli")],
         why="README 画的目录树与图片引用是否与仓库一致（抓到过一条跑不通的自测命令）"),

    dict(name="l0-count-claims", py="server",
         script="tools/audit_l0_count_claims.py",
         needs=[os.path.join(REPOS, "phocinae-guard", "l0_table.json")],
         why="README 里 L0 表的条数是否等于实际（曾有两份文档对同一张表说法不一致）"),

    dict(name="published-version-sites", py="server",
         script="tools/check_published_wheel_version_sites.py",
         why="已发布的 wheel 里每个版本常量是否都等于它自己的版本（0.1.6 曾报成 0.1.5）"),

    dict(name="gallery-coverage", py="server",
         script="tools/audit_gallery_coverage.py",
         env={"PHOC_SCREEN_DOCS": os.path.join(STAGING, "dsh-phocinae-screen", "docs"),
              "PHOC_GUARD_REPO": os.path.join(REPOS, "phocinae-guard")},
         # The gallery evidence table lives in the harness repo and refers to the guard
         # checkout. Where those are absent the audit must not be asked to run at all —
         # pointing PHOC_SCREEN_DOCS at a path that does not exist turns a "cannot check"
         # into a failure, which is exactly the confusion this runner is meant to remove.
         needs=[os.path.join(REPOS, "phocinae-guard"),
                os.path.join(STAGING, "dsh-phocinae-screen", "docs")],
         why="27 个演示 -> 插件覆盖（shipped/measured/unmeasured）"),

    dict(name="bilingual-sync", py="server", script="tools/audit_bilingual_sync.py",
         why="成对 README 是否漂移"),

    dict(name="version-consistency", py="server",
         script="tools/audit_package_version_consistency.py",
         args=lambda A: [REPOS, STAGING],
         needs=[REPOS, STAGING],
         why="每个仓在所有清单里是否只声明一个版本"),

    dict(name="plugin-manifests", py="server",
         script="tools/audit_plugin_manifests.py",
         needs=[os.path.join(REPOS, "dsh-phocinae"),
                os.path.join(REPOS, "codebuddy-phocinae"),
                os.path.join(REPOS, "workbuddy-phocinae")],
         why="三个插件仓的清单/版本/入口文件与 README 声称"),

    dict(name="tool-server-override", py="server",
         script=os.path.join(WORK, "tools", "verify_tool_server_override.py"),
         in_work=True,
         needs=[os.path.join(WORK, "tools", "verify_tool_server_override.py")],
         why="四个 MCP 工具是否都接受每次调用的 server 覆盖"),
]


def run_one(A, spec):
    name = spec["name"]
    py = A.cli_python if spec["py"] == "cli" else A.server_python
    script = spec["script"]
    if not spec.get("in_work"):
        script = os.path.join(ROOT, script)

    if not os.path.isfile(script):
        return "SKIP", "script not found: %s" % script, ""
    if not os.path.isfile(py):
        return "SKIP", "interpreter not found: %s" % py, ""
    for need in spec.get("needs", []):
        if not os.path.exists(need):
            return "SKIP", "missing checkout/file: %s" % need, ""

    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PHOC_CHECK_PYTHON"] = py
    env["PHOC_SCRATCH"] = A.scratch
    env.update(spec.get("env") or {})
    args = spec.get("args")
    cmd = [py, script] + (args(A) if callable(args) else list(args or []))

    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=A.timeout,
                           env=env, cwd=ROOT)
    except subprocess.TimeoutExpired:
        return "FAIL", "timed out after %ds" % A.timeout, ""
    out = (p.stdout + p.stderr).decode("utf-8", "replace")
    secs = time.time() - t0

    verdict = "PASS" if p.returncode == 0 else "FAIL"
    detail = "exit %d, %.1fs" % (p.returncode, secs)
    # A suite may decline to run because its environment is missing; it says so and exits 0.
    # Only the suite-level phrasing counts. Matching the bare words "nothing was verified"
    # also caught a per-package NOTE from audit_readme_examples, where two packages were
    # checked and two had no checkable example — that is a partial result, not a skip.
    if p.returncode == 0 and (
            "nothing was verified (this is a SKIP" in out
            or out.lstrip().startswith("SKIP ")):
        verdict = "SKIP"
        detail = "the suite declined to run (environment), see the log"
    return verdict, detail, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cli-python", default=os.environ.get("PHOC_CLI_PYTHON")
                    or DEFAULT_CLI_PY)
    ap.add_argument("--server-python", default=os.environ.get("PHOC_SERVER_PYTHON")
                    or DEFAULT_SRV_PY)
    ap.add_argument("--scratch", default=os.environ.get("PHOC_SCRATCH")
                    or os.path.join(WORK, ".tmp"))
    ap.add_argument("--timeout", type=int, default=2400)
    ap.add_argument("--model-dir", default=os.environ.get("PHOC_MODEL_DIR", ""),
                    help="豁免需要模型权重的检查；不设则它们 SKIP 并说明原因")
    ap.add_argument("--only", default="", help="逗号分隔的套件名")
    A = ap.parse_args()

    # 权重目录：设了就让需要模型的检查真的跑起来（本机有；CI 没有）。
    if A.model_dir:
        os.environ["PHOC_MODEL_DIR"] = A.model_dir

    os.makedirs(A.scratch, exist_ok=True)
    logdir = os.path.join(A.scratch, "verify_all_logs")
    os.makedirs(logdir, exist_ok=True)

    wanted = [s.strip() for s in A.only.split(",") if s.strip()]
    suites = [s for s in SUITES if not wanted or s["name"] in wanted]

    print("verify_all: %d suite(s)" % len(suites))
    print("  cli interpreter    : %s" % A.cli_python)
    print("  server interpreter : %s" % A.server_python)
    print("  logs               : %s" % logdir)
    print()

    results = []
    for spec in suites:
        v, detail, out = run_one(A, spec)
        logp = os.path.join(logdir, spec["name"] + ".log")
        with io.open(logp, "w", encoding="utf-8") as fh:
            fh.write(out or "(no output)\n")
        results.append((spec, v, detail))
        print("  %-4s %-24s %s" % (v, spec["name"], detail))
        if v == "SKIP":
            print("       why this suite matters: %s" % spec["why"])

    n_pass = sum(1 for _, v, _ in results if v == "PASS")
    n_fail = sum(1 for _, v, _ in results if v == "FAIL")
    n_skip = sum(1 for _, v, _ in results if v == "SKIP")

    print()
    print("=== summary ===")
    print("  PASS %d   FAIL %d   SKIP %d   (of %d)"
          % (n_pass, n_fail, n_skip, len(results)))
    for spec, v, detail in results:
        if v != "PASS":
            print("  %-4s %-24s %s" % (v, spec["name"], detail))

    if n_fail:
        print()
        print("verify_all: FAILED — see %s" % logdir)
        return 1
    if n_pass == 0:
        # "什么都没跑"不是成功。
        print()
        print("verify_all: FAILED — no suite actually ran; this is not a pass")
        return 1
    print()
    print("verify_all: all %d suite(s) that could run have passed" % n_pass)
    return 0


if __name__ == "__main__":
    sys.exit(main())
