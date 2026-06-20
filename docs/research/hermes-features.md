# Hermes Agent — Complete Feature Inventory

Source: `C:\E.D.I.T.H\reference\hermes` (Hermes Agent by Nous Research, v0.17.x). READ-ONLY analysis.
All paths below are relative to `reference/hermes/` unless noted.

## 0. Top-Level Layout

| Area | Location | Notes |
|------|----------|-------|
| Entry points | `cli.py` (~652KB monolith), `run_agent.py`, `mcp_serve.py`, `batch_runner.py`, `mini_swe_runner.py` | CLI + library + MCP server + datagen |
| CLI package | `hermes_cli/` (100+ modules) | argparse, auth, gateway, cron, kanban, models, plugins, dashboard auth, doctor |
| Agent core | `agent/` (transports, adapters, context engine, memory, LSP, credentials) | model adapters: anthropic, bedrock, gemini (native + cloudcode), codex, azure |
| Tools | `tools/` (~90 modules) | self-registering tool registry (`tools/registry.py`) |
| Gateway | `gateway/` + `gateway/platforms/` | multi-channel messaging server |
| Plugins | `plugins/` | model-providers, memory, web, image_gen, video_gen, platforms, browser, cron, observability |
| Cron | `cron/` | native scheduler, blueprint/suggestion catalogs |
| Web UI | `web/` (React + Vite + TS) | dashboard SPA |
| TUI | `ui-tui/` (Ink/React TS) | terminal UI |
| Desktop | `apps/desktop/` (Electron) + `apps/bootstrap-installer/` (Tauri/Rust) | |
| ACP | `acp_adapter/` + `acp_registry/` | editor integration (Zed/ACP protocol) |
| Skills | `skills/`, `optional-skills/` | procedural memory; agentskills.io standard |
| Datagen/Training | `batch_runner.py`, `datagen-config-examples/`, `trajectory_compressor.py` | ShareGPT trajectories |

---

## 1. Channels / Gateway

Gateway server: `gateway/run.py`, platform base `gateway/platforms/base.py`, registry `gateway/platform_registry.py`. Plugin-based platforms in `plugins/platforms/`.

### Built-in platforms (`gateway/platforms/`)

| Channel | File |
|---------|------|
| Telegram | `gateway/platforms/telegram.py`, `telegram_network.py` |
| Slack | `gateway/platforms/slack.py` |
| Signal | `gateway/platforms/signal.py`, `signal_rate_limit.py` |
| WhatsApp (Web) | `gateway/platforms/whatsapp.py`, `whatsapp_common.py` |
| WhatsApp Cloud API | `gateway/platforms/whatsapp_cloud.py` |
| Email (IMAP/SMTP) | `gateway/platforms/email.py` |
| SMS | `gateway/platforms/sms.py` |
| Feishu / Lark | `gateway/platforms/feishu.py`, `feishu_comment.py`, `feishu_comment_rules.py`, `feishu_meeting_invite.py` |
| WeCom (WeChat Work) | `gateway/platforms/wecom.py`, `wecom_callback.py`, `wecom_crypto.py` |
| Weixin (personal WeChat) | `gateway/platforms/weixin.py` |
| DingTalk | `gateway/platforms/dingtalk.py` |
| Matrix | `gateway/platforms/matrix.py` |
| BlueBubbles (iMessage) | `gateway/platforms/bluebubbles.py` |
| QQ Bot | `gateway/platforms/qqbot/` (adapter, crypto, keyboards, onboard, chunked_upload) |
| Yuanbao (Tencent) | `gateway/platforms/yuanbao.py` + media/proto/sticker |
| Microsoft Graph webhook | `gateway/platforms/msgraph_webhook.py` |
| Generic Webhook / HTTP API | `gateway/platforms/webhook.py`, `api_server.py` |

### Plugin platforms (`plugins/platforms/`)

Discord, Google Chat, Home Assistant, IRC, LINE, Mattermost, ntfy, Photon, Raft, SimpleX, Microsoft Teams. (Discord also has a first-class agent tool — see Tools.)

