# Hermes Agent — Core Architecture Reference

Deep-research reference for reimplementing the core of the **Hermes Agent** (Nous Research).
Target tree: `C:\E.D.I.T.H\reference\hermes` (read-only). All paths below are relative to that root.
Two files are too large to read whole and were inspected by grep/targeted reads: `cli.py` (~652 KB) and `hermes_state.py` (~210 KB).

The codebase is a single Python monolith with a strict layering discipline: a tiny **narrow waist** (provider profiles, tool registry, environment base, memory/context engine ABCs) with everything else hung off it as **plugins**. The agent itself (`AIAgent`) lives in `run_agent.py`; most of its body has been extracted into `agent/*.py` helper modules that take the `AIAgent` instance as their first argument.

---

## 1. Entry / Runtime

### Launcher chain
- **`hermes` console-script → `hermes_cli/main.py`**. The module docstring (`hermes_cli/main.py:1-44`) enumerates every subcommand (`chat`, `gateway`, `setup`, `cron`, `doctor`, `acp`, `honcho …`, `sessions browse`, `claw migrate`). Default with no args is interactive chat.
- **`hermes_bootstrap` must be the first import** of every entry point (`main.py:46-62`, `gateway/run.py:16-25`). It is a top-level py-module (registered via `pyproject.toml` `py-modules`) and is imported under a `try/except ModuleNotFoundError` so a half-finished `hermes update` (git-reset landed new code before `uv pip install -e .` finished) can still boot.
  - `hermes_bootstrap.py:1-31` — Windows-only UTF-8 fix: sets `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`, and `sys.stdout/stderr.reconfigure(encoding="utf-8")` so `print()` and every spawned subprocess (sandbox, delegation children, linters) avoid `cp1252` `UnicodeEncodeError`. No-op on POSIX.
- `main.py` also sets the process title (`_set_process_title`, `main.py:68-105`) via `setproctitle` → `prctl(PR_SET_NAME)` (Linux) → `pthread_setname_np` (macOS), and does a cheap dependency-free read of `display.interface` (`cli`/`tui`) before `hermes_cli.config` is importable (`main.py:108-120`).
- The CLI itself is assembled from mixins: `hermes_cli/cli_commands_mixin.py`, `cli_agent_setup_mixin.py`, `commands.py`, `_parser.py`, etc. (the actual `AIAgent` wiring and interactive loop live in `cli.py`).

### Gateway (long-running daemon for messaging platforms)
- **`gateway/run.py`** — `start_gateway()` / `GatewayRunner` manage the lifecycle (`run.py:1-14`). Runs all configured platform adapters (`gateway/platforms/*` — Telegram, Slack, Discord, WhatsApp, Signal, Matrix, Feishu, WeCom, QQ-bot, email/SMS, etc.).
- Per-session `AIAgent` cache: `_AGENT_CACHE_MAX_SIZE = 128`, idle TTL eviction `_AGENT_CACHE_IDLE_TTL_SECS = 3600` (`run.py:60-67`). LRU + `_session_expiry_watcher`. Each cached `AIAgent` holds its own LLM clients, tool schemas, memory providers.
- Regex filters strip transient infrastructure noise from user-facing chat (`_TELEGRAM_NOISY_STATUS_RE`, `_GATEWAY_PROVIDER_ERROR_RE`, `run.py:71-100`) — provider/rate-limit chatter stays in logs.
- Account-usage import (`from agent.account_usage import fetch_account_usage`) is deliberately top-level despite ~230 ms cost, to preserve the test-patch surface (`run.py:48-54`).

### Reimplementation takeaway
A single bootstrap shim (encoding + proc title) imported first everywhere; one interactive entry and one daemon entry that both construct the same agent object; an LRU+TTL agent cache keyed by session for the daemon.

---

## 2. The Agent Loop

