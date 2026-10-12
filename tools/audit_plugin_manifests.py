#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_plugin_manifests.py — 三个插件仓的清单与 README 声称是否自洽。

**已经确认的一处**：`workbuddy-phocinae/README.md` 第 123 行写

    "本仓库**未提交** WorkBuddy 开放平台审核、**未上架**连接器市场、
     **未推送**任何远程仓库（本地 git 无 remote）"

而实测 `git remote -v` 是 `https://github.com/Phocinae/workbuddy-phocinae.git`，
分支 main、3 个提交、CI 也在跑。**"未推送任何远程仓库"这句话是错的** ——
只有"未提交审核 / 未上架"那两句仍然成立。

这类"曾经为真、后来变了"的声称最难发现，因为它读起来完全合理。

本脚本检查（都是**可判定**的）：

  1. 清单文件的**版本号**在各处是否一致（package.json / plugin.json /
     connector-meta.json / marketplace.json）
  2. 清单里的**入口文件**是否真的存在（args 指向的脚本、mcp 的 command）
  3. README 里"未推送 / 无 remote / 未发布"这类声称，与**实际 git remote** 是否矛盾
  4. 清单声明的 MCP 工具名，是否在对应脚本里实现
"""
import io
import json
import os
import re
import subprocess
import sys

REPOS = {
    "dsh-phocinae": r"D:\Projects\phociane-project\_work\repos\dsh-phocinae",
    "codebuddy-phocinae": r"D:\Projects\phociane-project\_work\repos\codebuddy-phocinae",
    "workbuddy-phocinae": r"D:\Projects\phociane-project\_work\repos\workbuddy-phocinae",
}

FAILS = []
NOTES = []


def check(name, cond, detail=""):
    print(("  PASS " if cond else "  FAIL ") + name + ("" if cond else "  " + str(detail)))
    if not cond:
        FAILS.append(name)


def note(msg):
    print("  NOTE %s" % msg)
    NOTES.append(msg)


def read_json(p):
    try:
        with io.open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def versions_in(repo):
    """从各清单里收集 (文件:键, 版本)。"""
    out = []
    pj = read_json(os.path.join(repo, "package.json"))
    if pj and pj.get("version"):
        out.append(("package.json:version", pj["version"]))
    for rel in (".codebuddy-plugin/plugin.json", ".codebuddy-plugin/marketplace.json",
                "connector-meta.json", "token-schema.json"):
        d = read_json(os.path.join(repo, rel))
        if isinstance(d, dict) and d.get("version"):
            out.append(("%s:version" % rel, d["version"]))
        if isinstance(d, dict) and isinstance(d.get("plugins"), list):
            for i, pl in enumerate(d["plugins"]):
                if isinstance(pl, dict) and pl.get("version"):
                    out.append(("%s:plugins[%d].version" % (rel, i), pl["version"]))
    return out


def remote_of(repo):
    p = subprocess.run(["git", "remote", "-v"], cwd=repo, capture_output=True)
    return p.stdout.decode("utf-8", "replace").strip()


def main():
    for name, repo in REPOS.items():
        print("=" * 72)
        print(name)
        if not os.path.isdir(repo):
            note("%s: checkout missing" % name)
            continue

        # ---- 1) 版本一致性 ----
        vs = versions_in(repo)
        uniq = sorted({v for _, v in vs})
        print("  declared versions: %s" % (vs or "(none)"))
        if not vs:
            note("%s: no version declared anywhere" % name)
        elif len(uniq) == 1:
            check("%s: one version everywhere (%s)" % (name, uniq[0]), True)
        else:
            check("%s: one version everywhere" % name, False, "found %s" % uniq)

        # ---- 2) 清单里的入口文件真的存在 ----
        mcp = read_json(os.path.join(repo, "mcp.json")) or read_json(
            os.path.join(repo, ".mcp.json"))
        if isinstance(mcp, dict):
            for srv, cfg in (mcp.get("mcpServers") or {}).items():
                for a in (cfg.get("args") or []):
                    if not isinstance(a, str):
                        continue
                    # 只有**看起来是仓库内路径**的参数才检查存在性。
                    # 第一版把 `http://127.0.0.1:8155` 也拿去 os.path.exists，
                    # 报了一条"文件不存在"的假警 —— 它是个 URL。
                    looks_like_path = (
                        "://" not in a
                        and not a.startswith("-")
                        and ("/" in a or "\\" in a)
                        and not a.endswith(":")            # 形如 C: 的盘符不算
                    )
                    if looks_like_path:
                        exists = os.path.exists(os.path.join(repo, a))
                        check("%s: mcp server %r arg %r exists" % (name, srv, a), exists,
                              "not found relative to the repo root")
                    else:
                        print("  [skip] arg %r is not a repo path (option/URL/module)" % a)
        else:
            note("%s: no mcp.json / .mcp.json" % name)

        # ---- 3) "未推送 / 无 remote" 这类声称 vs 实际 ----
        rem = remote_of(repo)
        has_remote = bool(rem)
        readme = ""
        for cand in ("README.md", "README.zh.md", "README_CN.md"):
            p = os.path.join(repo, cand)
            if os.path.isfile(p):
                with io.open(p, encoding="utf-8") as fh:
                    readme += fh.read()
        claims = []
        for pat in (r"未推送[^。\n]{0,30}", r"无\s*remote", r"本地 git 无 remote",
                    r"未推送任何远程仓库"):
            for m in re.finditer(pat, readme):
                claims.append(m.group(0))
        if claims:
            print("  README claims about pushing: %s" % claims)
            bad = [c for c in claims if "未推送" in c or "无 remote" in c]
            check("%s: README does not claim 'no remote' while a remote exists" % name,
                  not (bad and has_remote),
                  "remote is %s but README says %s" % (rem.split("\n")[0][:60], bad))
        if has_remote:
            print("  actual remote: %s" % rem.split("\n")[0])

        # ---- 4) 清单声明的工具名是否在脚本里实现 ----
        #     （只做"名字出现过"的粗检，避免误判）
        tools = []
        for rel in ("connector-meta.json", ".codebuddy-plugin/plugin.json", "package.json"):
            d = read_json(os.path.join(repo, rel))
            if isinstance(d, dict):
                for key in ("tools", "mcpTools"):
                    v = d.get(key)
                    if isinstance(v, list):
                        tools += [t if isinstance(t, str) else t.get("name")
                                  for t in v if t]
        if tools:
            blob = ""
            for dp, dn, fn in os.walk(repo):
                if ".git" in dp or "node_modules" in dp:
                    continue
                for f in fn:
                    if f.endswith((".py", ".mjs", ".js", ".json", ".md")):
                        try:
                            with io.open(os.path.join(dp, f), encoding="utf-8") as fh:
                                blob += fh.read()
                        except OSError:
                            pass
            missing = [t for t in tools if t and blob.count(t) < 2]
            check("%s: every declared tool name appears in the tree" % name, not missing,
                  "mentioned once only: %s" % missing)

    print()
    for n in NOTES:
        print("  note %s" % n)
    print()
    if FAILS:
        print("audit_plugin_manifests: FAILED %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("audit_plugin_manifests: the plugin manifests and README claims agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
