#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_doc_claims_have_tests.py — 文档里承诺的行为，是否有测试真的验过它。

**为什么做这个**：这一轮已经证明"green where it was checked, broken where it was not"
是本项目的主要失效模式（Windows-only 的 shell、插件清单从未进 CI、wheel 内容从未被打开）。
所以"文档承诺"与"测试覆盖"之间的空隙值得单独量一次。

做法（刻意只做**可判定**的抽取，不做语义理解）：

  1. **退出码契约**：README 里写了 `exit 0` / `exit 1` / `exit 2` 的地方，
     测试文件里是否也出现同样的断言数字。
  2. **工具名**：MCP README 列出的工具名，测试是否逐个调用过。
  3. **CLI 子命令**：README 里的子命令，测试是否逐个执行过。
  4. **环境变量**：README 提到的开关，测试是否出现过。

抽取不到的**不报**（宁可漏，不可误报 —— 本轮已经因为误报浪费过时间）。
用法：python tools/audit_doc_claims_have_tests.py
"""
import io
import os
import re
import sys

# 默认检查命令行给出的目录；不传则扫当前目录（CI 里各仓通常 checkout 在同一层）。
# **不能写死本机路径** —— 在别处会一个仓库都找不到，然后报"每一条都有测试"。
DEFAULT_ROOTS = ["."]

# 只审计"有文档 + 有测试"的已发布包
TARGETS = ["phocinae-guard", "phocinae-mcp", "phocinae-cli", "phocinae-server"]


def read(p):
    try:
        with io.open(p, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return ""


def test_text(repo):
    """所有测试与 CI 配置的合并文本 —— 断言可能写在 workflow 里。"""
    out = []
    for dp, dn, fn in os.walk(repo):
        dn[:] = [d for d in dn if d not in (".git", "node_modules", "__pycache__", "dist",
                                            "dist-upload", "build")]
        for f in fn:
            if f.endswith((".py", ".mjs", ".js", ".sh", ".ps1")) or "workflow" in dp:
                out.append(read(os.path.join(dp, f)))
    return "\n".join(out)


def docs_text(repo):
    return "\n".join(read(os.path.join(repo, n))
                     for n in ("README.md", "README.zh.md", "SKILL.md"))


def main():
    roots = sys.argv[1:] or DEFAULT_ROOTS
    problems = []
    found_any = False
    claims_checked = 0
    for name in TARGETS:
        repo = next((os.path.join(r, name) for r in roots
                     if os.path.isdir(os.path.join(r, name))), None)
        if not repo:
            # 也允许 root 本身就是那个仓库
            repo = next((r for r in roots
                         if os.path.basename(os.path.abspath(r)) == name), None)
        if not repo:
            continue
        found_any = True
        print("### %s" % name)
        doc, tests = docs_text(repo), test_text(repo)
        claims_checked += 4

        # 1) 退出码契约
        codes = sorted(set(re.findall(r"exit\s+([0-3])\b", doc)))
        for c in codes:
            # 测试里应当出现该数字（作为断言的一部分）
            hit = re.search(r"returncode\s*[=!]=\s*%s|exit\s+%s\b|\brc\s*[=!]=\s*%s|"
                            r"-eq\s+%s\b" % (c, c, c, c), tests)
            mark = "ok  " if hit else "MISS"
            print("  [%s] documents exit %s" % (mark, c))
            if not hit:
                problems.append("%s: documents 'exit %s' but no test asserts it" % (name, c))

        # 2) MCP 工具名（只对 mcp 生效）
        if name == "phocinae-mcp":
            tools = sorted(set(re.findall(r"`(gate|classify|route|score)`", doc)))
            for t in tools:
                hit = ('"' + t + '"') in tests or ("'" + t + "'") in tests
                print("  [%s] documents tool %-9s used in tests" % ("ok  " if hit else "MISS", t))
                if not hit:
                    problems.append("%s: documents tool %r but tests never call it" % (name, t))

        # 3) CLI 子命令
        if name == "phocinae-cli":
            subs = sorted(set(re.findall(r"phocinae\s+(check|batch|serve|gate|version)\b", doc)))
            for s in subs:
                hit = re.search(r"%s\b" % s, tests)
                print("  [%s] documents subcommand %-8s appears in tests"
                      % ("ok  " if hit else "MISS", s))
                if not hit:
                    problems.append("%s: documents subcommand %r but tests never run it" % (name, s))

        # 4) 环境变量开关
        envs = sorted(set(re.findall(r"`(PHOCINAE_[A-Z_]+|PHOC_[A-Z_]+)`", doc)))
        for e in envs:
            hit = e in tests
            print("  [%s] documents env %-32s appears in tests" % ("ok  " if hit else "MISS", e))
            if not hit:
                problems.append("%s: documents %s but no test sets it" % (name, e))
        print()

    print("=== summary ===")
    if not found_any:
        print("  FAILED - no target repositories found under: %s" % ", ".join(roots))
        print("  (a check with nothing to check must not report success)")
        return 1
    if not problems:
        print("  every documented claim has a test, across %d repo(s)" % claims_checked // 4
              if False else
              "  every documented claim has a test")
        print("  claim categories examined: %d across the found repositories"
              % claims_checked)
        return 0
    for p in problems:
        print("  - %s" % p)
    print("\naudit_doc_claims_have_tests: %d gap(s) between the docs and the tests"
          % len(problems))
    return 1


if __name__ == "__main__":
    sys.exit(main())
