# OpenClaw Architecture Reference

Research target: `C:\E.D.I.T.H\reference\openclaw` (OpenClaw `v2026.6.8`, a TypeScript pnpm
monorepo). Read-only investigation; no reference files were modified.

## Provenance note (read this first)

The checkout at `reference/openclaw` is a **sparse/published tree**: it contains the root
package manifest, the launcher, and the `.agents/` skills+docs corpus, but **not** the
compiled `dist/` or the full `src/`, `packages/`, `extensions/`, `ui/` source trees. Every
claim below is anchored to one of these readable artifacts:

- `reference/openclaw/package.json` (2024 lines: `bin`, `exports`, `scripts`, `dependencies`, `engines`)
- `reference/openclaw/pnpm-workspace.yaml` (workspace globs, overrides, allowBuilds)
- `reference/openclaw/openclaw.mjs` (the `openclaw` bin launcher, 680 lines)
- `reference/openclaw/.agents/skills/**/SKILL.md` and
  `.agents/skills/claw-score/references/completeness/*.md` (architecture rubrics and
  debugging skills that cite real internal `src/...` and `packages/...` paths and RPC names)

Where a subsystem's internal source is not physically present in this sparse tree, the
internal file paths cited (e.g. `src/gateway/server.ts`, `src/agents/code-mode.ts`) come
from the `.agents` docs that reference them by exact path; those are flagged as
**cited-but-not-resident**. Items reconstructed from the surface taxonomy plus general
OpenClaw knowledge (not directly in this tree) are explicitly marked **[reconstructed]**.

---

## 1. Gateway daemon boot, Node runtime, and control plane

### 1.1 The `openclaw` bin launcher (`openclaw.mjs`)

`package.json` declares the binary:

```json
"bin": { "openclaw": "openclaw.mjs" },
"type": "module",
"main": "dist/index.js",
"engines": { "node": ">=22.19.0" },
"packageManager": "pnpm@11.2.2+sha512..."
```

`openclaw.mjs` is a pure-Node ESM bootstrap that runs **before** any TypeScript runtime
loads. Its responsibilities, in order:

1. **Node version gate** (`openclaw.mjs:11-53`): hard minimum `MIN_NODE_MAJOR = 22`,
   `MIN_NODE_MINOR = 19`. `ensureSupportedNodeVersion()` prints an `nvm`-based remediation
   message and `process.exit(1)` if too old.
2. **Version fast-path** (`tryOutputLauncherVersion`, `:55, :470-617`): `--version/-V/-v`
   prints `OpenClaw <version> (<commit>)` by reading `package.json`, `dist/build-info.json`,
   and the git `HEAD`/`packed-refs` directly — without booting the runtime.
3. **Compile-cache management** (`:59-279`): detects a source checkout
   (`./.git` or `./src/entry.ts`) vs a packaged install, and either disables Node's compile
   cache or respawns the process with `NODE_COMPILE_CACHE` pointed at a per-version cache
   dir under `os.tmpdir()/node-compile-cache/openclaw/<version>/<installMarker>`. There is a
   Windows-Node-24 deadlock guard (`shouldSkipCompileCacheForWindowsNode24`, `:34-36`).
   Respawn uses `spawn(command, args, { stdio: "inherit" })` with signal forwarding
   (`runRespawnedChild`, `:110-205`) for `SIGTERM/SIGINT/SIGHUP/SIGQUIT` (POSIX) or
   `SIGTERM/SIGINT/SIGBREAK` (Windows).
4. **Help fast-path** (`:371-662`): bare `--help`, and `browser/secrets/nodes --help`, are
   served from precomputed `dist/cli-startup-metadata.json` without loading the runtime,
   unless config contains `plugins`/`$include` (`shouldDeferRootHelpToRuntimeEntry`).
5. **Entry handoff** (`:664-679`): `await tryImport("./dist/entry.js")` (then `.mjs`); on
   miss it throws the "missing dist/entry — run `pnpm build`" message
   (`buildMissingEntryErrorMessage`, `:354-369`). So **`dist/entry.js` (compiled from
   `src/entry.ts`) is the true runtime entrypoint.**