### Turn entry: `agent/conversation_loop.py`
- `run_conversation(agent, user_message, system_message, conversation_history, task_id, stream_callback, persist_user_message, persist_user_timestamp)` (`conversation_loop.py:469-499`) is the ~3,900-line body extracted from `AIAgent.run_conversation`; the method on the class is now a thin forwarder. It accesses all state through the passed `agent` instance, and resolves symbols that tests/production patch on `run_agent` via the `_ra()` indirection (`conversation_loop.py:13-15, 147-149`).
- **Per-turn prologue** is itself extracted into `agent/turn_context.py::build_turn_context` (`conversation_loop.py:500-524`): stdio guarding, retry-counter resets, user-message sanitization, todo/nudge hydration, system-prompt restore-or-build, crash-resilience persistence, preflight compression, the `pre_llm_call` plugin hook, and external-memory prefetch. It mutates `agent` and returns the locals the loop reads back.
- The loop then: assembles `api_messages`, applies caching, calls the provider (streaming or not), parses `assistant_message.tool_calls`, dispatches tools, appends tool results, and repeats until no tool calls / budget exhausted. Tool dispatch is `agent._execute_tool_calls(assistant_message, messages, effective_task_id, api_call_count)` (`conversation_loop.py:3972`); calls are de-duplicated and `delegate_task` calls are capped (`conversation_loop.py:3895-3899`).
- An `IterationBudget` (`agent/iteration_budget.py`) and `TurnRetryState` (`agent/turn_retry_state.py`) bound the loop. Errors are classified by `agent/error_classifier.py::classify_api_error` → `FailoverReason` to drive retry/fallback. Fallback chain comes from `hermes_cli/fallback_config.py::get_fallback_chain`.

### Context assembly
- **`agent/system_prompt.py`** — stateless assembly of identity, platform hints, environment hints (`build_environment_hints`), skills index, coding posture, memory blocks, and context files (`AGENTS.md`, `.cursorrules`, `SOUL.md`, `.hermes.md`/`HERMES.md` via `_find_hermes_md`, `system_prompt.py:78-90`). Context files are scanned for prompt-injection before injection — `_scan_context_content` uses the shared `tools/threat_patterns.py` (`scope="context"`) and **blocks** matching content with a placeholder so it never reaches the prompt (`system_prompt.py:46-62`).
- **`agent/prompt_builder.py`** — assembles the pieces (the file is the builder layer; `system_prompt.py` provides stateless fragment functions).
- **`agent/context_engine.py`** — abstract `ContextEngine` ABC (`context_engine.py:32-90`). Selected by config `context.engine` (default `"compressor"` = built-in `ContextCompressor`; third-party e.g. LCM drop into `plugins/context_engine/<name>/`). Lifecycle: `on_session_start` → `update_from_response(usage)` after every call → `should_compress()` each turn → `compress(messages)` when true → `on_session_end` at real boundaries only. Key knobs: `threshold_percent = 0.75`, `protect_first_n = 3`, `protect_last_n = 6` (`context_engine.py:64-66`). `protect_first_n` = non-system head messages preserved verbatim **in addition to** the always-protected system prompt — this is what keeps the cache prefix stable.

### "Sacred prompt caching" — `agent/prompt_caching.py`
The whole file is small and load-bearing. Single layout, **`system_and_3`**: exactly 4 `cache_control` breakpoints — the system prompt + the **last 3 non-system messages** — all at the same TTL (`5m` or `1h`). Pure functions, no class state.

```python
def apply_anthropic_cache_control(api_messages, cache_ttl="5m", native_anthropic=False):
    messages = copy.deepcopy(api_messages)          # never mutate caller
    marker = _build_marker(cache_ttl)               # {"type":"ephemeral"[, "ttl":"1h"]}
    breakpoints_used = 0
    if messages[0].get("role") == "system":
        _apply_cache_marker(messages[0], marker, native_anthropic=native_anthropic)
        breakpoints_used += 1
    remaining = 4 - breakpoints_used
    non_sys = [i for i in range(len(messages)) if messages[i].get("role") != "system"]
    for idx in non_sys[-remaining:]:
        _apply_cache_marker(messages[idx], marker, native_anthropic=native_anthropic)
    return messages
```
`_apply_cache_marker` (`prompt_caching.py:15-39`) handles every content shape: `tool` role (only marks when `native_anthropic`), empty/None content, plain-string content (wrapped into a `[{type:text, cache_control}]` list), and list content (marks the last block). Called from the loop at `conversation_loop.py:792`.

**The sacred invariant**: the system prompt and the message *head* are byte-stable for the session. Memory (`MEMORY.md`/`USER.md`) is a **frozen snapshot** captured at session start; mid-session memory writes hit disk immediately but are **not** re-injected — they would invalidate the prefix cache (`tools/memory_tool.py:11-14`). The same discipline is why background review / curator run in **forks** that never touch the main prompt cache.

