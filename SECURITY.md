# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| Phocinae-Largha-150M-v1 (model weights) | ✅ |
| phocinae-server / phocinae-guard / phocinae-mcp (PyPI) | ✅ latest only |
| dsh-phocinae (npm) | ✅ latest only |

## Reporting a vulnerability

Phocinae-Largha is a local inference model and toolset. Security-relevant concerns include
(but are not limited to): prompt-injection behaviour of the decision heads, calibration
exploitation, gate bypass scenarios in `phocinae-guard`/`dsh-phocinae`, and supply-chain
issues in released artifacts.

**Please do NOT open a public issue for vulnerabilities.** Instead:

1. Report via the private channel listed in the GitHub Security tab of this repository
   ("Report a vulnerability"), or
2. Email a description (scope, reproduction steps, impact) to the maintainer via the
   address in the GitHub profile of the repository owner.

What to include: affected component and version, steps to reproduce, expected vs actual
behaviour, and (if available) a patch suggestion.

## What to expect

- Acknowledgment within 7 days.
- Status update within 30 days, including whether the report is accepted.
- Disclosure: after a fix is released, we credit reporters (or keep them anonymous on request)
  in the release notes / CHANGELOG.

## Scope notes

- The model itself is a research artifact; it makes probabilistic decisions. It is NOT a
  security boundary on its own — `phocinae-guard` and `dsh-phocinae` default to
  fail-closed (deny) precisely because of this.
- Known limitations (e.g., knowledge-heavy reasoning) are documented in
  `docs/technical-report.md` and `MODEL_CARD.md`; reports duplicating documented limitations
  may be closed as known issues.