The CLI itself is built on `commander` (`package.json` deps: `"commander": "14.0.3"`) and
the launcher references `dist/cli/program/root-help.js`.

### 1.2 Node runtime, gateway process, daemonization

- The gateway is started by `openclaw gateway` (the `.agents` debugging skill uses exactly
  `OPENCLAW_DEBUG_MODEL_TRANSPORT=1 openclaw gateway`,
  `.agents/skills/openclaw-debugging/SKILL.md:36-39`). `package.json` `"start": "node openclaw.mjs"`.
- **Service install / daemon lifecycle** is OS-specific under `src/daemon/`
  (cited-but-not-resident): `package.json:1854` runs
  `src/daemon/launchd.test.ts`, `src/daemon/runtime-paths.test.ts`,
  `src/daemon/runtime-binary.test.ts`, plus `src/infra/brew.test.ts` and
  `src/infra/stable-node-path.test.ts`. So macOS uses **launchd**, and a stable Node path is
  resolved/pinned for the service. The `gateway-runtime` rubric lists lifecycle stages:
  "Foreground startup, Service installation, Restart and stop, Service status, Bind and port
  settings, Config reload, Multi-gateway isolation"
  (`.agents/.../completeness/gateway-runtime.md:41`).

### 1.3 Control plane: WebSocket + HTTP, protocol package, port

- There is a dedicated **gateway protocol package**: `packages/gateway-protocol/`
  (`package.json:1728` runs `packages/gateway-protocol/src/connect-error-details.test.ts`).
  The `gateway-runtime` rubric describes the WebSocket handshake:
  "WebSocket transport, Connect challenge, Connect request, Protocol version negotiation,
  hello-ok snapshot, Startup retry, Session limits, Plugin surface URLs"
  (`gateway-runtime.md:43`), and a published/runtime-validated schema with
  "Swift client models, Version negotiation, Client transport defaults"
  (`gateway-runtime.md:39`).
- Transport libraries (`package.json` deps): **`ws` 8.21.0** (WebSocket server/client),
  **`express` 5.2.1** for the HTTP surface, **`web-push` 3.6.7** for push tokens,
  `@homebridge/ciao` 1.3.9 for mDNS endpoint discovery, `qrcode` 1.5.4 for pairing QR codes.
- Gateway server/client source (cited-but-not-resident): `src/gateway/server.ts`,
  `src/gateway/client.ts`, `src/gateway/reconnect-gating.ts`
  (`package.json:1728` test:auth:compat).
- HTTP API surface (from `gateway-runtime.md:32-34`): OpenAI-compatible APIs, a Tool
  invocation API, an Admin API, and **hook ingress** endpoints `POST /hooks/wake` and
  `POST /hooks/agent` (`automation-cron-hooks-tasks-polling.md:9`). Hosted web surfaces:
  Control UI, WebChat, plugin web routes, Canvas/A2UI routes.
- **Port / bind**: "Bind and port settings" is an explicit gateway-lifecycle capability
  (`gateway-runtime.md:41`); network modes are "Loopback and LAN access, Tailnet access, SSH
  tunnels" (`gateway-runtime.md:36`). **[reconstructed]** The default control-plane port is
  configured in `~/.openclaw/openclaw.json` and is commonly `8765`/`8787`-class loopback; the
  exact default is not present in this sparse tree — treat the bind/port as
  config-driven, defaulting to loopback with non-loopback access gated by auth (see §7).

---

## 2. Session management (keying, task queue, concurrency)

Source lives under `src/gateway/` and session/context modules (cited-but-not-resident,
proven by `package.json` test entries and the `session-memory-and-context-engine` rubric).
The Docker lane `session-runtime-context` (`package.json:1814`,
`scripts/e2e/session-runtime-context-docker.sh`) exercises this end-to-end.

- **Session routing / conversation binding**: the rubric category is
  "Session Routing, Conversation Binding" plus "Cross-client History, Session Parity"
  (`session-memory-and-context-engine.md:11,16`). The plugin-sdk exports expose the binding
  primitives directly: `plugin-sdk/conversation-binding-runtime`,
  `plugin-sdk/conversation-runtime`, `plugin-sdk/thread-bindings-runtime`,
  `plugin-sdk/thread-bindings-session-runtime`, and `plugin-sdk/model-session-runtime`
  (`package.json:506-521, 470-473`).