### Providers — `plugins/model-providers/*` over `providers/base.py`
- **Narrow waist:** `providers/base.py::ProviderProfile` (`base.py:38-80`) is one declarative dataclass describing a provider: `name`, `api_mode` (`chat_completions`/messages/responses), `aliases`, `env_vars`, `base_url`, `auth_type` (`api_key|oauth_device_code|oauth_external|copilot|aws_sdk`), `supports_vision`, `fallback_models`, `hostname`, plus request hooks `build_extra_body()` and `build_api_kwargs_extras()`. The transport reads the profile instead of receiving "20+ boolean flags." Profiles are **declarative only** — they do not own client construction, credential rotation, or streaming (those stay on `AIAgent`).
- Each provider plugin is `plugins/model-providers/<name>/__init__.py` that constructs a profile and calls `register_provider(...)`. Example `plugins/model-providers/nous/__init__.py:10-54`: `NousProfile` injects Nous portal product `tags` via `build_extra_body`, and omits the `reasoning` field when reasoning is disabled. `base_url = https://inference.nousresearch.com/v1`, `auth_type="oauth_device_code"`.
- Sibling plugins: `anthropic`, `deepseek`, `openrouter`, `gemini`, `bedrock`, `azure-foundry`, `copilot[-acp]`, `xai`, `minimax`, `qwen-oauth`, `zai`, `kimi-coding`, plus a generic `custom`. Provider-specific adapters live in `agent/*_adapter.py` (`anthropic_adapter`, `bedrock_adapter`, `gemini_native_adapter`, `codex_responses_adapter`, `azure_identity_adapter`).

### Tool-call handling
- Strict-API sanitation before each call: `agent._sanitize_tool_call_arguments`, `_sanitize_tool_calls_for_strict_api` (`conversation_loop.py:681-752`); non-ASCII/surrogate scrubbing from `agent/message_sanitization.py`.
- After a response: invalid tool names get an error tool-result so the model can self-correct (`conversation_loop.py:3734-3744`); `finish_reason="length"` mid-tool-call is rewritten to `tool_calls`; results are appended as `tool` messages and the loop continues.

---

## 3. Closed-Loop Learning / Self-Improvement

This is the headline capability: after a turn the agent **forks itself** to reflect and crystallize learnings into memory + skills, without disturbing the live conversation or its prompt cache.

### Background review — `agent/background_review.py`
- `spawn_background_review_thread(...)` returns a `(target, prompt)` tuple consumed by `AIAgent._spawn_background_review` (`background_review.py:700-732`). The target runs on a **daemon thread** that replays the conversation snapshot in a **forked `AIAgent`** and asks "should any skill/memory be saved/updated?" (`background_review.py:1-17`).
- The fork **inherits the parent's live runtime** (provider, model, base_url, credentials, cached system prompt) so it hits the same prefix cache and same auth, but runs with a **runtime tool whitelist** limited to the `memory` and `skills` toolsets — everything else is denied at dispatch (`background_review.py:592-609`):
  ```python
  review_whitelist = {t["function"]["name"]
                      for t in get_tool_definitions(enabled_toolsets=["memory","skills"], quiet_mode=True)}
  set_thread_tool_whitelist(review_whitelist, deny_msg_fmt="Background review denied non-whitelisted tool: {tool_name}...")
  ```
  Dangerous commands are auto-denied in the review thread (`_bg_review_auto_deny`, `background_review.py:466`).
- Two review prompts (`background_review.py:34-100+`): `_MEMORY_REVIEW_PROMPT` (persona/preferences/expectations → memory tool, else "Nothing to save.") and `_SKILL_REVIEW_PROMPT` (be **active**, most sessions should produce ≥1 skill update; prefers, in order: patch a currently-loaded skill → patch an existing umbrella skill → add a `references/`|`templates/`|`scripts/` support file → create a new class-level umbrella skill). The skill prompt explicitly treats user-frustration signals ("stop doing X", "too verbose") as first-class skill signals.

### Trajectory — `agent/trajectory.py`
- `save_trajectory(trajectory, model, completed, filename)` appends ShareGPT-format JSONL: `trajectory_samples.jsonl` (completed) or `failed_trajectories.jsonl` (`trajectory.py:30-56`). These are training-data exports for fine-tuning the Hermes model family.
- `convert_scratchpad_to_think` / `has_incomplete_scratchpad` (`trajectory.py:16-27`) normalize `<REASONING_SCRATCHPAD>` ↔ `<think>` tags and detect truncated reasoning (used by the loop to drive continuation).

