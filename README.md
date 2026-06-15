# E.D.I.T.H.

**E**ven **D**ead, **I**'m **T**he **H**ero — an autonomous, local-first AI agent that fuses the
best of OpenClaw (broad networked gateway) and Hermes Agent (self-improving closed loop),
adds the capabilities of J.A.R.V.I.S. & F.R.I.D.A.Y., and ships a stealth browser engine plus
an authorized-security toolkit.

> Built as a clean reimplementation — not a literal fork — because it fixes every documented
> pain point of OpenClaw and Hermes at the architecture level instead of inheriting them.

---

## Why E.D.I.T.H. exists

The research behind this project catalogued the real-world failures of the two leading 2026
agent frameworks. E.D.I.T.H. is designed so that **each documented grievance is solved by
construction**:

| Pain point (from research) | Framework | E.D.I.T.H.'s fix |
|---|---|---|
| Browser gets **blocked / CAPTCHA-walled on Linux servers** | Both | `edith.browser.stealth` — patched Playwright, fingerprint spoofing, residential-proxy rotation, human cadence, CAPTCHA fallback |
| Agent **overwrites hand-crafted skills** during self-reflection | Hermes | Skill **immutability lock** (`edith skills protect <name>`) enforced in the registry |
| Memory **"junk drawer"** — vector collisions, wrong tool picked | Hermes | Namespaced 3-layer memory + automatic dedup + per-task profiles |
| **Context drift** from token compaction | OpenClaw | Pre-compaction flush hook writes state to `WORKING.md` before truncation |
| **Token blowup** — 16k tokens on an empty session | Hermes | Progressive 3-level skill loading + dynamic skill router |
| **Prompt injection → host compromise** | OpenClaw | Sandbox backends + capability dropping + injection scanner on every memory write |
| Wide permissions → **unauthorized actions** | OpenClaw | Explicit permission matrix + authorization gate for any sensitive op |
| No **P2P multi-agent mesh** | OpenClaw wish | ruflo swarm bridge (mesh/hierarchical topologies) |
| Subagents are **short-lived, can't collaborate** | Hermes wish | Persistent horizontal teams over a shared message bus |

See [`docs/PAINPOINTS_SOLVED.md`](docs/PAINPOINTS_SOLVED.md) for the full mapping with citations
back to the source research.

---

## Architecture at a glance

```
                         ┌─────────────────────────────┐
                         │        E.D.I.T.H. core       │
                         │   agent loop · context build │
                         └──────────────┬──────────────┘
        ┌──────────────┬───────────────┼───────────────┬──────────────┐
        ▼              ▼               ▼               ▼              ▼
   ┌─────────┐   ┌──────────┐   ┌────────────┐   ┌──────────┐   ┌──────────┐
   │ memory  │   │  skills  │   │  stealth   │   │ security │   │ channels │
   │ 3-layer │   │ progress │   │  browser   │   │ authz +  │   │ gateway  │
   │ SQLite  │   │ + locks  │   │ anti-block │   │ recon    │   │ adapters │
   └─────────┘   └──────────┘   └────────────┘   └──────────┘   └──────────┘
        └──────────────┴───────────────┼───────────────┴──────────────┘
                                        ▼
                         ┌─────────────────────────────┐
                         │   ruflo MCP orchestration    │
                         │ swarm · memory · agent spawn │
                         └─────────────────────────────┘
```

Full detail in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Quick start

```bash
# 1. install (editable)
python -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e .

# 2. install the stealth browser runtime
python -m edith browser install

# 3. configure
cp .env.example .env                 # add your LLM + proxy keys
cp config/edith.example.yaml config/edith.yaml

# 4. run
python -m edith chat                 # interactive
python -m edith run "summarize my open GitHub issues"
```

---

## Security & authorization

E.D.I.T.H.'s offensive-security toolkit is **authorization-gated**. It will refuse to act
against any host not listed in your signed engagement scope (`config/authorization.yaml`).
This makes it a powerful tool for **CTFs, authorized penetration tests, and your own
infrastructure** — and a non-starter for abuse. See [`docs/SECURITY.md`](docs/SECURITY.md).

---

## Status

This is **v0.1 — a working foundation**, not a finished product. What runs today and what is
scaffolded for the next iterations is tracked honestly in [`docs/ROADMAP.md`](docs/ROADMAP.md).
