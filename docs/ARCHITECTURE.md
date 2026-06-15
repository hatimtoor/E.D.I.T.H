# E.D.I.T.H. Architecture

E.D.I.T.H. fuses the two design philosophies the research identified:

- **OpenClaw = broad networked gateway** (wide channel/tool reach) — the "JARVIS" archetype.
- **Hermes = narrow self-improving specialist** (closed learning loop) — the "FRIDAY" archetype.

E.D.I.T.H. takes the gateway breadth *and* the self-improving loop, then hardens both.

## Module map

```
edith/
├── core/
│   ├── config.py      # config + 5-level permission matrix
│   ├── llm.py         # provider-agnostic chat (anthropic/openai/openrouter, lazy import)
│   ├── context.py     # context assembly + pre-compaction flush (drift fix)
│   └── agent.py       # the loop: build context -> LLM -> tool dispatch -> remember
├── memory/
│   ├── vector.py      # dependency-free hashing embedder + cosine
│   └── store.py       # 3-layer SQLite(+FTS5) store, namespaced, dedup, injection scan
├── skills/
│   └── registry.py    # progressive 3-level loading + agent-immutable protection lock
├── browser/
│   └── stealth.py     # anti-block engine (patchright/camoufox, proxy rotation, human cadence)
├── security/
│   ├── authorization.py  # scope gate — assert_in_scope() choke point
│   └── recon.py          # authorized recon (resolve, port scan, TLS) — all gated
├── sandbox/
│   └── backends.py    # local / docker(hardened) / ssh execution boundary
├── channels/
│   └── base.py        # OpenClaw-style channel adapter abstraction (+ CLIChannel)
├── ruflo/
│   └── bridge.py      # swarm/shared-memory orchestration w/ graceful local fallback
└── __main__.py        # Typer CLI
```

## Request flow (one turn)

```
user/channel ─▶ Agent.step()
                  │
                  ├─ ContextBuilder.build()
                  │     ├─ skill SUMMARIES (progressive)        ← token-lean
                  │     ├─ recall(query) from episodic memory   ← namespaced + deduped
                  │     ├─ restore WORKING.md if present        ← post-compaction recovery
                  │     └─ flush to WORKING.md if near budget   ← drift fix
                  │
                  ├─ LLMClient.chat(messages, tools)
                  │     └─ provider resolved from "provider:model"
                  │
                  ├─ tool loop (≤ max_tool_rounds)
                  │     ├─ dispatch tool (sandbox-gated for shell)
                  │     └─ feed result back to the model
                  │
                  └─ remember(Q/A) → episodic memory
```

## Design principles (borrowed + improved)

- **Narrow waist (Hermes):** the loop is tiny; capabilities live in tools/skills.
- **Broad gateway (OpenClaw):** channels normalize any platform to one message shape.
- **Safe by default:** sandbox is Docker-hardened; offensive tools refuse without scope;
  memory refuses injection; skills can be locked.
- **Offline-first imports:** every module imports with no keys/network; heavy SDKs and
  browser engines are imported lazily and degrade with actionable errors.

## Orchestration (ruflo)

When the ruflo MCP server is connected, `RufloBridge` delegates swarm coordination and
shared memory to it (`swarm_init`, `memory_store`). When it isn't, the bridge falls back
to in-process thread parallelism + the local `MemoryStore`. Either way the agent runs.