### Insights — `agent/insights.py`
- `InsightsEngine(db).generate(days=30)` mines the SQLite state DB for token/cost/tool-usage/activity/model/platform breakdowns and per-session metrics (`insights.py:1-31`), with cost via `agent/usage_pricing.py`. This is the `/insights` analytics surface, not part of the live loop.

### Curator — `agent/curator.py`
- Auxiliary-model background **skill maintenance**, **inactivity-triggered** (no cron daemon): when the agent is idle and the last run was > `interval_hours` ago, `maybe_run_curator()` forks an `AIAgent` to review **agent-created** skills (`curator.py:1-20`).
- Strict invariants: only touches agent-created skills (`tools/skill_usage.is_agent_created`); **never auto-deletes — only archives** (recoverable); pinned skills bypass all auto-transitions; uses the auxiliary client and never the main session's prompt cache.
- Defaults: `DEFAULT_INTERVAL_HOURS = 24*7`, `DEFAULT_MIN_IDLE_HOURS = 2`, `DEFAULT_STALE_AFTER_DAYS = 30`, `DEFAULT_ARCHIVE_AFTER_DAYS = 90`, `DEFAULT_CONSOLIDATE = False` (`curator.py:56-64`). The deterministic inactivity prune (`apply_automatic_transitions`) always runs when enabled; the LLM umbrella-building consolidation pass is opt-in. State persisted in `.curator_state`.

### agentskills.io standard
Skills are agentskills.io-compatible (`tools/skills_tool.py:23-46`): `SKILL.md` YAML frontmatter with `name` (≤64), `description` (≤1024), optional `version`, `license`, `platforms`, `prerequisites`, `compatibility`, and arbitrary `metadata` (Hermes namespaces its own under `metadata.hermes` for `tags`, `related_skills`). `assets/` is the agentskills.io supplementary-files dir.

---

## 4. Skill System

### Layout & store
All skills live in **`~/.hermes/skills/`** (single source of truth; bundled skills are seeded here on install so agent edits + hub installs + bundled skills coexist without polluting the repo — `skills_tool.py:90-94`, `skill_manager_tool.py:107-110`). Per-skill dir: `SKILL.md` (required) + optional `references/`, `templates/`, `scripts/`, `assets/` (`ALLOWED_SUBDIRS`, `skill_manager_tool.py:245`).

### Progressive 3-level loading
Explicitly modeled on Anthropic Claude Skills progressive disclosure (`skills_tool.py:9-13, 53-54`):
- **Tier 1 — metadata only**: `skills_list()` returns just `name` + `description` (≤64 / ≤1024 chars, `MAX_NAME_LENGTH`/`MAX_DESCRIPTION_LENGTH`, `skills_tool.py:96-98`) — this is the index injected into the system prompt.
- **Tier 2 — full instructions**: `skill_view(name)` loads the whole `SKILL.md` body on demand.
- **Tier 3 — linked files**: `skill_view(name, "references/dataset-formats.md")` loads a single support file on demand.
- The system-prompt skills index is built by `build_skills_system_prompt(available_tools, available_toolsets, compact_categories)` only when the agent actually has `skills_list`/`skill_view`/`skill_manage` tools (`system_prompt.py:258-288`). An opt-in **focus/coding mode** (`agent/coding_context.py::coding_compact_skill_categories`) demotes non-coding categories to names-only in the index — never hidden, since `skill_view`/`skills_list` still reach everything.
- Frontmatter parsing + conditional activation: `agent/skill_utils.py::parse_frontmatter`, `skill_matches_platform` (top-level `platforms:`), `skill_matches_environment` (`environments:`), `extract_skill_conditions`, `extract_skill_config_vars` (`skill_utils.py:123-549`).

### create / edit / patch / delete — `tools/skill_manager_tool.py`
Single `skill_manage` tool with `action` (`skill_manager_tool.py:14-32`): `create` (full `SKILL.md`), `edit` (full rewrite of a user skill), `patch` (targeted find-and-replace in `SKILL.md` or any support file), `delete`, `write_file` (add/overwrite a support file under `references/|templates/|scripts/|assets/`), `remove_file`. Approval gate: when approvals are on, writes are **staged** for review (skills are too big to review inline so they always stage); when off they apply directly (`skill_manager_tool.py:1019-1034`).