- **Main vs group keying**: group/room policy is a first-class runtime concern —
  `plugin-sdk/runtime-group-policy` (`package.json:466-469`) and
  `plugin-sdk/access-groups` (`:710-713`). The multi-agent rubric requires
  "Conversation Routing: agent selection, route precedence, default fallback, peer
  overrides" and "Account Routing" (`multi-agent-orchestration.md:28-29`).
  **[reconstructed]** Sessions are keyed by (channel, account, conversation/thread id),
  where a direct/main chat keys to a single per-peer session and a group/room keys to a
  shared room session governed by group policy (mention-gating, allowlists). The
  `channel-message-flows` skill confirms thread preservation and delivery ordering are
  tracked as session evidence (`channel-message-flows/SKILL.md:31`).
- **Task queue / concurrency**: the SDK ships dedicated runtimes —
  `plugin-sdk/concurrency-runtime`, `plugin-sdk/delivery-queue-runtime`,
  `plugin-sdk/async-lock-runtime`, `plugin-sdk/dedupe-runtime`,
  `plugin-sdk/pair-loop-guard-runtime`, `plugin-sdk/reply-dedupe`
  (`package.json:418-429, 410-413, 402-405, 342-345`). The automation rubric lists
  "Background Tasks and Flows: Task list/show/cancel, Task notifications, Task audit … Task
  pressure status, Managed flows" (`automation-cron-hooks-tasks-polling.md:11`). So
  concurrency is bounded per-session via async locks + a delivery queue, with idempotent
  side effects and de-dupe ("Idempotent side effects", `gateway-runtime.md:34`).

---

## 3. Agent loop, context assembly, LLM providers, tool-call loop

### 3.1 Context engine and instruction files (SOUL.md / AGENTS.md / TOOLS.md / daily logs)

- The `session-memory-and-context-engine` rubric defines the assembly surface:
  "Context Engine and Runtime Assembly", "Instruction Profile and Context Visibility",
  "Memory Files, Tools, and Active Memory: Memory Backend Storage, Memory Files, Tools,
  Active Memory" (`session-memory-and-context-engine.md:10-15`).
- AGENTS.md is treated as the **canonical agent-instruction file**, with aliases
  (`CLAUDE.md`, `AGENT.md`, `.cursorrules`, `.agent/`, `.agents/`, `.pi/`) kept as
  compatibility surfaces; "AGENTS.md is treated as canonical when present"
  (`technical-documentation/SKILL.md:23`,
  `technical-documentation/references/agent-and-contributing.md:34-36`).
- **[reconstructed]** SOUL.md (persona/identity), AGENTS.md (operating instructions),
  TOOLS.md (tool guidance), and per-day **daily log** files live in the agent's workspace
  (`~/.openclaw/workspace/...`, see §4) and are read by the context engine into the
  "Instruction Profile" each turn. These specific filenames are not resident in this sparse
  tree; the **mechanism** (instruction-profile assembly from workspace memory files) is
  confirmed by the rubric and by the `plugin-sdk/skills-runtime` /
  `plugin-sdk/agent-config-primitives` exports (`package.json:550-553, 706-709`).

### 3.2 LLM providers

First-party provider SDKs are direct dependencies (`package.json:1927-1981`):

- `@anthropic-ai/sdk` 0.100.1 (pinned via override at `pnpm-workspace.yaml:96`)
- `openai` 6.39.1 (also drives OpenAI-compatible + Codex paths)
- `@google/genai` 2.7.0
- `@mistralai/mistralai` 2.2.5
- `@modelcontextprotocol/sdk` 1.29.0 (MCP, see §5)
- `@agentclientprotocol/sdk` 0.22.1 + patched `claude-agent-acp` (ACP — external CLI agents)

