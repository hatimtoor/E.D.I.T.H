# E.D.I.T.H.

**E**ven **D**ead, **I**'m **T**he **H**ero — an original, autonomous, local-first AI agent.
It takes the best ideas from OpenClaw (broad networked gateway) and Hermes Agent
(self-improving closed loop), fixes their documented pain points, and ships a stealth
browser plus an authorization-gated security toolkit.

> Original codebase — not a fork. Hermes and OpenClaw are *references* we studied and
> selectively reimplemented with attribution (see `NOTICE`).

## Pain points fixed (by construction)

| Pain point | Fix |
|---|---|
| Browser **blocked / CAPTCHA-walled on Linux servers** | `edith/browser/stealth.py` — patched engine, fingerprint patches, residential-proxy rotation, human cadence, xvfb preflight, CAPTCHA detect |
| Agent **overwrites hand-crafted skills** | `edith skills protect <name>` — real edit-lock in the registry |
| Memory **"junk drawer"** collisions | namespaced 3-layer SQLite+FTS5 + vectors + dedup |
| **Context drift** from compaction | pre-compaction flush to `WORKING.md` + real truncation |
| **Token blowup** | progressive 3-level skill loading |
| **Prompt-injection → host compromise** | injection scan on memory writes + hardened Docker sandbox + scope gate |

Full mapping: [`docs/PAINPOINTS_SOLVED.md`](docs/PAINPOINTS_SOLVED.md). Architecture:
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Plan: [`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md).

## Quick start

```bash
python -m venv .venv && . .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e .[browser,llm]
python -m edith browser install                 # patchright + chromium
cp .env.example .env                            # add keys / proxy
python -m edith doctor
python -m edith browser test https://example.com
python -m edith run "summarize the latest on <topic>"
```

## Security

The offensive-security toolkit is **authorization-gated**: it refuses any host not listed
in a signed `config/authorization.yaml`. Built for CTFs, authorized pentests, and your own
infra. See [`docs/SECURITY.md`](docs/SECURITY.md).

## Status

v0.1 — working, tested foundation. Honest status: [`docs/ROADMAP.md`](docs/ROADMAP.md).