### Slash invocation — `agent/skill_commands.py`
`/skill-name` expands the turn into a model-facing message embedding the full skill body + scaffolding (markers `_SKILL_INVOCATION_PREFIX`, `_SINGLE_SKILL_MARKER`, etc., `skill_commands.py:47-55`). Because that expanded text flows into memory providers, `extract_user_instruction_from_skill_message` recovers just the user's real instruction so memory stays clean (`skill_commands.py:58+`). Bundles are built in `agent/skill_bundles.py`; markers must stay byte-identical across builders (asserted in tests).

### Guard / protection / provenance / hub
- **`tools/skills_guard.py`** — regex static-analysis scanner for externally-sourced skills (exfil, injection, destructive cmds, persistence). Trust tiers (`skills_guard.py:11-55`): `builtin` (never scanned, always trusted), `trusted` (`openai/skills`, `anthropics/skills`, `huggingface/skills`, `NVIDIA/skills` — caution allowed), `community` (any finding = blocked unless `--force`). `INSTALL_POLICY` is a `(safe, caution, dangerous)` matrix per tier. Agent-created skills are only scanned when `skills.guard_agent_created` is on (default off — the agent can already run the same code via `terminal()`, `skill_manager_tool.py:59-102`).
- **`tools/skill_provenance.py`** — a `ContextVar` write-origin marker distinguishing agent-sediment writes (background review/curator) from foreground user-directed writes; `is_background_review()` gates auto-create suppression in foreground (`skill_manager_tool.py:1076-1083`). Set in the loop via `set_current_write_origin` (`conversation_loop.py:63`).
- **Pin / protection**: pinned skills bypass all curator auto-transitions (`curator.py:18`). Lifecycle (active → stale → archived) is derived from activity timestamps; archive is recoverable, delete is never automatic.
- **`tools/skills_hub.py`** — `SkillSource` ABC + adapters for `official`, `github`, `clawhub`, `claude-marketplace`, `lobehub` (`skills_hub.py:3-13, 74`); `HubLockFile` tracks provenance of installed hub skills; downloads land in `~/.hermes/skills/.hub/quarantine/` for scanning before install, with `install_path` validated to end in the skill name to keep `uninstall`'s `rmtree` inside `SKILLS_DIR` (`skills_hub.py:123-165`).

---

## 5. Memory

Three coordinated layers.