Provider/runtime selection is described in `agent-runtime-and-provider-execution.md`:
"Model and Runtime Selection", "Hosted Provider Execution", "Local and Self-hosted
Providers", "Provider Auth … Auth failover, Provider fallback recovery, Rate-limit and
capacity recovery" (`agent-runtime-...md:8-17`). Local/self-hosted providers (Ollama, vLLM,
SGLang, LM Studio) get their own surface (`local-model-providers-...md`) and SDK export
`plugin-sdk/lmstudio-runtime`, `plugin-sdk/self-hosted-provider-setup`
(`package.json:186-201`).

### 3.3 Tool-call loop and "code mode"

The debugging skill names the exact runtime files (cited-but-not-resident):

```
Model payload + Responses stream:  src/agents/openai-transport-stream.ts
Guarded fetch/timing:              src/agents/provider-transport-fetch.ts
OpenAI/Codex provider wrappers:    src/agents/pi-embedded-runner/openai-stream-wrappers.ts
Tool construction, Tool Search,
  code-mode activation:            src/agents/pi-embedded-runner/run/attempt.ts
Code-mode runtime and worker:      src/agents/code-mode.ts, src/agents/code-mode.worker.ts
Tool Search catalog:              src/agents/tool-search.ts
```
(`.agents/skills/openclaw-debugging/SKILL.md:82-94`)

Key behaviors:
- The embedded agent runner is **`pi-embedded-runner`** (built on `@earendil-works/pi-tui`
  0.78.0, `package.json:1932`). A turn assembles model-visible tools, optionally activates
  **Tool Search** (a dynamic catalog) and **code mode** (where the model is given exactly
  `exec` and `wait` tools that run JS in a `quickjs-wasi` 3.0.0 sandbox), then streams the
  provider response (SSE for OpenAI Responses), handles tool calls, and reports usage.
  "Code mode means exactly `exec` and `wait` only after it actually activates"
  (`SKILL.md:62-64`).
- Streaming/transport is observable via `OPENCLAW_DEBUG_MODEL_TRANSPORT`,
  `OPENCLAW_DEBUG_MODEL_PAYLOAD=tools|summary|full-redacted`, `OPENCLAW_DEBUG_SSE=events|peek`,
  `OPENCLAW_DEBUG_CODE_MODE=1` (`SKILL.md:44-52`).
- Turn lifecycle from the rubric: "Turn startup and runtime choice, Session and run
  coordination, Abort and terminal outcomes" plus "External harness selection, Subagent
  turns" (`agent-runtime-...md:8-9`). Tool parsing uses `partial-json` 0.1.7 and `zod` 4.4.3
  for schema validation.

### 3.4 External/CLI runtimes and subagents

OpenClaw can delegate a turn to an **external harness** over ACP — Claude Code CLI,
OpenAI Codex, Gemini CLI, Droid, OpenCode — visible in the live test matrix
(`package.json:1758-1772`: `OPENCLAW_LIVE_ACP_BIND_AGENT=claude|codex|droid|gemini|opencode`,
`OPENCLAW_LIVE_CLI_BACKEND_MODEL=claude-cli/...`, `google-gemini-cli/...`). SDK export
`plugin-sdk/acp-runtime`, `plugin-sdk/cli-backend`, `plugin-sdk/agent-harness*`
(`package.json:638-651, 594-617`).

---

## 4. `~/.openclaw/workspace` layout and config

From the launcher's config resolution (`openclaw.mjs:393-457`):

- **Home/state resolution**: `OPENCLAW_HOME` (supports `~` expansion) overrides the OS home;
  otherwise `HOME`/`USERPROFILE`/`os.homedir()`.
- **Config path precedence** (`resolveLauncherConfigPaths`, `:422-439`):
  1. `OPENCLAW_CONFIG_PATH` (explicit file), else
  2. `OPENCLAW_STATE_DIR` → `<stateDir>/openclaw.json` then `<stateDir>/clawdbot.json`, else
  3. `~/.openclaw/openclaw.json`, `~/.openclaw/clawdbot.json`,
     `~/.clawdbot/openclaw.json`, `~/.clawdbot/clawdbot.json` (legacy `clawdbot` fallback).
