# OpenClaw — Complete Feature Inventory

Source: `C:\E.D.I.T.H\reference\openclaw` (TS monorepo). Evidence cited from `package.json`, `openclaw.plugin.json`, app Swift sources, and `skills/*/SKILL.md`. Read-only survey.

OpenClaw is a plugin-driven personal-agent gateway. User-facing capabilities arrive through four delivery mechanisms:
1. **Channel adapters** (`extensions/<name>`) — messaging platforms the agent talks on.
2. **Provider/tool extensions** (`extensions/<name>`) — LLM, speech, media-gen, search, browser, memory.
3. **Companion apps** (`apps/*`) — macOS menubar app + iOS/Android/watchOS "nodes" exposing device sensors.
4. **Skill packs** (`skills/<name>/SKILL.md`) — markdown-defined CLI wrappers for ecosystem integrations (Hue, Notion, Spotify, Sonos, Apple apps, etc.).

---

## 1. Channel Adapters (messaging platforms)

All live under `extensions/<name>`. Library taken from each `package.json` `dependencies`.

| Channel | Library | Capabilities | Path |
|---|---|---|---|
| Discord | `@discordjs/voice`, `discord-api-types`, `libopus-wasm`, `ws` | Channels, DMs, slash commands, app events, voice, native commands/skills auto-enabled, markdown | `extensions/discord` |
| Slack | `@slack/bolt`, `@slack/web-api` | Channels, DMs, commands, app events | `extensions/slack` |
| Telegram | `grammy` 1.43 | Bot chats, channels, DMs | `extensions/telegram` |
| WhatsApp | `baileys` 7.0 (WhatsApp Web) | WhatsApp Web chats, QR auth, auth-dir override | `extensions/whatsapp` |
| Signal | `ws` (signal-cli HTTP daemon) | Account by E.164, talks to a Signal HTTP daemon (host/port config) | `extensions/signal` |
| iMessage | `imsg` CLI on signed-in Mac | iMessage + SMS via Messages.app DB; service auto/imessage/sms, region | `extensions/imessage` |
| Google Chat | webhook-based (typebox/zod) | Spaces + DMs, webhook URL/path, audience (app-url / project-number) | `extensions/googlechat` |
| Matrix | `matrix-js-sdk` 41 | Rooms + DMs, homeserver/user/token/device, initial sync limit | `extensions/matrix` |
| MS Teams | `@microsoft/teams.api`, `@microsoft/teams.apps`, `@azure/identity`, `express` | Bot conversations | `extensions/msteams` |
| Feishu/Lark | `@larksuiteoapi/node-sdk` | Chats + workplace tools (community maintained) | `extensions/feishu` |
| LINE | `@line/bot-sdk` 11 | LINE Bot API chats | `extensions/line` |
| Mattermost | `ws`, `zod` (REST/WS) | Channel plugin | `extensions/mattermost` |
| Nextcloud Talk | (REST) | Conversations | `extensions/nextcloud-talk` |
| Nostr | `nostr-tools` 2.23 | NIP-04 encrypted DMs, nsec/hex key, relay URLs | `extensions/nostr` |
| Synology Chat | (REST/webhook) | Channels + DMs | `extensions/synology-chat` |
| Twitch | `@twurple/api`, `@twurple/auth`, `@twurple/chat` | Chat + moderation workflows | `extensions/twitch` |
| Zalo (bot) | (bot/webhook) | Bot + webhook chats | `extensions/zalo` |
| Zalo (personal) | `zca-js` 2.1 | Personal-account integration | `extensions/zalouser` |
| QQ Bot | (REST/WS) | Group + DM workflows | `extensions/qqbot` |
| Tlon/Urbit | `@tloncorp/tlon-skill`, `@urbit/aura`, `@aws-sdk/client-s3` | Urbit chat, group channels, DM allowlist, auto-discovery | `extensions/tlon` |
| IRC | (raw IRC) | IRC channel plugin | `extensions/irc` |
| SMS | Twilio | Twilio text messages | `extensions/sms` |
| ClickClack | — | Channel plugin (internal/experimental) | `extensions/clickclack` |
| QA channel | — | Synthetic test channel | `extensions/qa-channel` |