### Tier A — Curated file memory (`tools/memory_tool.py`)
Bounded, file-backed, persists across sessions (`memory_tool.py:1-24`). Two stores in `~/.hermes/memories/` (`get_memory_dir`, `memory_tool.py:55-57`): **`MEMORY.md`** (agent's notes: environment facts, conventions, tool quirks) and **`USER.md`** (preferences, communication style, expectations). Single `memory` tool with `action` ∈ `add|replace|remove`; replace/remove use short unique-substring matching (not IDs). Entry delimiter `\n§\n` (`memory_tool.py:59`); **char limits** not token limits (model-independent). **Frozen-snapshot pattern**: injected into the system prompt at session start; mid-session writes hit disk immediately but do not change the prompt (preserves the prefix cache); snapshot refreshes next session. Content is scanned with `tools/threat_patterns.py` (`scope="strict"`) before write because a poisoned entry would persist across sessions (`memory_tool.py:62-80`). Cross-platform file locking (`fcntl` / `msvcrt`).

### Tier B — Provider abstraction (`agent/memory_provider.py` + `agent/memory_manager.py`)
- **`MemoryProvider` ABC** (`memory_provider.py:42-90`): `is_available`, `initialize(session_id, **kwargs)`, `system_prompt_block()` (static text), `prefetch(query)` (background recall before each turn), `sync_turn(user, asst)` (async write after turn), `get_tool_schemas()` / `handle_tool_call()`, `shutdown()`. Optional hooks: `on_turn_start`, `on_session_end`, `on_session_switch`, `on_pre_compress(messages)`, `on_memory_write`, `on_delegation`. `initialize` kwargs carry `hermes_home`, `platform`, `agent_context` (`primary`/`subagent`/`cron`/`flush` — non-primary contexts skip writes so cron prompts don't corrupt user representations), `agent_identity`, `user_id`, `parent_session_id`.
- **`MemoryManager`** (`memory_manager.py:1-45`) is the single integration point in `run_agent.py`: `build_system_prompt()`, `prefetch_all(query)` pre-turn, `sync_all(user,asst)` + `queue_prefetch_all(user)` post-turn. **Enforces exactly one external provider** at a time (prevents tool-schema bloat / conflicting backends). `inject_memory_provider_tools(agent)` appends provider tool schemas only when the `memory` toolset is enabled (`memory_manager.py:48-70`).

### Tier C — SQLite session state (`hermes_state.py::SessionDB`)
- SQLite + FTS5, **WAL mode** for concurrent readers + single writer (gateway multi-platform; `hermes_state.py:10, 657-663`). WAL is set with a fallback to `journal_mode=DELETE` on WAL-incompatible mounts (NFS/SMB/FUSE) detected via `OperationalError("locking protocol")`/`_WAL_INCOMPAT_MARKERS`, and never downgrades if the on-disk header already says WAL (`hermes_state.py:128-308`). Includes malformed-schema recovery via `PRAGMA writable_schema` surgery (`hermes_state.py:414-482`).
- **Schema** (`SCHEMA_SQL`, `hermes_state.py:509-590`): `sessions` (id, source, user_id, model, system_prompt, `parent_session_id` self-FK for subagents, timing, message/tool/api counts, full token+cache+reasoning token columns, billing provider/base_url/mode, estimated/actual cost, title, handoff_state, archived) and `messages` (session_id FK, role, content, tool_call_id, tool_calls, tool_name, reasoning fields incl. `codex_reasoning_items`, `platform_message_id`, `observed`, `active`). Plus `state_meta` and `compression_locks` (distributed compaction lock with `expires_at`).
- **FTS5 search** (`FTS_SQL`, `hermes_state.py:601-624`): `messages_fts` virtual table on `content`, kept in sync by insert/delete/update triggers that index `content || tool_name || tool_calls`. A second `messages_fts_trigram` table with `tokenize='trigram'` (`hermes_state.py:630-654`) provides CJK/Thai substring search the default unicode61 tokenizer can't.

### External memory plugins — `plugins/memory/*`
One-at-a-time external backends, each a `MemoryProvider`: `mem0`, `honcho` (full client/session/cli under `honcho/`), `holographic` (local `store.py`/`retrieval.py`/`holographic.py`), `supermemory`, `byterover`, `hindsight`, `retaindb`, `openviking`. The memory `mode` is configurable `hybrid`/`honcho`/`local` (see `hermes honcho mode`, `main.py:29-31`).

---

## 6. Sandbox / Execution Backends — `tools/environments/*`

### Base — `tools/environments/base.py`
- **Unified spawn-per-call model** (`base.py:1-7`): every command spawns a fresh `bash -c`. A **session snapshot** (env vars, functions, aliases, shell opts) is captured once at init (`init_session`, `base.py:351-400`) and re-sourced before each command; CWD persists via in-band stdout markers (remote) or a temp file (local). Snapshot bootstrap: `export -p`, `declare -f` (filtered), `alias -p`, `shopt -s expand_aliases`, `set +e/+u`, then `cd` to configured cwd and emit `_cwd_marker` (`base.py:372-382`). All snapshot/cwd paths are `shlex.quote`d so Git-Bash-on-Windows `C:/…` paths don't glob-split on the colon.
- **`BaseEnvironment(ABC)`** (`base.py:288-345`): subclasses implement `_run_bash(cmd_string, *, login, timeout, stdin_data) -> ProcessHandle` and `cleanup()`; the base provides `execute()` with snapshot sourcing, CWD tracking, interrupt handling (`tools/interrupt.is_interrupted`), and timeout enforcement. `_stdin_mode` is `"pipe"` or `"heredoc"` (Modal/Daytona use heredoc, `base.py:296-297`). `get_sandbox_dir()` roots host-side storage at `TERMINAL_SANDBOX_DIR` or `{HERMES_HOME}/sandboxes/` (`base.py:81-93`).
- A thread-local **activity callback** (`set_activity_callback` / `touch_activity_if_due`, `base.py:43-78`) lets long-running commands report liveness to the gateway at ≥10 s cadence. Windows stdin newline corruption is avoided by writing through `proc.stdin.buffer` (`_pipe_stdin`, `base.py:101-130`).
- Backends: `local.py`, `docker.py`, `ssh.py`, `singularity.py`, `modal.py`, `managed_modal.py`, `daytona.py` (+ `modal_utils.py`). File transfer between host and remote backend: `file_sync.py`.

### Permission / control matrix (5 levels) — `tools/approval.py`
Dangerous-command detection + per-session approval state, keyed by `session_key` via contextvars (`approval.py:1-7, 36-45`). The effective control levels:
1. **`off` / `--yolo` / `/yolo`** — bypass all approval prompts (`_YOLO_MODE_FROZEN` process-scoped from `HERMES_YOLO_MODE`; `is_current_session_yolo_enabled()` session-scoped; `approval.py:1408-1412`).
2. **`smart`** — auxiliary LLM risk assessment (`_smart_approve`) decides `approve`/`deny`/escalate before prompting the user; inspired by OpenAI Codex Smart Approvals (`approval.py:1483-1499`).
3. **`manual` / interactive (`on`)** — `detect_dangerous_command` + Tirith (`tools/tirith_security.check_command_security`) findings → user approval prompt with per-pattern session memory (`is_approved`/`approve_session`, `approval.py:1442-1481`).
4. **`cron_mode`** — non-interactive sessions (`HERMES_CRON_SESSION`): `approve`/`deny` governed by `approvals.cron_mode` config, never interactive resolve (`approval.py:1424-1440`).
5. **Hard guards (un-bypassable)** — checks that fire **before** the yolo/mode check: e.g. the sudo-stdin guard (`_check_sudo_stdin_guard`) blocks even under yolo/smart/off (`approval.py:1400-1406`); in-place edits of credential/SSH/shell-rc/`~/.hermes/config.yaml`/`.env` are gated regardless of mode (`approval.py:453-501`). `~/.hermes/config.yaml` *is* the security policy, mtime-cached so an edit takes effect mid-session.

Subagents add their own non-interactive layer (`tools/delegate_tool.py:73-97`): `_subagent_auto_deny` (default — returns "deny", never calls `input()` which would deadlock the parent TUI) or `_subagent_auto_approve` (opt-in via `delegation.subagent_auto_approve`).

---

## 7. Multi-Agent Delegation — `tools/delegate_tool.py`

- Spawns **child `AIAgent` instances** with isolated context, restricted toolsets, and their own terminal sessions; single-task or batch (parallel via `ThreadPoolExecutor`). The parent **blocks** until all children complete (`delegate_tool.py:1-17`).
- Each child gets: a **fresh conversation** (no parent history), its own `task_id` (own terminal session + file-ops cache), a restricted toolset, and a focused system prompt built from `goal + context`. The parent's context only ever sees the delegation call and the **summary result** — never the child's intermediate tool calls or reasoning (`delegate_tool.py:9-17`).
- **`DELEGATE_BLOCKED_TOOLS`** (`delegate_tool.py:45-53`) always stripped from children: `delegate_task` (no recursive delegation), `clarify` (no user interaction), `memory` (no writes to shared `MEMORY.md`), `send_message` (no cross-platform side effects), `execute_code` (children reason step-by-step rather than scripting).
- Approval callbacks are injected into each worker thread via `ThreadPoolExecutor(initializer=_set_subagent_approval_cb, initargs=(cb,))` because worker threads don't inherit the CLI's `threading.local()` approval callback (`delegate_tool.py:56-72`).
- Parent↔child observation: the memory provider hook `on_delegation(task, result, **kwargs)` lets the parent's memory observe subagent work (`memory_provider.py:30`). Subagent session lineage is recorded via `sessions.parent_session_id` (`hermes_state.py:521, 548`). Async variant + RPC plumbing in `tools/async_delegation.py`.

---

## 8. "Narrow Waist" Philosophy & Extension Surfaces

The architecture is a small set of stable ABCs/registries (the waist) with everything pluggable above and below:

| Waist interface | File | Plugins / implementations |
|---|---|---|
| `ProviderProfile` | `providers/base.py` | `plugins/model-providers/*` (one declarative profile + `register_provider`) |
| Tool `registry` | `tools/registry.py` | every `tools/*.py` self-registers via module-level `registry.register(...)`; discovered by AST-scanning for that call (`registry.py:29-65`) |
| `BaseEnvironment` | `tools/environments/base.py` | `local/docker/ssh/singularity/modal/managed_modal/daytona` |
| `ContextEngine` | `agent/context_engine.py` | built-in `compressor`, plus `plugins/context_engine/*` (e.g. LCM) |
| `MemoryProvider` | `agent/memory_provider.py` | `plugins/memory/*` (mem0/honcho/holographic/…) |
| `SkillSource` | `tools/skills_hub.py` | official/github/clawhub/claude-marketplace/lobehub |
| Platform adapter | `gateway/platforms/base.py` | `gateway/platforms/*` + `plugins/platforms/*` (discord/irc/line/mattermost/ntfy/…) |

- **Tool registry as waist**: `model_tools.py` queries `registry` instead of duplicating data; tools declare schema + handler + toolset + availability check at import. `toolsets.py::TOOLSETS` groups tools (`memory`, `skills`, …) and is what delegation/whitelisting filter on.
- **MCP**: `tools/mcp_tool.py` + `tools/mcp_oauth*.py`; MCP servers are configured (`hermes_cli/mcp_config.py`, `mcp_catalog.py`, `mcp_startup.py`) and surfaced as tools through the same registry — external MCP tools are just more entries in the waist.
- **ACP** (Agent Client Protocol, editor integration): `hermes acp` → `acp_adapter/` (`server.py`, `session.py`, `tools.py`, `permissions.py`, `edit_approval.py`, `events.py`, `provenance.py`, `auth.py`). `server.py` exposes Hermes via the `acp` package's schema (`InitializeResponse`, `NewSessionResponse`, `SetSessionModeResponse`, MCP server descriptors, etc., `acp_adapter/server.py:1-50`). ACP's `permissions.py`/`edit_approval.py` bridge editor approval prompts to the same approval layer.
- **Hooks/plugins**: lifecycle hooks (`pre_llm_call`, `pre_approval_request`/`post_approval_response`, gateway `builtin_hooks/`) let plugins intercept turns and approvals without forking the core.

---

## Reimplementation notes for E.D.I.T.H

1. **Make the prompt prefix sacred.** Adopt the frozen-snapshot rule everywhere: system prompt + memory + first-N messages are byte-stable per session; all mutations (memory writes, learning) go to disk now and into the prompt *next* session. Cache with the `system_and_3` pattern — system prompt + last 3 non-system messages, 4 breakpoints, single TTL (`agent/prompt_caching.py` is ~80 lines and directly portable).
2. **Build the narrow waist first.** Five ABCs/registries — `ProviderProfile`, tool `registry`, `BaseEnvironment`, `ContextEngine`, `MemoryProvider` — then implement one concrete of each. Everything else (every model vendor, every sandbox, every memory backend) is a plugin that never touches the core. The AST-based self-registration in `tools/registry.py` is a clean way to avoid a central import list.
3. **Closed-loop learning = forked self-review under a tool whitelist.** Reuse the parent's runtime/cache, restrict to `[memory, skills]` toolsets, run on a daemon thread, and bias the prompt toward *acting* (≥1 update/session). Add an inactivity-triggered curator that only archives (never deletes) and respects pins. Export ShareGPT JSONL trajectories for later fine-tuning.
4. **Three-tier skills with progressive disclosure.** Tier-1 index (`name`+`description` ≤64/≤1024) in the system prompt; tier-2 full `SKILL.md` on `skill_view`; tier-3 support files on demand. Keep the agentskills.io frontmatter contract so skills are portable. Gate external installs through a trust-tiered scanner; leave agent-created skills ungated (they can already run code).
5. **One SQLite DB, WAL + FTS5, with a robust fallback.** Mirror the `sessions`/`messages` schema (self-FK for subagent lineage, full token/cache/cost columns) and the dual FTS5 (unicode61 + trigram) for non-Latin substring search. Implement the WAL→DELETE fallback for network mounts and a distributed `compression_locks` table if multiple surfaces share the DB.
6. **Delegation = fresh child agents, summary-only return.** Block the parent, isolate context/terminal/task_id, hard-strip `delegate_task`/`memory`/`send_message`/`execute_code`/`clarify` from children, and inject a non-interactive approval callback into every worker thread (default deny). Surface delegation results to memory via an `on_delegation` hook.
7. **Layered, un-bypassable permission matrix.** Order matters: hard guards (sudo-stdin, credential/config in-place edits) fire *before* the `off`/yolo check; then `smart` (aux-LLM), then interactive `manual`, with a separate `cron_mode` for non-interactive runs. Keep the security policy in a single mtime-cached config file so changes take effect mid-session.
8. **Bootstrap shim first, always.** A tiny encoding/proc-title module imported before anything else at every entry point, guarded so a partial self-update can still boot and recover.