- **Plugin installs live under the state dir**, not the config dir: "Plugin npm installs live
  under that state dir (`npm/node_modules/...`), not under `OPENCLAW_CONFIG_DIR`"
  (`.agents/skills/crabbox/SKILL.md:434-437`). Test isolation uses
  `OPENCLAW_STATE_DIR=$(mktemp -d)`.
- Bundled-plugin discovery honors `OPENCLAW_BUNDLED_PLUGINS_DIR` /
  `OPENCLAW_DISABLE_BUNDLED_PLUGINS` (`openclaw.mjs:443-445`).

**[reconstructed]** workspace layout (mechanism confirmed; exact subdir names not resident):

```
~/.openclaw/
  openclaw.json            # primary config (JSON5/JSON; see config-schema export)
  npm/node_modules/...     # installed plugins (confirmed by crabbox skill)
  workspace/<agent>/       # per-agent isolated workspace (multi-agent rubric: "workspace separation")
    SOUL.md / AGENTS.md / TOOLS.md   # instruction profile files [reconstructed]
    logs/daily/<date>.md             # daily logs [reconstructed]
  media/                   # media store (plugin-sdk/media-store export)
  cron/ , tasks/           # cron + task state (cron-store-runtime export)
  <sqlite db>              # session/memory backend (kysely + sqlite-vec)
```

Config is typed and schema-validated: SDK exports `plugin-sdk/config-schema`,
`config-types`, `config-contracts`, `config-mutation`, `allowlist-config-edit`
(`package.json:302-329, 718-721`); secret references via `plugin-sdk/secret-ref-runtime`,
`secret-file-runtime`, `secret-provider-integration` (`:566-577`). Config is read with
`json5` and `yaml`, secrets via `dotenv`.

Multi-agent isolation (`multi-agent-orchestration.md:27`): "workspace separation, state
separation, auth separation, session separation, and tool profiles" — each added agent gets
its own workspace, credentials, and sessions with no implicit cross-agent leakage.

---

## 5. MCP integration, GitHub automation, ClawSweeper

### 5.1 MCP (Model Context Protocol)

- Dependency: `@modelcontextprotocol/sdk` 1.29.0 (`package.json:1939`). OpenClaw both
  **consumes** MCP servers (as tools) and **projects** its own tools as MCP — SDK export
  `plugin-sdk/codex-mcp-projection` (`package.json:598-601`).
- E2E lanes: `mcp-channels` (`package.json:1788`), `mcp-code-mode-gateway` and its live
  variant (`:1782, 1789`), `pi-bundle-mcp-tools` / `agent-bundle-mcp-tools`
  (`:1740`). The product profile explicitly covers "MCP channels"
  (`.agents/skills/openclaw-testing/SKILL.md:532`). MCP tools can be surfaced into code mode.

### 5.2 GitHub automation

- General-purpose CI/release automation runs through GitHub Actions workflows referenced
  throughout `openclaw-testing/SKILL.md` (e.g. `full-release-validation.yml`,
  `openclaw-release-checks.yml`, `package-acceptance.yml`, `ci-check-testbox.yml`).
- A large family of repo-maintenance "crawl" skills exist under `.agents/skills/` (gitcrawl,
  discrawl, notcrawl, graincrawl, slacrawl) plus PR/issue maintainers
  (`openclaw-pr-maintainer`, `tag-duplicate-prs-issues`, `security-triage`).

### 5.3 ClawSweeper (the maintenance bot)

Fully documented in `.agents/skills/clawsweeper/SKILL.md`. It is a **separate repo/app**
(`~/Projects/clawsweeper`, the `clawsweeper` GitHub App) that sweeps OpenClaw issues/PRs and
commits, runs reviews, and opens guarded fix PRs:

- **Token boundary** (`SKILL.md:42-49`): Codex/review workers run with **stripped secret/token
  env**; only deterministic scripts hold short-lived GitHub-App tokens for comments, labels,
  branch pushes, PR creation, and merges. **Merge and write gates default closed.**
- **Reports** are markdown: `records/<repo-slug>/commits/<sha>.md`,
  `records/<repo-slug>/items/<number>.md` (`SKILL.md:54, 89-91`).
