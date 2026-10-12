#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_package_version_consistency.py — 一个仓内**所有**声明版本的字段必须一致。

**为什么需要**：`audit_version_refs.py` 只认"文件里声称本包当前版本"的**行内**形态
（`This is **X.Y.Z**`、安装命令、默认值标注）。JSON 字段不属于这些形态：

    "version": "0.2.4"          <- server.json 顶层
    "version": "0.2.4"          <- server.json packages[0]

所以 manifest 类文件是那个检查的盲区。而 manifest 恰恰是**发布时才会被读**的东西：

  * `pyproject.toml` 的 `version` → PyPI 上的版本
  * `server.json` 的 `version` + `packages[].version` → MCP Registry 上的条目
  * `package.json` 的 `version` → npm 上的版本
  * `__init__.py` 的 `__version__` → 运行时自报的版本
  * `.claude-plugin/plugin.json` 的 `version` → CC 插件加载时读的版本

这几处只要有一处漏改，就会出现"PyPI 上是 0.2.4、Registry 上写着 0.2.3"这类
**互相矛盾的对外声明**，而两边各自都"能跑"。

本脚本只做**仓内**一致性，不需要网络：把所有权威版本字段收集起来，要求它们相等。
跨渠道是否真的同步（PyPI vs Registry vs npm）另由 `verify_published.py` 与 CI 负责。