Related telephony / call channels:
| Item | Library | Capabilities | Path |
|---|---|---|---|
| Voice Call | Twilio, Telnyx, Plivo (`commander`, `ws`) | Outbound/inbound phone calls | `extensions/voice-call` |
| Google Meet | Chrome or Twilio transports | Joins Meet calls as participant | `extensions/google-meet` |

---

## 2. Companion Apps / Mobile Nodes (`apps/*`)

Native Swift/Kotlin apps that pair to the gateway over WebSocket and expose device sensors as agent tools ("nodes"). Evidence from `apps/ios/Sources/**`, `apps/macos/Sources/**`.

| App | Platform | Capabilities (file evidence) | Path |
|---|---|---|---|
| macOS app | macOS (menubar) | Canvas windows (`CanvasManager`, `CanvasWindowController*`), Camera capture (`CameraCaptureService`), Dashboard window, Cron/scheduling UI (`CronJobEditor`, `CronSettings*`, `CronJobsStore`), Channels settings/config UI, Gateway process mgmt + autostart launch agent, device-pairing approval, Exec approval prompts/allowlist, cost/usage menu, audio input observer | `apps/macos` |
| iOS/iPadOS node | iOS | Camera (`Camera/CameraController`), Screen capture + record (`Screen/ScreenController`, `ScreenRecordService`, `ScreenWebView`), GPS/location (`Location/LocationService`, `SignificantLocationMonitor`), Motion (`Motion/MotionService`), Voice wake-words (`Settings/VoiceWakeWordsSettingsView`, `Status/VoiceWakeToast`), Realtime talk relay / push-to-talk (`Voice/RealtimeTalkRelaySession`, `TalkProTab`), Canvas surface (`Model/NodeAppModel+Canvas`), Photo library, Contacts, Calendar (EventKit), Reminders, Push notifications + exec-approval push, Live Activities, QR-scanner pairing (`Onboarding/QRScannerView`), capability router (`NodeCapabilityRouter`), Command Center, Skill workshop, Workboard | `apps/ios` |
| watchOS app | watchOS | Watch reply coordinator, watch connectivity transport, watch messaging | `apps/ios/WatchApp`, `apps/ios/Sources/Services/Watch*` |
| Android node | Android (Kotlin/Gradle) | Android node app (camera/screen/GPS analog), benchmark module | `apps/android` |
| macos-mlx-tts | macOS | On-device MLX text-to-speech engine | `apps/macos-mlx-tts` |
| swabble | macOS CLI | Speech pipeline + wake-word gate (`SpeechPipeline`, `WakeWordGate`), mic/transcribe/serve commands, hook executor | `apps/swabble` |
| shared / OpenClawKit | shared | Shared Swift kit across apps | `apps/shared/OpenClawKit` |

Pairing/control extensions backing the nodes:
| Item | Capabilities | Path |
|---|---|---|
| Device Pairing | Generates setup codes / QR; approves pairing requests; `/pair` slash; public WS URL | `extensions/device-pair` |
| Phone Control | Arm/disarm high-risk phone-node commands (camera/screen/writes) with auto-expiry; `/phone` slash | `extensions/phone-control` |
| Bonjour | mDNS gateway discovery for nodes | `extensions/bonjour` |
| Canvas | HTML canvas surface on connected nodes (Lit + `@a2ui/lit`, chokidar file watch, ws); navigate/eval/snapshot | `extensions/canvas` |

---

## 3. Browser Automation