### Cross-channel / gateway infrastructure

| Feature | File |
|---------|------|
| Cross-platform conversation continuity / channel mapping | `gateway/channel_directory.py`, `gateway/mirror.py` |
| Conversation pairing (link identities across channels) | `gateway/pairing.py`, `hermes_cli/pairing.py` |
| Session + context per channel | `gateway/session.py`, `gateway/session_context.py` |
| Streaming dispatch / events | `gateway/stream_dispatch.py`, `stream_consumer.py`, `stream_events.py` |
| Slash commands (shared CLI/gateway) | `gateway/slash_commands.py`, `slash_access.py` |
| Delivery / rich message store | `gateway/delivery.py`, `rich_sent_store.py`, `sticker_cache.py` |
| Relay transport (WS) | `gateway/relay/` (adapter, auth, transport, ws_transport) |
| WhatsApp identity, authz, response filters | `gateway/whatsapp_identity.py`, `authz_mixin.py`, `response_filters.py` |

---

## 2. Built-in Tools

Self-registering via `tools/registry.py`; grouped into toolsets in `toolsets.py`; exposed through `model_tools.py`. Tool names confirmed from `registry.register(name=...)` calls.

| Tool | Purpose | File |
|------|---------|------|
| `read_file`, `write_file`, `patch`, `search_files` | File ops + unified-diff patching | `tools/file_tools.py` |
| `terminal` | Shell exec: local / Docker / Modal / SSH / Singularity / Daytona backends | `tools/terminal_tool.py` |
| `process` | Long-running process registry/management | `tools/process_registry.py` |
| `read_terminal` | Read live terminal output | `tools/read_terminal_tool.py` |
| `execute_code` | Programmatic Tool Calling (PTC): LLM writes Python that calls tools over UDS/file RPC; collapses chains into one turn | `tools/code_execution_tool.py` |
| `delegate_task` | Spawn child sub-agents with isolated context + restricted toolsets; parent blocks | `tools/delegate_tool.py` |
| `mixture_of_agents` | Multi-model ensemble answering | `tools/mixture_of_agents_tool.py` |
| `web_search`, `web_extract` | Web search + content extraction | `tools/web_tools.py` |
| `x_search` | X/Twitter search | `tools/x_search_tool.py` |
| `browser_navigate/snapshot/click/type/scroll/back/press/get_images/vision/console` | Playwright browser automation | `tools/browser_tool.py` |
| `browser_cdp` | Chrome DevTools Protocol control | `tools/browser_cdp_tool.py` |
| `browser_dialog` | JS dialog handling | `tools/browser_dialog_tool.py` |
| `computer_use` | GUI computer-use (screenshot+click) | `tools/computer_use_tool.py` |
| `vision_analyze`, `video_analyze` | Image / video understanding | `tools/vision_tools.py` |
| `image_generate` | Image gen via FAL (see §4) | `tools/image_generation_tool.py` |
| `video_generate` | Video gen (FAL/xAI) | `tools/video_generation_tool.py` |
| `text_to_speech` | TTS (multi-provider, see §3) | `tools/tts_tool.py` |
| `memory` | Persistent agent memory CRUD | `tools/memory_tool.py` |
| `session_search` | FTS5 cross-session search + LLM summarization | `tools/session_search_tool.py` |
| `todo` | Task list management | `tools/todo_tool.py` |
| `kanban_*` (show/list/create/complete/block/unblock/comment/link/heartbeat) | Kanban board | `tools/kanban_tools.py` |
| `cronjob` | Schedule cron jobs (natural language) | `tools/cronjob_tools.py` |
| `clarify` | Ask user clarifying questions | `tools/clarify_tool.py` |
| `skills_list`, `skill_view` | Browse/read skills | `tools/skills_tool.py` |
| `skill_manage` | Create/edit skills | `tools/skill_manager_tool.py` |
| `discord`, `discord_admin` | Discord messaging + admin | `tools/discord_tool.py` |
| `feishu_doc_read` | Read Feishu docs | `tools/feishu_doc_tool.py` |
| `feishu_drive_*` (list_comments, replies, reply, add) | Feishu Drive comments | `tools/feishu_drive_tool.py` |
| `yb_query_group_info/members`, `yb_send_dm` | Yuanbao group/DM ops | `tools/yuanbao_tools.py` |
| `ha_list_entities/get_state/list_services/call_service` | Home Assistant control | `tools/homeassistant_tool.py` |
| MCP tools | Dynamic MCP server tool proxy + OAuth | `tools/mcp_tool.py`, `mcp_oauth.py`, `mcp_oauth_manager.py` |
| `tool_search` | Deferred-tool discovery / lazy schema load | `tools/tool_search.py` |
| Transcription | Voice-note STT (see §3) | `tools/transcription_tools.py` |
| Microsoft Graph | Auth + client for Outlook/Teams | `tools/microsoft_graph_auth.py`, `microsoft_graph_client.py` |
| `send_message` (internal) | Channel send helper (not agent-callable) | `tools/send_message_tool.py` |

