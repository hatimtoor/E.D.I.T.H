# E.D.I.T.H. — Master Feature Spec & Build Plan

Synthesis of the 4 research docs (`hermes-architecture`, `hermes-features`, `openclaw-architecture`,
`openclaw-features`) + the 3 source documents. This is the single source of truth for what we build.

## Vision (from the documents)
E.D.I.T.H = an original local-first agent that has **OpenClaw's breadth** (a gateway reachable from
every messaging channel + device sensors) **and Hermes' depth** (self-improving skill loop, hardened
sandboxes, sacred prompt caching), plus **JARVIS/FRIDAY** traits (multi-modal, proactive, network-
aware) and an **authorized hacking toolkit**, and it **browses the web unblocked on Linux servers**.

## The two design philosophies (verified in code)
- **Hermes = "narrow waist"**: 5 stable ABCs/registries; everything else is a plugin.
  `ProviderProfile` (`providers/base.py`), tool `registry` (`tools/registry.py`, AST self-register),
  `BaseEnvironment` (`tools/environments/base.py`), `ContextEngine` (`agent/context_engine.py`),
  `MemoryProvider` (`agent/memory_provider.py`). Plus `gateway/platforms/base.py` for channels.
- **OpenClaw = plugin gateway**: ~110 `extensions/`, a WS control plane (gateway-protocol),
  companion device "nodes", markdown skill packs. Capability arrives as plugins.
→ **E.D.I.T.H adopts the narrow-waist core, then hangs every channel/tool/provider off it as a plugin.**

---

## Architecture decisions (locked, grounded in research)

1. **Sacred prompt cache** (Hermes `agent/prompt_caching.py`, ~80 lines, directly portable):
   system prompt + last-3 non-system messages = 4 cache breakpoints, single TTL. Memory is a
   **frozen snapshot** at session start; mid-session writes hit disk but are NOT re-injected
   (would break the prefix). Learning runs in **forks** that never touch the live cache.
2. **Narrow waist first**: build the 5 ABCs + one concrete impl each, then plugins. Our current
   `edith/` already has primitive versions of memory/skills/sandbox/llm — refactor them to the ABCs.
3. **One SQLite DB**: WAL + dual FTS5 (unicode61 + trigram) with WAL→DELETE fallback; `sessions`
   (self-FK for subagent lineage, token/cost columns) + `messages`. (Hermes `hermes_state.py`.)
4. **Closed-loop learning** = forked self-review on a daemon thread, tool-whitelisted to
   `[memory, skills]`, biased to act (≥1 update/session) + inactivity curator that only archives.
5. **Gateway** = long-running daemon, per-session agent cache (LRU 128 + 1h TTL), platform adapters
   behind one `Channel` ABC; cross-channel identity pairing.
6. **Layered permission matrix** (un-bypassable hard guards → smart aux-LLM → manual → cron mode);
   security policy in one mtime-cached config file.
7. **Progressive 3-tier skills** (agentskills.io `SKILL.md` frontmatter): tier-1 index in prompt,
   tier-2 body on `skill_view`, tier-3 support files on demand. Trust-tiered scanner for installs.

---

## Feature matrix → build plan

Legend: **Have** = exists in `edith/` now · **Port** = adapt from research · **New** = build fresh.
Priority: P0 (core spine) … P8 (stretch).