| Item | Engine | Capabilities | Path |
|---|---|---|---|
| Browser tool | `playwright-core` 1.60 + MCP SDK, express, ws | Headless/driven browser tool plugin exposed to agent (navigate, scrape, automate); also drives `web-readability`/`web-content-core` | `extensions/browser` |
| Diff viewer | `playwright-core` | Read-only diff viewer + file renderer for agents | `extensions/diffs` (+ `diffs-language-pack` syntax highlighting) |
| QA Lab | `playwright-core` | Private debugger UI + scenario runner | `extensions/qa-lab` |
| Web Readability | local Readability | Local article extraction | `extensions/web-readability` |

---

## 4. Voice / TTS / STT / Media Generation

### Speech (TTS / STT / media understanding)
| Item | Type | Path |
|---|---|---|
| ElevenLabs | TTS speech provider | `extensions/elevenlabs` |
| Azure Speech | TTS/STT | `extensions/azure-speech` |
| Microsoft (speech) | TTS | `extensions/microsoft` |
| Inworld | speech | `extensions/inworld` |
| Gradium | speech | `extensions/gradium` |
| Deepgram | media-understanding (STT) | `extensions/deepgram` |
| Groq | media-understanding | `extensions/groq` |
| SenseAudio | media-understanding | `extensions/senseaudio` |
| Local CLI TTS | local TTS via CLI | `extensions/tts-local-cli` |
| Talk Voice | Talk voice selection (`/voice` list/set) | `extensions/talk-voice` |
| speech-core | speech runtime package | `packages/speech-core` |
| media-understanding-core | media understanding runtime | `extensions/media-understanding-core`, `packages/media-understanding-common` |

### Image / Video / Audio generation
| Item | Type | Path |
|---|---|---|
| image-generation-core | image-gen runtime | `extensions/image-generation-core` |
| video-generation-core | video-gen runtime | `extensions/video-generation-core` |
| ComfyUI | image-gen provider | `extensions/comfy` |
| fal | media (image/video) provider | `extensions/fal` |
| Runway | video provider | `extensions/runway` |
| PixVerse | video provider | `extensions/pixverse` |
| Alibaba Model Studio | video provider | `extensions/alibaba` |
| Vydra | media provider | `extensions/vydra` |
| BytePlus / Volcengine | provider (media-capable) | `extensions/byteplus`, `extensions/volcengine` |
| media-generation-core | shared media-gen runtime | `packages/media-generation-core`, `packages/media-core` |

---

## 5. Hardware / Ecosystem Integrations

These ship primarily as **skill packs** (`skills/<name>/SKILL.md`) wrapping CLIs/APIs, plus a few extensions. From SKILL.md `description` frontmatter.

| Integration | Mechanism | Capabilities | Path |
|---|---|---|---|
| Philips Hue | OpenHue CLI | Control lights + scenes | `skills/openhue` |
| Sonos | sonoscli | Discover/status/play/volume/group | `skills/sonoscli` |
| BluOS | blu CLI | Discovery, playback, grouping, volume | `skills/blucli` |
| Spotify | spogo / spotify_player | Terminal playback + search | `skills/spotify-player` |
| Eight Sleep | eightctl | Pod status, temperature, alarms, schedules | `skills/eightctl` |
| RTSP/ONVIF cameras | camsnap | Capture frames/clips | `skills/camsnap` |
| Apple Notes | memo CLI | Create/view/edit/delete/search/move/export | `skills/apple-notes` |
| Apple Reminders | remindctl | List/add/edit/complete/delete reminders + lists | `skills/apple-reminders` |
| Bear Notes | grizzly CLI | Create/search/manage notes | `skills/bear-notes` |
| Things 3 | (CLI) | Todos/inbox/today/projects/areas/tags | `skills/things-mac` |
| Notion | Notion CLI/API | Pages, markdown, data sources, files, comments, search, raw API | `skills/notion` |
| Obsidian | obsidian CLI | Read/search/create/edit notes, tasks, links, properties, plugins | `skills/obsidian` |
| Trello | Trello REST API | Boards, lists, cards | `skills/trello` |
| Gmail/Calendar/Drive/Contacts/Sheets/Docs | gog (Google Workspace CLI) | Full Workspace ops | `skills/gog` |
| IMAP/SMTP mail | himalaya CLI | List/read/search/compose/reply/forward/move/delete | `skills/himalaya` |
| Twitter/X | xurl CLI | Posts, replies, search, DMs, media upload, followers, raw v2 API | `skills/xurl` |
| GitHub | gh CLI | Issues, PRs, CI logs, reviews, releases, repos, gh api | `skills/github`, `skills/gh-issues` |
| 1Password | op CLI | Sign-in, desktop integration, read/inject secrets | `skills/1password` |
| Google Places | goplaces | Text search, place details, reviews | `skills/goplaces` |
| Weather | web_fetch / wttr.in | Current + forecast | `skills/weather` |
| Food delivery | ordercli | Foodora order status (Deliveroo WIP) | `skills/ordercli` |
| Slack (tool) | message-tool | send/read/edit/delete, react, pin, emoji | `skills/slack` |
| Discord (tool) | message-tool | send/read/edit/delete, react, poll, pin, thread, presence | `skills/discord` |
| iMessage (tool) | imsg CLI | List chats, history, send | `skills/imsg` |
| WhatsApp (tool) | wacli | Send 3rd-party messages, sync/search history | `skills/wacli` |
| macOS UI automation | Peekaboo CLI | Capture + automate macOS UI | `skills/peekaboo` |
| Voice call | OpenClaw voice-call | Start voice calls | `skills/voice-call` |

