# Contributing to Phocinae-Largha-150M-v1

Thanks for your interest! This repository hosts the release artifacts of a 144.3M typed
decision model plus bilingual documentation, benchmark sheets and demo gallery. We welcome
contributions in the following areas.

## Ways to contribute

1. **Docs & translations** — typos, unclear passages, missing Chinese/English parity
   between `README.md` ↔ `README.zh.md` and `docs/*.md` ↔ `docs/*.zh.md`.
2. **Reproductions** — re-run the evaluation or calibration numbers described in
   `docs/reproduce.md` and report your measured values. We explicitly keep independent
   reproductions side-by-side with official numbers in `docs/cost-savings.md`.
3. **Gallery & figures** — new demo scenes (see `docs/gallery/README.md` for the S/G
   numbering scheme and the size limits in `docs/gallery/SHA256SUMS`).
4. **Integrations** — new bindings for `phocinae-server` (the `/v1/systemone`-compatible
   HTTP API described in `docs/protocol.md`). Note: official plugins such as
   `dsh-phocinae` live in their own repositories; this repo only hosts model-side docs.
5. **Bug reports** — wrong numbers, broken links, checksum mismatches. See issue templates.

## Ground rules

- **Numbers are frozen.** Any change to a reported metric (accuracy, latency, savings %)
  must keep the official value AND add the independent-reproduction value alongside it,
  clearly labelled (see `docs/cost-savings.md`). Never silently replace a published number.
- **Language parity.** Text changes to English docs should mirror to the Chinese docs
  (and vice versa) in the same PR where possible.
- **License.** This repo is Apache-2.0. Upstream mmBERT is MIT — keep the `NOTICE` file
  intact; if you copy third-party code, preserve its license headers.
- **No weight changes.** Model weights are release-frozen; don't PR weight updates. New
  model variants are discussed via issues first.

## Pull request checklist

- [ ] English + Chinese doc parity for doc changes
- [ ] Official vs independent reproduction values both present for metric changes
- [ ] No `figures/` or `docs/gallery/` asset added without updating `SHA256SUMS`
- [ ] Commit messages describe the change, not "fix stuff"

## Dev quickstart

```bash
git clone https://github.com/Phocinae/Phocinae-Largha-150M-v1.git
cd Phocinae-Largha-150M-v1
# weights are on Hugging Face; download them there (see README quickstart)
pip install phocinae-server
```

## Code of conduct

See [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md).
