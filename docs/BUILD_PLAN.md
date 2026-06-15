# E.D.I.T.H. — Build Plan (approved 2026-06-15)

## Context

We're building **E.D.I.T.H.** ("Even Dead, I'm The Hero") — a local-first autonomous AI agent
that fuses the two real open-source agents from the research and fixes their documented pain
points, with a **stealth browser** that survives Linux-server bot-blocking as the #1 feature.

Approved decisions (corrected 2026-06-15 after a clone misstep):
- **ruflo = build orchestrator only** (not a runtime dependency). E.D.I.T.H stays standalone.
- **E.D.I.T.H is an ORIGINAL codebase** — our own Python package `edith/`. We **study** Hermes +
  OpenClaw as references and **port specific code with inline attribution** only where it clearly
  helps. We do **NOT** clone either repo into ours.
- **Connect ruflo as an MCP server** (native tools) — may need one Claude Code restart.
- **v1 priority = stealth browser.**

Both references are **MIT-licensed** → reuse with attribution. The full reference repos stay
**local-only** (`reference/`, gitignored), never committed.

**Codebase**: the `edith/` package IS the project (at repo root). Its modules — stealth browser,
skill protection lock, namespaced memory, authorization gate — are original code informed by
studying both references. The two pending review rounds (2 CRITICAL + HIGH) are applied in Phase 3.

---

## Technologies

| Layer | Tech |
|---|---|
| Core brain | **Fork of NousResearch/hermes-agent** (Python 3.11–3.13, `uv` deps) |
| Channels | Hermes Python `gateway/` + ported OpenClaw extras (TS adapters as sidecars where needed; Node 22) |
| Stealth browser | **patchright** (default) + **camoufox** option + Playwright; `agent-browser` (Hermes) augmented |
| Memory | SQLite + FTS5 (Hermes) + vector embeddings + namespacing/dedup (ported) |
| Sandbox | Docker (hardened) / SSH / local backends |
| Security | authorized recon/exploit + ruflo `security` (CVE/threat) at build time |
| LLM | Anthropic / OpenAI / OpenRouter / Nous Hermes / DeepSeek (Hermes multi-provider) |
| Anti-block | residential proxy pool, xvfb, fingerprint spoofing |
| Build orchestration | **ruflo v3.10.4** (swarm / autopilot / hive-mind / memory / neural / hooks / MCP) |

---

## How ruflo will actually be used (build-time only)

1. **Register MCP** — `ruflo mcp start` then `claude mcp add ruflo` so swarm/agent/memory/neural
   tools become **native callable tools**. (`ruflo mcp exec <tool>` / `ruflo swarm ...` work via CLI immediately.)
2. **`ruflo init`** → enables ruflo hooks + shared build memory across sessions.
3. **`ruflo swarm init` + `swarm start -o "<phase objective>" -s development`** → specialized build agents per phase.
4. **`ruflo autopilot enable`** → persistent completion until all tasks done; `learn/predict` to improve.
5. **`ruflo memory`** → durable cross-agent build memory (decisions, file map, blockers).
6. **`ruflo security`** → CVE/threat scan of fork deps + our changes during the build.
7. ruflo is **NOT** imported by E.D.I.T.H at runtime — the shipped agent runs without it.

---

## Build phases

**Phase 0 — ruflo + fork baseline:** register ruflo MCP, `ruflo init`, copy Hermes source in as core
(record upstream commit, keep LICENSE + NOTICE), verify it boots, gitignore heavy artifacts.

**Phase 1 — Rebrand to E.D.I.T.H:** CLI `edith`, banner, `~/.hermes → ~/.edith`, `HERMES_* → EDITH_*`
compat shim. Internal module names rename progressively.

**Phase 2 — Stealth browser ⭐ (v1 PRIORITY):** replace/augment Hermes `tools/browser_tool.py` +
`browser_camofox.py` + `agent/browser_provider.py` with patchright default + camoufox (free) +
JS fingerprint patches + residential proxy rotation + human cadence + xvfb preflight + CAPTCHA detect.
Acceptance: passes a bot-detection page headless on Linux behind residential proxy under `xvfb-run`.

**Phase 3 — Apply documented fixes (port v0.1 patches):** skill edit-lock, memory namespacing+dedup+
injection scan, pre-compaction flush, authorization scope gate, + the 2 CRITICAL/HIGH review fixes.

**Phase 4 — OpenClaw channel capabilities:** base on Hermes' Python gateway; port OpenClaw extras
incrementally (iMessage, mobile WebSocket nodes + Canvas, missing adapters).

**Phase 5 — Authorized security/hacking toolkit:** recon → exploitation behind scope gate; ruflo
`security` for CVE/threat at build/dev time.

**Phase 6 — QA + validation:** ruflo autopilot to completion; pytest; `edith doctor`;
separate-lane security-reviewer + code-reviewer must approve.

---

## What E.D.I.T.H. will be able to do

- Run 24/7 local-first (Hermes brain), reachable from **multiple messaging channels** incl. your phone.
- **Browse the web unblocked on a Linux server** — the headline both upstreams fail at.
- **Self-improving skills** with human **protection locks**.
- **Namespaced, deduped, injection-resistant memory** (no junk-drawer).
- **Authorized security/recon toolkit** (CTF / pentest / own infra), scope-gated & safe-by-default.
- **Sandboxed execution** (Docker/SSH/local) with hardened defaults.
- Inherited Hermes extras: voice/TTS, image generation, cron automation, multi-agent delegation.

## Verification
- `edith doctor` green · stealth passes a bot-detection page under xvfb+proxy · `pytest` green ·
  `ruflo autopilot status` complete · security-reviewer + code-reviewer approve.

## Risks / notes
- Hermes is large (~5k files, 652KB `cli.py`) → record upstream commit, gitignore artifacts.
- OpenClaw channels are TS → full port is large; v1 leans on Hermes' gateway, ports extras incrementally.
- ruflo MCP tools may need one Claude Code restart to register.
- Multi-session work; ruflo autopilot + memory keep state across sessions.