Media/utility skill packs: `meme-maker`, `gifgrep`, `diagram-maker` (SVG/Excalidraw), `nano-pdf`, `video-frames` (ffmpeg), `songsee` (audio spectrograms), `summarize` (URL/YouTube/PDF), `openai-whisper` + `openai-whisper-api` (STT), `sherpa-onnx-tts`, `sag` (ElevenLabs say), `weather`, `tmux`, `mcporter` (MCP servers), `coding-agent` (delegate to Codex/Claude Code/OpenCode), `oracle` (second-model review), `spike`, `healthcheck`, `clawhub` (skill registry install/publish), `skill-creator`.

Search providers (extensions): Brave (`brave`), DuckDuckGo (`duckduckgo`), Exa (`exa`), Tavily (`tavily`), Perplexity (`perplexity`), SearXNG (`searxng`), Parallel (`parallel`), Firecrawl (`firecrawl`).

Document/web extraction extensions: `document-extract`, `web-readability`, `web-content-core` (pkg).

---

## 6. Skills & Memory

| Item | Mechanism | Capabilities | Path |
|---|---|---|---|
| memory-core | core search | Core memory search plugin | `extensions/memory-core` |
| memory-lancedb | `@lancedb/lancedb` + `apache-arrow` + OpenAI embeddings | Long-term memory: auto-recall, auto-capture, vector search | `extensions/memory-lancedb` |
| memory-wiki | persistent wiki | Persistent markdown wiki plugin | `extensions/memory-wiki` |
| active-memory | blocking sub-agent | Runs bounded memory sub-agent before replies; injects relevant memory into prompt context; circuit breaker, prompt styles, query modes | `extensions/active-memory` |
| memory-host-sdk | pkg | Memory host SDK for plugins | `packages/memory-host-sdk` |
| Skills system | markdown SKILL.md packs | File-based markdown skills (56 packs); `skill-creator` to author, `clawhub` to install/publish, `model-usage`/`session-logs` introspection | `skills/*` |
| Session logs | jq over session JSON | Search/analyze own/parent conversation logs | `skills/session-logs` |
| Canvas skill | canvas hosts | Present HTML on node canvases, navigate/eval/snapshot | `skills/canvas` |

---

## 7. Other: Dashboards, Auth, Scheduling, Workflows, Diagnostics