- **Gates** are GitHub repo variables that default off:
  `CLAWSWEEPER_ALLOW_EXECUTE`, `CLAWSWEEPER_ALLOW_FIX_PR`, `CLAWSWEEPER_ALLOW_MERGE`,
  `CLAWSWEEPER_ALLOW_AUTOMERGE`, `CLAWSWEEPER_COMMENT_ROUTER_EXECUTE` (`SKILL.md:172-188`).
- **Maintainer control** via `@clawsweeper <command>` mentions (status, review, re-review,
  fix ci, autofix, automerge, approve, stop, …); freeform mentions dispatch read-only
  assist reviews that cannot directly mutate GitHub (`SKILL.md:196-228`). Repair caps:
  `CLAWSWEEPER_MAX_REPAIRS_PER_PR=10`, `CLAWSWEEPER_MAX_REPAIRS_PER_HEAD=1` (`SKILL.md:283-285`).
- **Security carve-out** (`SKILL.md:287-299`): vulnerability/CVE/secret/SSRF/XSS/RCE/auth-bypass
  work is routed to central OpenClaw security handling, never staged for unattended repair;
  merges stay blocked until a clean exact-head re-review and open gates.

The takeaway for E.D.I.T.H: ClawSweeper is the canonical "deterministic-executor-owns-writes,
LLM-workers-are-read-only, gates-default-closed" automation pattern.

---

## 6. Cron / scheduling

- Library: **`croner` 10.0.1** (`package.json:1947`) — the cron engine.
- State: SDK export `plugin-sdk/cron-store-runtime` (`package.json:322-325`); persisted under
  the state dir.
- Capability surface (`automation-cron-hooks-tasks-polling.md:8`): "Create/edit/remove jobs,
  Schedule types, Timezone and stagger, Cron RPCs, **Agent cron tool**, Manual cron runs,
  **Isolated cron execution**, Model/provider preflight, Run history, Timeout and denial
  diagnostics, Chat announce delivery, Webhook delivery, Failure destinations, Skipped-run
  alerts, Delivery previews." So a cron job can run an agent turn in isolation, preflight the
  model/provider, then deliver results to a chat or webhook, with failure-destination
  fallbacks.
- Adjacent schedulers: a **heartbeat** loop ("Heartbeat scheduling, Active hours, Wake and
  cooldown handling, Due-only heartbeat tasks, Commitment check-ins",
  `automation-...md:12`) and **event ingress** (Telegram long-polling/webhook,
  `POST /hooks/wake`, `POST /hooks/agent`, mapped hooks with auth policy + async dispatch,
  `automation-...md:9`). E2E: `cron-mcp-cleanup` lane (`package.json:1751`).
- **Automation hooks** are authored as `HOOK.md` files and dispatched on lifecycle events
  via `api.on(...)`, plus tool-call-policy hooks and message hooks
  (`automation-...md:10`); SDK export `plugin-sdk/hook-runtime` (`package.json:618-621`).

---

## 7. Permissions, sandbox, security

### 7.1 Gateway auth & remote access

From `security-auth-pairing-and-secrets.md:9-11` and `gateway-runtime.md:35-42`:

- **Auth modes**: shared gateway token/password, **trusted-proxy identity**, **private
  ingress mode**, device-challenge signing, device tokens, setup-code bootstrap, auth
  mismatch recovery/migration. Non-loopback connections require auth; **trusted CIDR
  auto-approval** and **fail-closed protocol handling** are explicit security controls
  (`gateway-runtime.md:42`). WebSocket handshake auth is part of the connect challenge.
- **Network exposure**: loopback/LAN, **Tailscale Serve/Funnel**, SSH tunnels; bind and
  origin restrictions; TLS pinning (`security-...md:9`, `gateway-runtime.md:36`).
- **Pairing**: device identity creation, device-token issuance, operator-approved device
  pairing, **node pairing** + capability trust + remote-exec approvals (`security-...md:11`).
- Compat baseline is regression-tested: `src/gateway/server.auth.compat-baseline.test.ts`,
  `src/gateway/reconnect-gating.test.ts` (`package.json:1728`).

