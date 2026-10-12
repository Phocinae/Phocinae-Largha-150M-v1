#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_readme_trees_and_images.py — README 里的"目录结构"与图片引用是否真实。

**为什么查这个**：README 常在 ``` 代码块里画一棵目录树，读者据此判断"这个包里有什么"。
树一旦过期（改了文件名、加了子目录、删了文件），它不会报错，只会**慢慢说谎**。
图片同理：`<img src="docs/assets/x.png">` 指向不存在的文件时，GitHub 上就是一个破图。

判据（都是可判定的）：

  1. 从每个 README 的 ``` 代码块里抽出**看起来像文件名**的条目
     （有扩展名，或在 `├──`/`└──`/`│` 这类树形符号后面）
  2. 逐个检查该文件在**仓库检出**里是否存在
  3. 从 README 的 `<img src=...>` / `![](...)` 里抽图片路径，同样检查
     （外链 http(s) 跳过，只查仓内相对路径）
  4. 跳过明显是**示意**的行（带 `...`、`<name>`、`your-`、`/path/to`）

输出区分 FAIL（树里列了但文件不存在）与 NOTE（无法判定）。
"""
import io
import os
import re
import sys

REPOS = {
    "phocinae-guard": r"D:\Projects\phociane-project\_work\repos\phocinae-guard",
    "phocinae-mcp": r"D:\Projects\phociane-project\_work\repos\phocinae-mcp",
    "phocinae-server": r"D:\Projects\phociane-project\_work\repos\phocinae-server",
    "phocinae-cli": r"D:\Projects\phociane-project\_work\staging\phocinae-cli",
    "dsh-phocinae": r"D:\Projects\phociane-project\_work\repos\dsh-phocinae",
    "codebuddy-phocinae": r"D:\Projects\phociane-project\_work\repos\codebuddy-phocinae",
    "workbuddy-phocinae": r"D:\Projects\phociane-project\_work\repos\workbuddy-phocinae",
}

FAILS = []
NOTES = []

# 明显是示意/占位的行，不判
PLACEHOLDER = re.compile(
    r"(\.\.\.|<[^>]+>|your[-_]|/path/to|path/to|\bexample\b|xxx|\bN\b|"
    r"^\s*#|\bTODO\b|\.\.\./|\bname\b\s*$)", re.I)



# Extensions that can plausibly name a file in a project tree. A bare
# `\.[A-Za-z0-9]{1,6}` also matches version numbers, IP addresses, licence identifiers
# and timings — it produced twenty-four false alarms on the first run.
FILE_EXT = (
    "py", "pyi", "mjs", "cjs", "js", "ts", "tsx", "jsx", "json", "jsonl", "yml", "yaml",
    "toml", "cfg", "ini", "txt", "md", "rst", "sh", "bash", "ps1", "bat", "cmd",
    "png", "jpg", "jpeg", "gif", "svg", "webp", "ico", "css", "html", "htm",
    "lock", "example", "conf", "sql", "csv", "whl", "tgz", "gz", "zip", "d.ts",
)
# `(?<![\w.])` on the left: without it the pattern starts matching in the middle of
# a longer name — `guard_bridge.py` yielded `guard.py`, a file that does not exist,
# and the audit then reported it as missing from the tree.
FILE_RE = re.compile(r"(?<![\w.])([A-Za-z0-9_./-]+\.(%s))\b" % "|".join(FILE_EXT))


def _is_plausible_file(cand):
    """排掉"看起来像扩展名、其实是别的东西"的形态。"""
    if "://" in cand:
        return False
    if re.fullmatch(r"\d+(\.\d+)+", cand):          # 0.35 / 2.0 / 0.1.0
        return False
    if re.fullmatch(r"[\d.]+", cand):                  # 127.0.0.1
        return False
    if re.match(r"^[A-Za-z]+-\d", cand):               # Apache-2.0
        return False
    ext = cand.rsplit(".", 1)[-1]
    if ext.isdigit():
        return False
    # `21.0ms`：扩展名以数字开头
    if re.match(r"^\d", ext):
        return False
    return True



def _is_external_reference(line, repo_name, all_repos):
    """这一行讲的是**别的包**里的文件吗？

    用"行内是否出现另一个已知包名"来判定 —— 可判定，不需要语义理解。
    """
    for other in all_repos:
        if other != repo_name and other in line:
            return True
    return False


def tree_entries(readme, repo_name):
    """从 ``` 块里的树形条目抽出候选文件路径。"""
    out = []
    in_block = False
    for raw in readme.split("\n"):
        s = raw.rstrip()
        if s.strip().startswith("```"):
            in_block = not in_block
            continue
        if not in_block:
            continue
        if PLACEHOLDER.search(s):
            continue
        # **只取紧跟树形符号的那个名字。**
        # 一行里其余部分都是注释，注释里可能提到别的文件（`guard_bridge.py` 那行的注释
        # 就写着 `guard.py`），把它当成条目会报出并不存在的"缺失文件"。
        # 顶层条目（`phocinae-guard/`、`README.md`）没有树形符号，只在行首无缩进时取。
        m = re.match(r"^[\s│|]*[├└]──\s+(\S+)", s)
        if not m:
            m = re.match(r"^(\S+)\s*(#.*)?$", s)      # 顶层裸条目
        if not m:
            continue
        token = m.group(1)
        fm = FILE_RE.match(token)                       # 必须是**整个 token**
        if not fm:
            continue
        cand = fm.group(1)
        if cand.startswith("./"):
            cand = cand[2:]
        if not _is_plausible_file(cand):
            continue
        out.append((cand, s))
    return out


