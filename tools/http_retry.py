#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bounded-retry HTTP helpers for the verification tools.

Why this module exists: on this WSL network, pypi.org and
files.pythonhosted.org intermittently reset the TLS handshake
(``ConnectionResetError: [Errno 104]``). That is not a verification result. It
used to surface as a red traceback from whichever suite happened to fetch first,
so the same tree produced a different PASS/FAIL set on every run — and a gate
whose colour depends on the network is not a gate.

The retry is bounded and the last exception is re-raised, so a registry that is
genuinely unreachable still fails. No SKIP-on-network-error: a suite that says
"nothing was verified" must be a deliberate decision, not a swallowed reset.
"""
import shutil
import time
import urllib.request

DEFAULT_ATTEMPTS = 4


def get_bytes(req, timeout=60, attempts=DEFAULT_ATTEMPTS):
    """GET a URL (or Request) and return the body, retrying transient errors."""
    last = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:                     # noqa: BLE001
            last = e
            if attempt + 1 < attempts:
                time.sleep(1.5 * (attempt + 1))
    raise last


def download(url, dest, timeout=300, attempts=DEFAULT_ATTEMPTS):
    """Stream a URL to ``dest``, retrying the whole transfer on failure."""
    last = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r, open(dest, "wb") as o:
                shutil.copyfileobj(r, o)
            return
        except Exception as e:                     # noqa: BLE001
            last = e
            if attempt + 1 < attempts:
                time.sleep(1.5 * (attempt + 1))
    raise last