### 7.2 Approvals, sandbox, tool policy

- **Approval pipeline** is a large SDK surface: `plugin-sdk/approval-runtime`,
  `approval-gateway-runtime`, `approval-native-runtime`, `approval-reaction-runtime`,
  `exec-approvals-runtime`, `command-auth`, `command-gating`, `command-auth-native`
  (`package.json:258-301, 454-457, 734-745`). Exec approvals, plugin approvals, and node-exec
  approvals are distinct, with delivery fallback ("Delivery fallback behavior",
  `gateway-runtime.md:31`) and **approval replay protection**
  (`plugin-sdk-...md:38`).
- **Sandbox backends & isolation** (`browser-automation-and-exec-sandbox-tools.md:8-10`):
  "Sandbox Backends, Workspace Isolation, Sandboxed Browser, Codex Dynamic Tools, Tool
  Policy, Sandbox Tool Gates"; exec routing covers "Process Lifecycle, Direct Tool Invoke
  API, Node System.run, Host Exec Approvals, **Elevated Mode**." Code mode runs JS in
  `quickjs-wasi`; shell exec uses `tree-sitter-bash` for command parsing/gating; filesystem
  access is mediated by `@openclaw/fs-safe` 0.3.0 and `plugin-sdk/file-access-runtime`
  (`package.json:1941, 430-433`).
- **SSRF**: dedicated `plugin-sdk/ssrf-policy`, `ssrf-runtime` exports
  (`package.json:478-485`) guard browser/fetch tools; `provider-transport-fetch.ts` is the
  guarded-fetch boundary.
- **Secrets hygiene**: provider auth profiles, API-key health checks, secrets storage,
  **redaction**, configuration hygiene (`security-...md:13`); a built-in **dangerous-code
  scanner** screens plugins (`clawhub-...md:10`,
  `plugin-sdk/dangerous-name-runtime`). Secret-scanning is itself a maintainer skill
  (`.agents/skills/openclaw-secret-scanning-maintainer/`).

### 7.3 Roles & trust boundaries

Role negotiation, operator permissions, approval-gated actions, untrusted-node declarations,
and event scoping (`gateway-runtime.md:40`); gateway-vs-node trust boundaries and remote
execution safeguards (`gateway-runtime.md:42`).

---

## 8. Gateway commands and session tools

### 8.1 In-chat / gateway slash commands

The gateway exposes a command surface (SDK exports `plugin-sdk/command-surface`,
`command-detection`, `command-status`, `command-primitives-runtime`,
`package.json:746-765`). Command detection + gating means a leading `/...` message is parsed
to a structured command and authorization-checked before dispatch.

**[reconstructed]** session-control commands (the set requested: `/status`, `/new`, `/reset`,
`/compact`, `/think`). Their behaviors map onto resident capability surfaces, though the
exact command strings are not in this sparse tree:

| Command   | Maps to (cited capability) |
|-----------|----------------------------|
| `/status` | Health/identity/usage/memory RPCs + "Command status" (`gateway-runtime.md:34`, `command-status` export). Reports session, model/provider, token pressure. |
| `/new`    | Start a fresh session for the conversation key (session routing; `model-session-runtime`). |
| `/reset`  | Clear/rebind the current session/transcript ("Maintenance, Recovery"; `session-memory-...md:12`). |
| `/compact`| Trigger compaction under token pressure ("Compaction, Pruning, Token Pressure"; `session-memory-...md:9`). |
| `/think`  | Toggle/raise reasoning effort ("Thinking and context settings", "Reasoning and cache controls"; `agent-runtime-...md:10-12`). |

Command authorization is enforced by `command-auth` / `command-gating` (operator vs peer vs
group), consistent with the role model in §7.3.

### 8.2 Session tools (agent-facing)

Beyond chat commands, the agent has tools for memory and session state — "Memory Files,
Tools, and Active Memory" (`session-memory-...md:15`), the cron tool
(`automation-...md:8`), the canvas tool, browser tools, exec/`wait` (code mode), and
Tool Search to expand the catalog on demand (`tool-search.ts`). Embedding search over the
memory backend uses `sqlite-vec` 0.1.9 (optional dep) + `plugin-sdk/embedding-providers`
(`package.json:498-501, 2017`).