| Capability | Hermes ref | OpenClaw ref | E.D.I.T.H plan | Pri | Status |
|---|---|---|---|---|---|
| Provider profiles (Anthropic/OpenAI/OpenRouter/Ollama/LMStudio/DeepSeek/Nous/Gemini) | `providers/base.py`, `plugins/model-providers/*` | `extensions/<vendor>` | `ProviderProfile` dataclass + registry; port our LLMClient | P0 | Have(partial) |
| Tool registry (self-registering) | `tools/registry.py` | plugin-sdk | AST/decorator self-register; refactor our tools | P0 | Have(partial) |
| Sacred prompt caching | `agent/prompt_caching.py` | — | Port verbatim (~80 lines) | P0 | New |
| SQLite state (WAL+FTS5 dual) | `hermes_state.py` | — | `sessions`+`messages`, trigram FTS, WAL fallback | P0 | Port |
| Context engine (compress at 75%) | `agent/context_engine.py` | — | `ContextEngine` ABC + compressor; replace our flush | P1 | Have(primitive) |
| 3-tier skills + agentskills.io | `tools/skills_tool.py`,`skill_manager_tool.py` | `skills/*/SKILL.md` | `SKILL.md` frontmatter, view/manage, our edit-lock | P1 | Have(partial) |
| Closed-loop learning (fork review + curator) | `agent/background_review.py`,`curator.py`,`trajectory.py` | — | daemon-thread fork, `[memory,skills]` whitelist, ShareGPT export | P2 | New |
| 3-layer memory + provider ABC | `memory_tool.py`,`memory_provider.py` | `memory-lancedb`,`active-memory` | `MemoryProvider` ABC; keep our namespaced store as default; LanceDB plugin | P2 | Have(partial) |
| Sandbox backends (local/docker/ssh/+modal/daytona/singularity) | `tools/environments/*` | `extensions/openshell` | `BaseEnvironment` ABC; we have local/docker/ssh; add snapshot model | P2 | Have(partial) |
| Multi-agent delegation (blocking child agents) | `tools/delegate_tool.py` | `coding-agent` skills | `delegate_task` tool, summary-only return, blocked-tools | P3 | New |
| Messaging gateway + channels | `gateway/platforms/*` | `extensions/<channel>` | `Channel` ABC + daemon; build Telegram→Discord→WhatsApp→Slack→Signal first | P3 | Have(ABC only) |
| Cross-channel identity pairing | `gateway/pairing.py`,`channel_directory.py` | — | identity map table | P4 | New |
| Stealth browser (the headline) | `tools/browser_tool.py`,`browser_camofox.py` | `extensions/browser` | DONE — patchright+camoufox, proxy rotation, challenge wait | P0 | **Have** |
| Browser tool surface (navigate/click/type/snapshot/vision) | `tools/browser_tool.py` | `extensions/browser` | expand our StealthBrowser into agent tools | P3 | Have(fetch/search) |
| Web search providers | `tools/web_tools.py`,`plugins/web/*` | `extensions/{brave,exa,tavily,...}` | provider plugins; we have Bing-scrape default | P3 | Have(default) |
| Voice (push-to-talk, STT, full-duplex) | `tools/voice_mode.py`,`transcription_*` | `apps/swabble`,`extensions/*speech*` | STT (faster-whisper) + TTS tool; voice loop | P5 | New |
| TTS (Edge/ElevenLabs/OpenAI/Piper/Kitten/Neu…) | `tools/tts_tool.py` | `extensions/elevenlabs,azure-speech` | `text_to_speech` tool, provider plugins (Edge free default) | P5 | New |
| Image generation (FLUX/GPT-Image/Ideogram via FAL) | `tools/image_generation_tool.py` | `extensions/{fal,comfy}` | `image_generate` tool + FAL plugin | P6 | New |
| Video generation | `tools/video_generation_tool.py` | `extensions/{runway,pixverse}` | `video_generate` tool | P7 | New |
| Vision / computer-use | `tools/vision_tools.py`,`computer_use_tool.py` | iOS node | `vision_analyze`; computer_use later | P6 | New |
| Cron / NL scheduler | `cron/scheduler.py`,`tools/cronjob_tools.py` | macOS Cron UI,`croner` | `cronjob` tool + 60s tick scheduler; non-interactive runs | P4 | New |
| Companion device nodes (camera/GPS/screen/canvas) | — | `apps/ios`,`apps/macos`,`extensions/device-pair,canvas` | WS node protocol + a phone client; Canvas surface | P8 | New |
| Ecosystem skill packs (Hue/Sonos/Notion/Apple/GitHub/Gmail…) | `skills/`,`optional-skills/` | `skills/*` (CLI+SKILL.md) | ship as skill packs (CLI wrapper + SKILL.md) | P6+ | New |
| MCP client (consume external MCP tools) | `tools/mcp_tool.py` | `@modelcontextprotocol/sdk` | MCP client → registry entries | P4 | New |
| Authorized hacking toolkit (recon→exploit, CVE) | `tools/osv_check.py`,`tirith_security.py` | — | expand our scope-gated recon; add CVE (OSV), web/auth testing | P3 | Have(recon) |
| Permission matrix (5-level) | `tools/approval.py` | `extensions/phone-control` | hard-guards→smart→manual→cron; our perm levels are the base | P2 | Have(primitive) |
| Prompt-injection scanning everywhere | `tools/threat_patterns.py` | net-policy | our memory scan → shared scanner for context+memory+skills | P1 | Have(partial) |
| Trajectory/RL export, batch runner | `batch_runner.py`,`trajectory.py` | — | ShareGPT JSONL export from loop | P7 | New |
| Web dashboard + TUI | `web/`,`ui-tui/` | macOS app,`workboard` | FastAPI+small SPA dashboard; rich TUI | P7 | New |

---

## JARVIS / FRIDAY traits → concrete features
- **Always-on, multi-surface presence** → gateway daemon + companion nodes (P3/P8).
- **Environmental/network awareness** → device sensors (GPS/camera/screen) + authorized recon (P3/P8).
- **Proactive briefings** → NL cron scheduler delivering to channels (P4).
- **Real-time tactical analysis** → vision + stealth browser + tool loop (P3/P6).
- **Self-preservation/continuity** → namespaced persistent memory + session DB + (later) multi-node.

---

## Build phases (each phase = small, shippable, testable; keeps token cost low)
- **P0 Core spine**: ProviderProfile + tool registry refactor, prompt_caching port, SQLite state. (stealth browser already done)
- **P1 Context+skills+injection**: ContextEngine, 3-tier SKILL.md, shared threat scanner.
- **P2 Learning+memory+sandbox+perms**: fork review + curator, MemoryProvider ABC, env snapshot model, permission matrix.
- **P3 Reach+act**: gateway daemon + first channels (Telegram, Discord), delegation, browser tool surface, hacking recon→exploit.
- **P4 Automation+MCP+pairing**: cron scheduler, MCP client, cross-channel pairing.
- **P5 Voice**, **P6 Image/Vision+skill packs**, **P7 Video/dashboard/RL**, **P8 Device nodes**.

## What we already have (keep, refactor into the spine)
`edith/{core(config,llm,context,agent), memory, skills, browser(stealth+fetch), security, sandbox,
channels(ABC), tools(builtin), ruflo}` + 46 tests + working stealth browser (patchright+camoufox)
+ web fetch/search + local LLM providers. These become the P0/P1 concrete impls behind the ABCs.

## Token-lean build protocol
Build one matrix row at a time: small diff → `pytest` → commit. Use `reference/{hermes,openclaw}`
(gitignored, in-repo) for grounded porting. Don't re-read whole research docs; cite by section.