| Item | Capabilities | Path |
|---|---|---|
| Workboard | Dashboard workboard plugin | `extensions/workboard` |
| Cron / Scheduling UI | macOS Cron editor + jobs store; iOS AgentProTab+Cron | `apps/macos` (`CronSettings*`), `apps/ios/.../AgentProTab+Cron` |
| Lobster | Typed workflow pipelines, resumable approvals | `extensions/lobster` |
| TaskFlow | Durable multi-step detached jobs, waits, child tasks | `skills/taskflow`, `skills/taskflow-inbox-triage` |
| Webhooks | Webhook bridge plugin | `extensions/webhooks` |
| Admin HTTP RPC | Admin HTTP RPC endpoint | `extensions/admin-http-rpc` |
| File transfer | `file_fetch`, `dir_list`, `dir_fetch`, `file_write` | `extensions/file-transfer` |
| Diagnostics | OpenTelemetry + Prometheus exporters | `extensions/diagnostics-otel`, `extensions/diagnostics-prometheus` |
| Policy / Doctor | Workspace conformance checks | `extensions/policy` |
| Thread ownership | Thread ownership routing | `extensions/thread-ownership` |
| Migrations | Claude / Hermes import | `extensions/migrate-claude`, `extensions/migrate-hermes` |
| oc-path | `oc://` workspace path scheme | `extensions/oc-path` |
| OpenShell | NVIDIA OpenShell sandbox CLI backend, SSH exec, mirrored workspaces | `extensions/openshell` |
| Coding-agent backends | Codex app-server harness + fleet supervision; ACP runtime | `extensions/codex`, `extensions/codex-supervisor`, `extensions/acpx`, `packages/acp-core` |
| Copilot | GitHub Copilot agent runtime (JSON-RPC to Copilot CLI) | `extensions/copilot`, `extensions/copilot-proxy`, `extensions/github-copilot` |
| OpenProse | VM skill pack (slash command + telemetry) | `extensions/open-prose` |
| tokenjuice | Exec output compaction | `extensions/tokenjuice` |

### LLM Provider extensions (model access — not user-facing channels but enable all capability)
Anthropic (+ Vertex), OpenAI, Google, xAI, Mistral, Cohere, DeepSeek, DeepInfra, Groq, Cerebras, Together, Fireworks, OpenRouter, Ollama, LM Studio, llama.cpp, vLLM, SGLang, LiteLLM, Amazon Bedrock (+ Mantle), Azure/Microsoft Foundry, Cloudflare AI Gateway, Vercel AI Gateway, Hugging Face, Perplexity, Moonshot, Kimi, Qwen, Qianfan, Zai, Z.AI, Novita, NVIDIA, Venice, StepFun, MiniMax, Arcee, Synthetic, Chutes, GMI, Tencent, Volcengine, BytePlus, Xiaomi, Alibaba, Voyage (embeddings), Kilocode, OpenCode (+ Go), Vydra — all under `extensions/<name>`.

### Core runtime packages (`packages/`)
`agent-core`, `llm-core`, `llm-runtime`, `model-catalog-core`, `gateway-client`, `gateway-protocol`, `sdk`, `plugin-sdk`, `plugin-package-contract`, `markdown-core`, `media-core`, `media-generation-core`, `media-understanding-common`, `memory-host-sdk`, `net-policy`, `normalization-core`, `speech-core`, `terminal-core`, `tool-call-repair`, `web-content-core`, `acp-core`.

---

## Coverage Notes
- ~110 extensions, 22 core packages, 56 skill packs, 6 app targets inventoried.
- Channel libraries verified directly from each `package.json` (Baileys, grammY, discord.js voice, @slack/bolt, matrix-js-sdk, @line/bot-sdk, nostr-tools, @twurple, @larksuiteoapi, @microsoft/teams, zca-js, @urbit/aura).
- Device-sensor capabilities verified from Swift source filenames in `apps/ios/Sources` and `apps/macos/Sources`.
- Ecosystem integrations (Hue, Sonos, Spotify, Notion, Apple apps, Things 3, etc.) are skill-pack CLI wrappers, not TS extensions — reimplementation means shipping the CLI + a SKILL.md.