### Tool support / security infrastructure
`tools/approval.py`, `write_approval.py`, `slash_confirm.py`, `path_security.py`, `url_safety.py`, `website_policy.py`, `threat_patterns.py`, `tirith_security.py`, `osv_check.py` (dependency CVE scan), `schema_sanitizer.py`, `tool_output_limits.py`, `tool_result_storage.py`, `budget_config.py`, `checkpoint_manager.py`, `interrupt.py`, `managed_tool_gateway.py` (Nous Portal routing), `credential_files.py`.

---

## 3. Voice

| Capability | Evidence |
|-----------|----------|
| CLI push-to-talk voice mode | `tools/voice_mode.py` — sounddevice capture, WAV, STT dispatch, interruptible TTS playback, 3s silence auto-stop, headless-safe lazy audio import, Termux hints |
| Discord voice | `tools/discord_tool.py` (voice channel type), realtime via `plugins/google_meet/realtime/` |
| Web Speech / browser voice | Web UI (`web/`) + `gateway/platforms/api_server.py` (realtime) |
| Voice-note transcription | `tools/transcription_tools.py`; providers managed by `agent/transcription_provider.py`, `transcription_registry.py` |
| Google Meet realtime voice bot | `plugins/google_meet/` (meet_bot, audio_bridge, realtime/openai_client) |

### TTS providers (`tools/tts_tool.py`, registered tool `text_to_speech`)
Edge TTS (`edge_tts`), ElevenLabs (premium, `ELEVENLABS_API_KEY`), OpenAI, MiniMax (voice cloning, `MINIMAX_API_KEY`), Mistral Voxtral (`voxtral-mini-tts-2603`), Google Gemini TTS (30 voices), xAI Grok TTS (OAuth/`XAI_API_KEY`), NeuTTS (local, `tools/neutts_synth.py`), KittenTTS (local 25MB int8), Piper (local neural VITS, 44 langs), plus custom.

### STT providers (`tools/transcription_tools.py`)
local faster-whisper (default, free), Groq Whisper, OpenAI Whisper (`whisper-1`/`gpt-4o-transcribe`), Mistral Voxtral (`voxtral-mini-latest`), ElevenLabs Scribe (`scribe_v2`).

---

## 4. Image Generation (`tools/image_generation_tool.py`, tool `image_generate`)

Routed via FAL.ai (provider in `plugins/image_gen/fal/`; also `openai`, `xai`, `krea`, `openai-codex`). Routing: `agent/image_routing.py`, `image_gen_provider.py`, `image_gen_registry.py`.