### 8.3 CLI command families (operator-facing)

From `openclaw.mjs` precomputed help and `package.json` scripts: `gateway`, `tui`,
`logs` (`openclaw logs --follow`), `browser`, `secrets`, `nodes`, `qa`, `skills`,
`plugins` (search/install via ClawHub), `update`, `doctor`, `tasks`, and onboarding flows.

---

## Reimplementation notes for E.D.I.T.H

1. **Two-stage launcher.** Keep a tiny pure-runtime bootstrap (Node-version gate, fast paths
   for `--version`/`--help`, compile-cache/respawn) separate from the real entry. It makes
   cold-start cheap and keeps the hot runtime out of trivial invocations. Mirror
   `openclaw.mjs`'s `dist/entry.js` handoff.
2. **Config/state precedence ladder.** Adopt the `OPENCLAW_CONFIG_PATH` → `OPENCLAW_STATE_DIR`
   → `~/.app/` ladder, with `~`-expansion and a legacy-name fallback. Put **plugin installs
   under the state dir** (`npm/node_modules`), not the config dir — it makes `mktemp -d`
   state isolation trivial for tests and multi-agent separation.
3. **Protocol as its own package.** Factor the control plane into a versioned
   `gateway-protocol` package: connect-challenge → version-negotiate → `hello-ok` snapshot,
   with idempotent side effects, accepted-then-final results, and explicit event ordering.
   This is what lets web/CLI/mobile/Swift clients share one contract.
4. **Fail-closed security by default.** Non-loopback ⇒ auth required; gates (execute/fix/merge)
   default off; LLM/review workers run with **stripped secrets** while a deterministic
   executor owns all writes (the ClawSweeper pattern). Keep exec/plugin/node approvals as
   separate channels with replay protection and delivery fallback.
5. **Layered tool sandbox.** quickjs-wasi for code mode (`exec`+`wait` only), tree-sitter-bash
   for shell-command gating, an fs-safe boundary for files, and a single SSRF/guarded-fetch
   choke point for all network tools. Make the *actual model-visible tool set* observable
   (a `DEBUG_MODEL_PAYLOAD=tools`-style flag) — config-enabled ≠ run-activated.
6. **Instruction-profile context engine.** Assemble each turn's system context from canonical
   workspace files (AGENTS.md canonical + persona/tools/daily-log overlays), with explicit
   compaction/pruning under token pressure and a `/compact` escape hatch. Treat AGENTS.md as
   canonical and other instruction files as compatibility aliases.
7. **Session keying + bounded concurrency.** Key sessions by (channel, account, conversation),
   distinguish main vs group via a group-policy module, and serialize per-session work with
   async locks + a delivery queue + de-dupe so concurrent inbound events can't corrupt a
   transcript.
8. **Scheduling trio.** Cron (croner) for wall-clock jobs, a heartbeat loop with active-hours
   for proactive check-ins, and hook ingress (`POST /hooks/*`) for external triggers — all
   able to spawn an *isolated* agent turn with model/provider preflight and
   chat/webhook/failure-destination delivery.
9. **Pluggable providers behind one runtime.** Wrap Anthropic/OpenAI/Google/Mistral SDKs +
   MCP + ACP (external CLI agents) behind a single turn runtime with model-reference routing,
   auth-profile failover, and rate-limit recovery, so adding a provider is a plugin, not a
   core change.
```

Source basis: `reference/openclaw/package.json`, `pnpm-workspace.yaml`, `openclaw.mjs`, and
`.agents/skills/**` (clawsweeper, crabbox, openclaw-debugging, openclaw-testing,
channel-message-flows, technical-documentation, and the claw-score completeness rubrics for
gateway-runtime, session-memory-and-context-engine, agent-runtime-and-provider-execution,
automation-cron-hooks-tasks-polling, security-auth-pairing-and-secrets,
browser-automation-and-exec-sandbox-tools, multi-agent-orchestration,
plugin-sdk-and-bundled-plugin-architecture, clawhub-and-external-plugin-distribution).
