#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_mcp_tool_schemas_vs_docs.py — MCP 工具的参数说明与实现是否一致。

**为什么查这个**：MCP 工具的参数由 `inputSchema` 决定，客户端据此构造调用。
schema 与 README 不一致时，读者会按 README 传参、然后被服务端拒绝 —— 或者更糟，
传了 README 说"可选"的参数而 schema 里是必填。

判据（只做**可判定**的比对，不解读语义）：

  1. 四个工具（gate / classify / route / score）在 `tools/list` 里都存在
  2. 每个工具的 `inputSchema.properties` 里每个参数，**README 里都提到过**
  3. README 里以 `` `参数名` `` 形式出现、且看起来像工具参数的词，**都在某个 schema 里**
     （反向检查：文档承诺的参数真的存在）
  4. 每个工具都有 `description`，且 `required` 列表里的键都在 `properties` 里

用**发布到 PyPI 的 wheel**，通过真实 stdio MCP 会话取 schema —— 与客户端看到的一致。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_mcp_host_refusal import fetch_wheel  # noqa: E402  复用下载逻辑

TOOLS = ["gate", "classify", "route", "score"]
FAILS = []


def check(name, cond, detail=""):
    print(("  PASS " if cond else "  FAIL ") + name + ("" if cond else "  " + str(detail)))
    if not cond:
        FAILS.append(name)


def mcp_session(root, requests):
    boot = ("import sys; sys.path.insert(0, %r); "
            "from phocinae_mcp.server import main; sys.exit(main())") % root
    payload = ("\n".join(json.dumps(r) for r in requests) + "\n").encode()
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run([sys.executable, "-c", boot], input=payload,
                       capture_output=True, timeout=180, env=env)
    out = p.stdout.decode("utf-8", "replace")
    frames = {}
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if "id" in o:
            frames[o["id"]] = o
    return frames


def main():
    ver, root, wheel_path = fetch_wheel("phocinae-mcp")
    print("phocinae-mcp %s (from PyPI, unpacked)\n" % ver)

    frames = mcp_session(root, [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "schema-audit", "version": "1"}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ])
    tools = ((frames.get(2, {}).get("result") or {}).get("tools")) or []
    by_name = {t.get("name"): t for t in tools}
    check("tools/list returns all four tools", set(by_name) == set(TOOLS),
          "got %s" % sorted(by_name))

    # README 正文。wheel 里**没有** README.md（pyproject 的 files 未包含它），但
    # pyproject 的 readme= 会把它写进 METADATA 的 Description —— 那正是 PyPI 页面
    # 显示的正文。所以文档确实是随包发布的，只是不在文件列表里。
    readme = ""
    for cand in ("README.md", "README.zh.md"):
        p = os.path.join(root, cand)
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as fh:
                readme += fh.read()
    if not readme:
        import zipfile
        whls = [wheel_path] if os.path.isfile(wheel_path) else []
        for whl in whls:
            try:
                with zipfile.ZipFile(whl) as z:
                    meta = next(n for n in z.namelist()
                                if n.endswith(".dist-info/METADATA"))
                    raw = z.read(meta).decode("utf-8", "replace")
            except (zipfile.BadZipFile, StopIteration, OSError):
                continue
            lines = raw.split("\n")
            for i, l in enumerate(lines):
                if l.strip() == "":
                    readme = "\n".join(lines[i + 1:])
                    break
            if readme:
                print("  (documentation read from the wheel's METADATA)")
                break
    if not readme:
        print("  NOTE no documentation found in the artifact; skipping doc comparison")
        return 0 if not FAILS else 1

    all_params = set()
    for name in TOOLS:
        t = by_name.get(name)
        if not t:
            continue
        props = set((t.get("inputSchema") or {}).get("properties") or {})
        req = set((t.get("inputSchema") or {}).get("required") or [])
        all_params |= props

        check("%s has a description" % name, bool(t.get("description")))
        check("%s required keys exist in properties" % name, req <= props,
              "required=%s properties=%s" % (sorted(req), sorted(props)))
        # 每个 schema 参数都应在 README 里出现过
        missing = sorted(p for p in props if ("`%s`" % p) not in readme and p not in readme)
        check("%s: every schema parameter is documented" % name, not missing,
              "undocumented: %s" % missing)

    # 文档里的参数写在**工具表**的"输入"列里，形如：
    #   | `gate` | 判定 shell 命令能否执行 | `command`、`cwd?`、`server?` | `decision` … |
    # 名字在单元格里、列头才是"参数"，所以"附近 N 字符内有'参数'"这种判据抓不到 ——
    # 第一版就是这么把 7/7 全判成"未文档化"的。
    #
    # 解析表格，取"参数"那一列，逐工具比对：多一个、少一个都会报出来。
    def table_params(text):
        """返回 {tool: {"documented": set, "optional": set}}。"""
        rows = {}
        header_params_col = None
        for line in text.split("\n"):
            if not line.strip().startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if header_params_col is None:
                # 列头是 **输入**（不是"参数"）。我曾经两次按"参数"去找，都没找到，
                # 于是把 7/7 参数判成"未文档化"。认这三种写法。
                for i, c in enumerate(cells):
                    if re.search(r"输入|参数|input", c, re.I):
                        header_params_col = i
                        break
                continue
            if header_params_col is None or len(cells) <= header_params_col:
                continue
            tool_m = re.search(r"`([a-z]+)`", cells[0])
            if not tool_m or tool_m.group(1) not in TOOLS:
                continue
            cell = cells[header_params_col]
            names, optional = set(), set()
            for m in re.finditer(r"`([a-z_]{2,20})(\?)?`", cell):
                names.add(m.group(1))
                if m.group(2):
                    optional.add(m.group(1))
            rows[tool_m.group(1)] = {"documented": names, "optional": optional}
        return rows

    tbl = table_params(readme)
    print("\n  documented parameter table:")
    for name in TOOLS:
        info = tbl.get(name)
        print("    %-9s %s" % (name, sorted(info["documented"]) if info else "(no row)"))

    for name in TOOLS:
        t = by_name.get(name)
        if not t:
            continue
        props = set((t.get("inputSchema") or {}).get("properties") or {})
        req = set((t.get("inputSchema") or {}).get("required") or {})
        info = tbl.get(name)
        check("%s has a parameter row in the README" % name, info is not None)
        if not info:
            continue
        doc = info["documented"]
        check("%s: schema parameters == documented parameters" % name,
              props == doc,
              "schema only: %s; docs only: %s" % (sorted(props - doc), sorted(doc - props)))
        # 文档用 `x?` 表示可选，应当与 schema 的 required 相反
        declared_optional = info["optional"]
        actually_optional = props - req
        check("%s: optional markers match the schema" % name,
              declared_optional == actually_optional,
              "docs mark %s optional; schema says %s"
              % (sorted(declared_optional), sorted(actually_optional)))

    print()
    if FAILS:
        print("audit_mcp_tool_schemas_vs_docs: FAILED %d check(s)" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("audit_mcp_tool_schemas_vs_docs: tool schemas and documentation agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
