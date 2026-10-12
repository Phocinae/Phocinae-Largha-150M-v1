# tools/

## `verify_published.py` — check the *published* packages, not the source tree

```bash
python tools/verify_published.py                     # every package, latest on PyPI
python tools/verify_published.py --only mcp
python tools/verify_published.py --extra-path /path/to/site-packages
```

It downloads each wheel from PyPI, extracts it, and exercises it the way a user
would — no `pip install` (which stalls on restricted networks, and "it installed"
is not the thing under test). Dependencies are borrowed from the interpreter you
point it at, and a package whose dependencies are absent is reported as `SKIP`
with the missing names, never as a failure.

Current result against the published releases: **41 checks, 0 failures.**

```
phocinae-cli 0.1.2     15 checks  --version / ping / decide / gate x11 / bypasses
phocinae-guard 0.1.4   17 checks  bundled table, benign, dangerous, all bypasses, fail-closed
phocinae-mcp 0.2.4      4 checks  initialize/tools/list, gate call, stdout is pure JSON-RPC
phocinae-server 0.1.6   5 checks  declared deps (numpy!), loopback proxy bypass
```

## Why this exists

The project hit the same class of defect three times: **green in the source
checkout, broken in the published wheel.**

| release | defect | why source-level tests could not see it |
|---|---|---|
| `phocinae-mcp` 0.2.2 | the wheel did not contain the L0 table, so `pip install` produced a gate that denied *every* command | in a development checkout `locate_guard()` finds the sibling `../phocinae-guard/guard.py`, so the fallback path never runs |
| `phocinae-cli` 0.1.1 | the wheel carried a hand copy of guard 0.1.0, leaving four shell bypasses open (`ls\nrm -rf /`, `ls\trm -rf /`, `echo pwned>/etc/passwd`, `ls ; \rm -rf /`) | the source tree contained the same stale table, so its tests agreed with the bug |
| `phocinae-guard` 0.1.3 | the allowlist only had `python3 -m pytest`, and Windows has no `python3`, so running a test suite was denied | the authoring machine has both `python` and `python3` on PATH |

Each was found by taking the artifact that users actually receive and running it.
Two follow-on practices came out of this and are worth keeping:

- **Never hand-copy the L0 layer.** It now exists in four places (guard, mcp, the
  CLI package, and the single-file CLI) and every copy is *generated* from
  `guard.py`, with a parity test comparing all of them verdict-by-verdict.
- **Assert the artifact, not the intent.** The mcp wheel is checked for containing
  `l0_table.json`, because `package-data` was missing once and the table silently
  did not ship.

## Requirements

- Network access to `pypi.org` (for the wheels) and a running `phocinae-server`
  for the CLI and MCP checks — pass `--server` if it is not on the default
  `http://127.0.0.1:8155`.
- For the CLI: `typer`, `rich`, `httpx` somewhere on the path.
- For the server: `fastapi`, `uvicorn`, `torch`, `numpy`, `requests`.