| Model | FAL endpoint |
|-------|--------------|
| FLUX 2 Klein 9B (default) | `fal-ai/flux-2/klein/9b` (+ `/edit`) |
| FLUX 2 Pro | `fal-ai/flux-2-pro` (+ `/edit`) |
| Z-Image Turbo | `fal-ai/z-image/turbo` |
| Nano Banana Pro (Gemini 3 Pro Image) | `fal-ai/nano-banana-pro` (+ `/edit`) |
| GPT-Image 1.5 | `fal-ai/gpt-image-1.5` (+ `/edit`) |
| GPT-Image 2 | `fal-ai/gpt-image-2` (+ `openai/gpt-image-2/edit`) |
| Ideogram V3 | `fal-ai/ideogram/v3` (+ `/edit`) |
| Recraft V4 Pro | `fal-ai/recraft/v4/pro/text-to-image` |
| Qwen Image | `fal-ai/qwen-image` (edit via `fal-ai/qwen-image-2/pro/edit`) |

Video generation parallel: `tools/video_generation_tool.py` + `plugins/video_gen/{fal,xai}`.

---

## 5. Automation / Cron

Native scheduler in `cron/`: `scheduler.py` (60s tick, file-lock single-fire), `jobs.py`, `scheduler_provider.py`, `blueprint_catalog.py`, `suggestion_catalog.py`, `suggestions.py`. Agent-facing tool `cronjob` (`tools/cronjob_tools.py`) accepts natural-language schedules. CLI: `hermes_cli/cron.py`. Cron-spawned agents run non-interactive (auto-approve) with protected toolsets disabled (`cronjob`, `messaging`, `clarify`) and prompt-injection guarding (`CronPromptInjectionBlocked`). Delivery to any platform; daily reports / nightly backups / weekly audits. Web UI: `web/src/pages/CronPage.tsx`, `ScheduleBuilder.tsx`, `AutomationBlueprints.tsx`.

---

## 6. UI Surfaces

| UI | Location | Features (from page/component files) |
|----|----------|--------------------------------------|
| Web Dashboard | `web/` (React/Vite/TS) | Chat, Channels, Config, Cron, Docs, Env, Files, Logs, MCP, Models, Pairing, Plugins, Profiles, ProfileBuilder, Sessions, Skills, System, Webhooks, Analytics; OAuth login, model picker, toolset config drawer, skill editor, theme/language switchers |
| Terminal UI (TUI) | `ui-tui/` (Ink/React TS) | streaming markdown, slash commands (core/session/ops/billing/credits/debug/setup), subagent tree, delegation store, gateway client + recovery, reasoning picker, virtual history, Termux layout |
| Desktop | `apps/desktop/` (Electron) | spawns Python backend, gateway WS probe, dashboard token auth, session windows, git worktrees, VS Code marketplace, OAuth net requests, auto-update, hardening |
| Bootstrap Installer | `apps/bootstrap-installer/` (Tauri/Rust) | guided install (welcome/progress/success/failure), PowerShell bootstrap |
| Curses UI | `hermes_cli/curses_ui.py` | terminal menus |

---

## 7. Developer / Training

| Feature | Evidence |
|---------|----------|
| Batch runner | `batch_runner.py` — runs agent over task sets, saves trajectories in ShareGPT `from/value` conversation format (`_convert_to_trajectory_format`), JSONL output |
| ShareGPT trajectory export | `batch_runner.py` (`conversations` entries), `agent/trajectory.py` |
| Trajectory compression | `trajectory_compressor.py`, `datagen-config-examples/trajectory_compression.yaml` |
| Atropos RL integration | `model_tools.py` (async bridge spins up event loop for "the gateway's async stack or Atropos's event loop"); test `tests/test_model_tools_async_bridge.py` |
| Datagen config examples | `datagen-config-examples/`: `web_research.yaml`, `example_browser_tasks.jsonl`, `run_browser_tasks.sh`, `trajectory_compression.yaml` |
| SWE harness | `mini_swe_runner.py` |
| MCP server mode | `mcp_serve.py` — expose Hermes as MCP server |

---

## 8. Plugins System

Plugin loader: `plugins/__init__.py`, `plugin_utils.py`; CLI `hermes_cli/plugins.py`/`plugins_cmd.py`. Each plugin is a dir with `__init__.py` exposing `register(ctx)`; `PluginContext` allows `register_tool` (delegates to tool registry), hooks, middleware, commands.

