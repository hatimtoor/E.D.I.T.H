# E.D.I.T.H. roadmap & honest status

This is **v0.1 — a working, tested foundation**. Below is exactly what runs today and
what is scaffolded for next, so there's no overselling.

## ✅ Working today (installed, tested — 39 passing tests)
- Config + 5-level permission matrix, env overlay.
- Provider-agnostic LLM client (anthropic/openai/openrouter), lazy imports.
- 3-layer memory: SQLite(+FTS5) + local vectors, profile namespacing, dedup, injection scan.
- Skill registry: progressive 3-level loading + **agent-immutable protection lock**.
- Context builder with pre-compaction flush to `WORKING.md`.
- Stealth browser engine (strategy complete; needs `patchright`/`camoufox` installed to drive).
- Authorized-security toolkit: scope gate + recon (resolve/portscan/TLS), all gated.
- Hardened sandbox backends (local/docker/ssh) + destructive-command guard.
- ruflo bridge with graceful local fallback.
- Channel abstraction + local CLI channel.
- Full Typer CLI: `doctor, run, chat, browser, skills, memory, security`.

## 🚧 Next (scaffolded, not yet wired end-to-end)
- **Live LLM tool execution** verified against a real key (loop is built; needs a key to
  exercise the full multi-round tool path).
- **Network channel adapters**: WhatsApp/Telegram/Discord/Signal implementing `Channel`.
- **CAPTCHA solver** integration (seam exists; needs 2captcha/capsolver key + network).
- **Self-improvement loop**: trajectory capture → reflection → skill crystallization
  (registry + protection are ready to receive it safely).
- **Voice**: full-duplex low-latency voice (the shared community wish).
- **Exploit modules** beyond recon, all behind the same authorization gate.

## 🎯 Stretch (JARVIS/FRIDAY-grade)
- Distributed multi-node survival/persistence via ruflo mesh.
- Real-time environmental/streaming context.
- Nanotech-style dynamic tool composition (compose tools on the fly per task).

## How to move an item from 🚧 to ✅
Each scaffolded piece has a clear contract already (interfaces + `# FIX:`/seam comments).
Implement against the interface, add a test mirroring the ones in `tests/`, run
`python -m pytest`, and update this file.