def image_refs(readme):
    """README 里引用的仓内图片。"""
    out = []
    for m in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\']', readme, re.I):
        out.append(m.group(1))
    for m in re.finditer(r"!\[[^\]]*\]\(([^)\s]+)", readme):
        out.append(m.group(1))
    return [u for u in out if "://" not in u and not u.startswith("data:")]


def main():
    for name, repo in REPOS.items():
        print("=" * 72)
        print(name)
        if not os.path.isdir(repo):
            NOTES.append("%s: checkout missing" % name)
            print("  NOTE checkout missing")
            continue
        readme = ""
        for cand in ("README.md", "README.zh.md", "README_CN.md", "README_zh.md"):
            p = os.path.join(repo, cand)
            if os.path.isfile(p):
                with io.open(p, encoding="utf-8") as fh:
                    readme += fh.read() + "\n"
        if not readme:
            NOTES.append("%s: no README found" % name)
            print("  NOTE no README found")
            continue

        raw_entries = tree_entries(readme, repo_name=name)
        external = sorted({c for c, ln in raw_entries
                           if _is_external_reference(ln, name, REPOS)})
        entries = sorted({c for c, _ in raw_entries} - set(external))
        if external:
            print("  [skip] %s — belongs to another package (referenced, not shipped)"
                  % ", ".join(external))
        missing = []
        for e in entries:
            if os.path.exists(os.path.join(repo, e.replace("/", os.sep))):
                continue
            # 也接受"在某个子目录下存在同名文件"（树里常省略中间层级）
            base = os.path.basename(e)
            found = False
            for dp, dn, fn in os.walk(repo):
                if ".git" in dp or "node_modules" in dp:
                    continue
                if base in fn or base in dn:
                    found = True
                    break
            if not found:
                missing.append(e)
        print("  tree entries checked: %d" % len(entries))
        if entries:
            print("    %s" % ", ".join(entries[:8]) + (" ..." if len(entries) > 8 else ""))
        if missing:
            for m in missing:
                print("  FAIL tree lists %s but it is not in the repo" % m)
                FAILS.append("%s: README tree lists %s, missing" % (name, m))
        else:
            print("  PASS every file named in the tree exists")

        imgs = sorted(set(image_refs(readme)))
        if not imgs:
            NOTES.append("%s: no in-repo image references" % name)
            print("  NOTE no in-repo image references")
        else:
            bad = [u for u in imgs
                   if not os.path.exists(os.path.join(repo, u.replace("/", os.sep)))]
            print("  images referenced: %d" % len(imgs))
            if bad:
                for b in bad:
                    print("  FAIL image %s does not exist" % b)
                    FAILS.append("%s: README image %s is missing" % (name, b))
            else:
                print("  PASS every referenced image exists")

    print()
    for n in NOTES:
        print("  note %s" % n)
    print()
    if FAILS:
        print("audit_readme_trees_and_images: FAILED %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("audit_readme_trees_and_images: the documented trees and images match the repos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
