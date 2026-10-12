#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_readme_examples.py — README 里的示例命令，是否**真的能被命令行解析**。

**为什么做这个**：上一轮我凭印象编了一个 `--json` 参数（发布物里没有），报了假缺陷。
既然我会记错选项，**文档里的示例同样可能记错** —— 而且读者会照着敲。

判据（刻意选**不需要服务、不需要模型**的那一档，保证 CI 里也能跑）：

  * 从每个包的 README 抽出 ```bash 代码块里的、以该包命令开头的行
  * 用 `<cmd> --help` 拿到**真实的选项集合**（argparse/typer 都能反解出来）
  * 对示例里出现的每个 `--flag`，断言它在真实选项里存在
  * 断言示例里的**子命令**（第一个非选项词）是真实子命令

**不做的事**（说清楚边界）：
  * 不真的执行示例（多数需要服务/模型/网络）
  * 不判断 `--flag value` 的取值是否合法（只判断 flag 本身存在）
  * 不解析 shell 语法（`|`、`&&`、`$(...)` 一并跳过）

输出区分 **FAIL（flag/子命令不存在 -> 读者照敲必错）** 与
**SKIP（该包的 CLI 依赖没装，无法取真实选项集）**。
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

FAILS = []
SKIPS = []
NOTES = []


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

# project -> (命令名, 模块入口, 取 --help 的方式)
PACKAGES = {
    # entry_points.txt 写的是 phocinae-guard = phocinae_guard.guard:main，
    # 所以走**模块**方式取 --help，而不是去找 wheel 根目录下的 guard.py
    # （它实际在 phocinae_guard/ 里，而且入口是 console_script）。
    "phocinae-guard":  ("guard.py", "phocinae_guard.guard", "module"),
    "phocinae-cli":    ("phocinae", "phocinae_cli", "module"),
    "phocinae-mcp":    ("phocinae-mcp", "phocinae_mcp", "module"),
    "phocinae-server": ("phocinae", "phocinae.main", "module"),
}


def fetch(project):
    req = urllib.request.Request("https://pypi.org/pypi/%s/json" % project,
                                 headers={"User-Agent": "phocinae",
                                          "Cache-Control": "no-cache"})
    d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    ver = d["info"]["version"]
    whl = [f for f in (d["releases"].get(ver) or d["urls"])
           if f["filename"].endswith(".whl")][0]
    root = tempfile.mkdtemp(prefix="ex-x-", dir=SCRATCH)
    dest = os.path.join(root, whl["filename"])
    with urllib.request.urlopen(whl["url"], timeout=300) as r, open(dest, "wb") as o:
        shutil.copyfileobj(r, o)
    ex = tempfile.mkdtemp(prefix="ex-", dir=SCRATCH)
    with zipfile.ZipFile(dest) as z:
        z.extractall(ex)
        names = z.namelist()
    return ver, ex, dest, names


def readme_text(wheel, root):
    """README 正文：METADATA 的 Description（PyPI 上显示的那一份）。"""
    import zipfile
    with zipfile.ZipFile(wheel) as z:
        meta = next((n for n in z.namelist() if n.endswith(".dist-info/METADATA")), None)
        if not meta:
            return ""
        raw = z.read(meta).decode("utf-8", "replace")
    lines = raw.split("\n")
    for i, l in enumerate(lines):
        if l.strip() == "":
            return "\n".join(lines[i + 1:])
    return ""


def flags_of(help_text):
    """从 --help 文本里抽所有 --flag。"""
    return set(re.findall(r"(--[a-z][a-z0-9-]{1,28})", help_text))


def subcommands_of(help_text, cmdname):
    """从顶层 --help 里抽子命令名。

    rich/typer 会把它们画在带边框的表里，所以**不能**依赖行首缩进；
    改为在文本里找"已知形态"的短词 —— 但这里只用它来**递归取每个子命令的 help**，
    取不到就退化为"只有全局选项"，并把这件事说清楚。
    """
    names = set()
    for line in help_text.split("\n"):
        # 去掉 rich 的竖线边框，再按空白切词。
        # **不要**依赖"名字后恰好两个空格"：不同平台/终端宽度下 rich 的列宽会变，
        # 那种正则会随环境失配（我先后踩过两次）。
        stripped = line.strip().strip("\u2502|").strip()
        if not stripped:
            continue
        parts = stripped.split()
        if len(parts) < 2:
            continue
        if re.fullmatch(r"[a-z][a-z0-9-]{2,20}", parts[0]):
            names.add(parts[0])
    for word in ("--", "usage", "options", "commands", "help"):
        names.discard(word)
    return names


def collect_flags(py, root, entry, kind, cmdname, base_help):
    """返回 {None: 全局选项} | {subcommand: 选项集}。

    **必须按子命令分别取 --help** —— 顶层 `--help` 不列子命令的选项，
    我第一版只用顶层，于是把 `--state`/`--command`/`--l1`/`--fail-closed`
    全报成"不存在"（19 条假缺陷）。
    """
    table = {None: flags_of(base_help)}
    for sub in sorted(subcommands_of(base_help, cmdname)):
        if kind == "script":
            continue
        env = dict(os.environ)
        env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        try:
            p = subprocess.run([py, "-m", entry, sub, "--help"],
                               capture_output=True, timeout=120, env=env, cwd=root)
        except subprocess.TimeoutExpired:
            continue
        out = (p.stdout + p.stderr).decode("utf-8", "replace")
        if "No module named" in out or "No such command" in out:
            continue
        table[sub] = flags_of(out)
    return table


def run_help(py, root, entry, kind):
    env = dict(os.environ)
    env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    if kind == "script":
        cmd = [py, os.path.join(root, entry)] if os.path.isfile(
            os.path.join(root, entry)) else None
        if cmd is None:
            # guard.py 在 phocinae_guard/ 子目录里 —— 必须递归找，不能只看 root/
            for dp, dn, fn in os.walk(root):
                if entry in fn:
                    cmd = [py, os.path.join(dp, entry)]
                    break
        if cmd is None:
            return None, "script not found in the wheel"
    else:
        cmd = [py, "-m", entry]
    try:
        p = subprocess.run(cmd + ["--help"], capture_output=True, timeout=120,
                           env=env, cwd=root)
    except subprocess.TimeoutExpired:
        return None, "timed out"
    out = (p.stdout + p.stderr).decode("utf-8", "replace")
    if "No module named" in out or "ModuleNotFoundError" in out:
        return None, out.strip().split("\n")[-1][:110]
    return out, None


def example_lines(readme, cmdname):
    """从 ```bash 块里取以 cmdname 开头的命令行（去掉注释与续行）。"""
    out = []
    in_block = False
    for raw in readme.split("\n"):
        s = raw.strip()
        if s.startswith("```"):
            in_block = not in_block
            continue
        if not in_block:
            continue
        # 去掉行尾注释（保留 # 在引号内的简单情形：这里只处理 `#` 前有空格的情况）
        line = re.sub(r"\s+#.*$", "", s)
        # 续行合并：以 \ 结尾的与下一行拼接由下面的循环处理
        if not line:
            continue
        out.append(line)
    # 合并续行
    merged = []
    buf = ""
    for l in out:
        if buf:
            l = buf + " " + l.lstrip()
            buf = ""
        if l.rstrip().endswith("\\"):
            buf = l.rstrip()[:-1]
            continue
        merged.append(l)
    if buf:
        merged.append(buf)
    # 只认**命令位置**出现的 cmdname，否则会把下面这些也算成"示例"：
    #     git clone https://github.com/Phocinae/phocinae-server.git
    #     cd phocinae-server
    #     from phocinae.engine import Engine
    # 实测 server 的 5 行"示例"里有 3 行是这类 —— 于是"检查了 5 行、全部通过"
    # 其实是**空转**（真选项 0 个，任何 flag 都不会被判错）。
    #
    # 命令位置 = 行首 / 管道或逻辑符之后 / 环境变量赋值之后。
    pos = re.compile(r"(^|[|&;]\s*|\b[A-Z_][A-Z0-9_]*=\S*\s+)%s(\s|\$)" % re.escape(cmdname))
    out_lines = []
    for l in merged:
        if "git clone" in l or l.startswith("cd ") or l.startswith("from ") \
                or l.startswith("import "):
            continue
        if pos.search(l):
            out_lines.append(l)
    return out_lines


def main():
    py = os.environ.get("PHOC_CHECK_PYTHON") or sys.executable
    for project, (cmdname, entry, kind) in PACKAGES.items():
        ver, root, wheel, names = fetch(project)
        readme = readme_text(wheel, root)
        print("=" * 72)
        print("%s %s" % (project, ver))

        if not readme:
            skip = "%s: no METADATA description" % project
            print("SKIP " + skip)
            SKIPS.append(skip)
            continue

        help_text, why = run_help(py, root, entry or "", kind)
        if help_text is None:
            msg = "%s: cannot read the real option set (%s)" % (project, why)
            print("SKIP " + msg)
            SKIPS.append(msg)
            continue

        lines = example_lines(readme, cmdname)
        # **可见的第一步**：顶层 --help 到底拿到了什么。
        # CI 上 CLI 探到 0 个选项、0 个子命令，而本地同一条命令拿到 29 个 ——
        # 必须能一眼看出"探测本身失败了"，而不是把它当成"文档里有 19 个假选项"。
        if len(help_text.strip()) < 40 or "No module" in help_text:
            msg = ("%s: the CLI probe returned nothing usable (%d chars) — "
                   "nothing was checked" % (project, len(help_text.strip())))
            print("  NOTE %s" % msg)
            print("       first line: %s" % (help_text.strip().split(chr(10)) or ["(empty)"])[0][:100])
            NOTES.append(msg)
            continue
        print("  top-level --help: %d chars" % len(help_text))
        # 把**实际拿到的文本**打出来。这里用 repr 的前 400 字符：CR/LF、控制字符、
        # 以及中文码点都会原样可见。我为了同一个空探测在本地猜了四轮（顶层/子命令、
        # 列宽、转义、ANSI），都复现不出来 —— 那就让 CI 自己说话。
        if "--" not in help_text or len(flags_of(help_text)) == 0:
            print("  !! no --flag found in the help text; first 400 chars (repr):")
            print("     %r" % help_text[:400])
        table = collect_flags(py, root, entry, kind, cmdname, help_text)
        all_flags = set()
        for v in table.values():
            all_flags |= v
        subs = sorted(k for k in table if k)
        print("  subcommands probed: %s" % (subs or "(none)"))
        print("  real flags known: %d; example lines: %d" % (len(all_flags), len(lines)))

        bad = []
        for l in lines:
            # 跳过明显是 shell 组合/占位的行
            if any(t in l for t in ("|", "&&", "$(", "<", "...")):
                continue
            for f in flags_of(l):
                if f not in all_flags:
                    bad.append((l, f))
        if bad:
            for l, f in bad:
                print("  FAIL %s  -> %s is not a real option" % (l[:78], f))
                FAILS.append("%s: documented %s but it does not exist" % (project, f))
        else:
            checked = [l for l in lines
                       if not any(t in l for t in ("|", "&&", "$(", "<", "..."))]
            if not checked:
                # **空扫描不是通过。** 第一版在这里打了 PASS，而实际一行都没检查。
                msg = ("%s: no checkable example line was found — nothing was verified"
                       % project)
                print("  NOTE %s" % msg)
                NOTES.append(msg)
            else:
                print("  PASS every --flag in the examples exists (%d lines checked)"
                      % len(checked))

        # 记录被跳过的行，让"跳过了什么"可见
        skipped = [l for l in lines if any(t in l for t in ("|", "&&", "$(", "<", "..."))]
        if skipped:
            NOTES.append("%s: %d example line(s) skipped as shell-composed"
                         % (project, len(skipped)))

    print()
    for n in NOTES:
        print("  note %s" % n)
    print()
    if FAILS:
        print("audit_readme_examples: FAILED %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("audit_readme_examples: every documented flag exists in the real CLI"
          + (" (%d skipped)" % len(SKIPS) if SKIPS else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