| Category | Plugins (`plugins/<cat>/`) |
|----------|------------------------------|
| model-providers | anthropic, gemini, xai, deepseek, openrouter, bedrock, azure-foundry, copilot, copilot-acp, openai-codex, nous, minimax, alibaba(+coding-plan), arcee, gmi, huggingface, kilocode, kimi-coding, novita, nvidia, ollama-cloud, opencode-zen, qwen-oauth, stepfun, xiaomi, zai, custom |
| memory | mem0, honcho (dialectic user modeling), supermemory, byterover, hindsight, holographic (local store/retrieval), openviking, retaindb |
| context_engine | `plugins/context_engine/` (pluggable context engines; core in `agent/context_engine.py`) |
| web (search) | tavily, exa, firecrawl, searxng, ddgs, brave_free, parallel, xai |
| image_gen | fal, openai, openai-codex, xai, krea |
| video_gen | fal, xai |
| browser | browser_use, browserbase, firecrawl |
| platforms | discord, google_chat, homeassistant, irc, line, mattermost, ntfy, photon, raft, simplex, teams |
| cron | chronos |
| observability | langfuse, nemo_relay |
| dashboard_auth | basic, nous, self_hosted |
| other | google_meet, spotify, teams_pipeline, security-guidance, disk-cleanup |

### ACP (Agent Client Protocol) — editor integration
`acp_adapter/` (server, session, tools, permissions, edit_approval, provenance, auth, events, entry/`__main__`). Registry manifest `acp_registry/agent.json` (id `hermes-agent`, `uvx hermes-agent[acp]`, `hermes-acp` entry). Editor-side ACP client also in `agent/copilot_acp_client.py`.

---

## 9. Other Notable Features

- **Security**: path sandboxing (`tools/path_security.py`), URL/website allowlists (`url_safety.py`, `website_policy.py`), prompt-injection/threat patterns (`threat_patterns.py`), Tirith policy engine (`tirith_security.py`), dependency CVE scan via OSV (`osv_check.py`), write/exec approval gates (`approval.py`, `write_approval.py`, `slash_confirm.py`), AIDefence-style scanning, SSL guard (`agent/ssl_guard.py`), secret redaction/scoping (`agent/redact.py`, `secret_scope.py`, `secret_sources/bitwarden.py`), `SECURITY.md`.
- **Memory & learning loop**: agent-curated memory with periodic nudges (`agent/curator.py`), autonomous skill creation, self-improving skills, FTS5 session search w/ LLM summarization, Honcho dialectic user modeling. Memory provider abstraction `agent/memory_manager.py`, `memory_provider.py`.
- **LSP integration**: `agent/lsp/` (manager, client, servers, install) for code intelligence.
- **Skills system**: `skills/` + `optional-skills/` (mlops training, osint, productivity/telephony/powerpoint, research); Skills Hub sync (`tools/skills_hub.py`, `skills_sync.py`, `skills_guard.py`, `skill_provenance.py`); agentskills.io standard.
- **Context engineering**: `agent/context_compressor.py`, `conversation_compression.py`, `context_references.py`, `context_engine.py`, `prompt_caching.py`, `iteration_budget.py`.
- **Model adapters / providers**: Anthropic, Bedrock, Gemini (native + Cloud Code), Codex (Responses API), Azure identity, OpenRouter, LM Studio reasoning, models.dev metadata — under `agent/`.
- **OpenClaw migration**: `hermes_cli/claw.py` imports settings/memories/skills/keys.
- **Constants/config**: `hermes_constants.py` (Termux detection etc.), `cli-config.yaml.example`, `toolset_distributions.py` (toolset bundling per distribution/profile).
- **Kanban swarm / multi-agent orchestration**: `hermes_cli/kanban_swarm.py`, `kanban_decompose.py`, `kanban_specify.py`.
- **Nous Portal**: unified billing for model + web search + image + TTS + browser (`agent/billing_view.py`, `credits_tracker.py`, `managed_tool_gateway.py`).