用法：python tools/audit_package_version_consistency.py
"""
import io
import json
import os
import re
import sys

# 默认检查命令行给出的目录；不传则检查当前工作目录（CI 里就是 checkout 根）。
# 这里**不能**写死本机路径：在别处会扫不到任何仓库，然后报"全部一致"——
# 一个什么都没检查的假通过。
DEFAULT_ROOTS = ["."]
SKIP_DIRS = {".git", "node_modules", "dist", "build", "__pycache__", ".venv", "venv"}

# The verification tools download and unpack published wheels, and those unpacked packages
# carry their own `__version__`. Scanning them made this audit report that the model repo
# declares both 0.1.2 and 0.1.6 — it declares no version at all. Whatever the tools create
# has to be excluded by name, and by prefix because mkdtemp suffixes are random.
SKIP_DIRS |= {".phocinae-verify", ".phoc-scratch", ".tmp", "dist-upload",
              ".mypy_cache", ".pytest_cache", ".ruff_cache", "htmlcov"}
SKIP_PREFIXES = ("pubverify-", "pubx-", "pubaudit-", "failclosed-", "hostrefuse-",
                 "cli-contract-", "srv-api-", "srv-empty-", "srv-junk-",
                 "phocinae-verify")


def _skip_dir(name):
    return name in SKIP_DIRS or any(name.startswith(p) for p in SKIP_PREFIXES)



def read(p):
    try:
        return io.open(p, encoding="utf-8").read()
    except (OSError, UnicodeDecodeError):
        return None


def collect(repo):
    """返回 [(来源, 版本)] —— 只收"权威版本声明"，不收依赖钉版本。"""
    out = []

    p = os.path.join(repo, "pyproject.toml")
    s = read(p)
    if s:
        m = re.search(r'^version\s*=\s*"([^"]+)"', s, re.M)
        if m:
            out.append(("pyproject.toml:version", m.group(1)))
        # 依赖里的版本钉不算（不是本包版本）
        name = re.search(r'^name\s*=\s*"([^"]+)"', s, re.M)
        if name:
            out.append(("_pkgname", name.group(1)))

    p = os.path.join(repo, "package.json")
    s = read(p)
    if s:
        try:
            d = json.loads(s)
            if d.get("version"):
                out.append(("package.json:version", d["version"]))
        except ValueError:
            pass

    p = os.path.join(repo, "server.json")
    s = read(p)
    if s:
        try:
            d = json.loads(s)
            if d.get("version"):
                out.append(("server.json:version", d["version"]))
            for i, pkg in enumerate(d.get("packages") or []):
                if pkg.get("version"):
                    out.append(("server.json:packages[%d].version" % i, pkg["version"]))
        except ValueError:
            pass

    p = os.path.join(repo, ".claude-plugin", "plugin.json")
    s = read(p)
    if s:
        try:
            d = json.loads(s)
            if d.get("version"):
                out.append((".claude-plugin/plugin.json:version", d["version"]))
        except ValueError:
            pass

    # __init__.py / __main__.py 里的 __version__
    for dp, dn, fn in os.walk(repo):
        dn[:] = [d for d in dn if not _skip_dir(d)]
        for f in fn:
            if not f.endswith(".py"):
                continue
            s = read(os.path.join(dp, f))
            if not s:
                continue
            m = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', s, re.M)
            if m:
                out.append(("%s:__version__" % os.path.relpath(os.path.join(dp, f), repo),
                            m.group(1)))
    return out


# 明显的非仓库目录，不下探
NOT_A_REPO = {
    "datasets", "docs", "figures", "examples", "tools", "scripts", "tests",
    "assets", "gallery", "node_modules", "__pycache__", ".github", "dist",
    "build", ".git", "venv", ".venv",
}


def looks_like_repo(d):
    """含以下任一即视为仓库。

    模型仓没有 pyproject.toml / package.json —— 只有文档与 tools/ ——
    所以第一版把它排除掉了，却把它下面 35 个子目录当成了仓库。
    """
    if not os.path.isdir(d):
        return False
    for marker in (".git", "pyproject.toml", "package.json", "server.json",
                   "setup.py", "setup.cfg"):
        if os.path.exists(os.path.join(d, marker)):
            return True
    if os.path.isdir(os.path.join(d, "src")):
        return True
    # 顶层有 __init__.py 的包布局
    for n in os.listdir(d) if os.path.isdir(d) else []:
        if os.path.isdir(os.path.join(d, n)) and \
           os.path.isfile(os.path.join(d, n, "__init__.py")):
            return True
    return False


def find_repos(roots):
    """展开 roots：root 本身（若像仓库）+ 它的直接子目录（若像仓库）。"""
    repos = []
    for root in roots:
        if not os.path.isdir(root):
            print("  (skipping %s: not a directory)" % root)
            continue
        if looks_like_repo(root):
            repos.append(root)
        for n in sorted(os.listdir(root)):
            if n in NOT_A_REPO or n.startswith("."):
                continue
            d = os.path.join(root, n)
            if looks_like_repo(d):
                repos.append(d)
    seen, out = set(), []
    for r in repos:
        rp = os.path.abspath(r)
        if rp not in seen:
            seen.add(rp)
            out.append(r)
    return out


def main():
    roots = sys.argv[1:] or DEFAULT_ROOTS
    repos = find_repos(roots)
    if not repos:
        print("audit_package_version_consistency: FAILED - no repositories found under %s"
              % ", ".join(roots))
        print("  (a check with nothing to check must not report success)")
        return 1

    bad = []
    for repo in repos:
        items = [(k, v) for k, v in collect(repo) if not k.startswith("_")]
        if len(items) < 2:
            continue
        versions = {v for _, v in items}
        name = os.path.basename(repo)
        mark = "ok  " if len(versions) == 1 else "SPLIT"
        print("  [%s] %-26s %s" % (mark, name, sorted(versions)))
        for k, v in items:
            print("         %-42s %s" % (k, v))
        if len(versions) > 1:
            bad.append((name, items))

    print()
    if bad:
        print("audit_package_version_consistency: FAILED (%d repo(s) disagree with themselves)"
              % len(bad))
        for name, items in bad:
            print("  %s: %s" % (name, sorted({v for _, v in items})))
        return 1
    checked = sum(1 for r in repos
                  if len([1 for k, _ in collect(r) if not k.startswith("_")]) >= 2)
    if checked == 0:
        # 扫到了仓库但没有包版本字段 —— 对纯文档/工具仓这是**正常结果**。
        # 措辞必须准确：不能说"全部一致"，因为没有比较过任何东西。
        print("audit_package_version_consistency: nothing to compare")
        print("  %d repositor%s scanned, none declares a package version "
              "(a docs/tooling repo has none)" % (len(repos), "y" if len(repos) == 1 else "ies"))
        print("  this is a pass with 0 comparisons, not a verified claim")
        return 0
    print("audit_package_version_consistency: every repo declares one version everywhere"
          "  (%d repo(s) compared)" % checked)
    return 0


if __name__ == "__main__":
    sys.exit(main())
