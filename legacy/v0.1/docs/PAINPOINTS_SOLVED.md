# Pain points → E.D.I.T.H. fixes (grounded in the real source code)

These aren't guesses. Two read-only investigations of the real repos
(`openclaw/`, `nousresearch/hermes-agent`) established exactly how each problem is
caused. Each fix below cites the real upstream behavior and the E.D.I.T.H. file that
addresses it.

---

## 1. Browser gets blocked / CAPTCHA-walled on a Linux server  ⭐ headline

**Upstream cause (verified):**
- **OpenClaw** — `extensions/browser/src/browser/`:
  - Uses plain `playwright-core` (`playwright-core.runtime.ts`).
  - Launches `--headless=new` + `--disable-gpu` (`chrome.ts`), which is fingerprintable.
  - **No stealth at all**: `navigator.webdriver` is never patched, no fingerprint
    spoofing, no WebGL/canvas evasion (confirmed absent in `pw-tools-core.state.ts`).
  - Proxy only via manual `--proxy-server` in `extraArgs`; **no rotation**
    (`browser-proxy-mode.ts`), and `--no-proxy-server` is added by default.
  - Typing is a **fixed 75ms** (`pw-tools-core.interactions.ts:873`) — robotic cadence.
  - **No CAPTCHA** detection or handling anywhere.
- **Hermes** — `tools/browser_tool.py`, `tools/browser_camofox.py`,
  `agent/browser_provider.py`: has a good anti-detect option (**Camoufox**, a
  fingerprint-hardened Firefox) and Browserbase cloud stealth — but Camoufox is behind
  `CAMOFOX_URL` and the strong stealth is **paywalled** (`BROWSERBASE_ADVANCED_STEALTH`,
  "requires Scale Plan"). Off by default.

**E.D.I.T.H. fix — `edith/browser/stealth.py`:** stealth is **on by default** and stacks:
1. `patchright` engine (de-fingerprinted Playwright) instead of raw `playwright-core`.
2. Pre-navigation JS patches the exact signals OpenClaw leaves exposed:
   `navigator.webdriver→undefined`, plugins/languages, `window.chrome`, permissions
   consistency, **WebGL vendor/renderer spoof**.
3. `--disable-blink-features=AutomationControlled` + hardened Linux/Docker args.
4. Realistic rotating User-Agent, locale, timezone, randomized viewport.
5. **Residential proxy rotation** (`proxy_pool`) — the single biggest unblock factor.
6. Human cadence: variable 40–220ms typing with word-boundary pauses, mouse jitter.
7. Optional **Camoufox** backend (Hermes' good option, but free + default-available).
8. `preflight()` gives the *practical* Linux guidance: run headed under `xvfb-run`,
   set a residential proxy — the two things that actually stop the blocking.
9. CAPTCHA is **detected and surfaced** instead of silently hanging.

---

## 2. Self-improvement loop overwrites hand-crafted skills

**Upstream cause (verified):** Hermes `tools/skill_manager_tool.py` — "pin" blocks
**deletion only**; the message literally says *"Patches and edits are allowed on pinned
skills."* Meanwhile `agent/background_review.py` runs after every turn and is prompted
to be **active** ("most sessions produce at least one skill update… PATCH that one
first"). So a loaded user skill can be rewritten without consent.

**E.D.I.T.H. fix — `edith/skills/registry.py`:** a real **edit lock**. `protect(name)`
marks a skill agent-immutable; `update()`/`delete()` raise `ProtectedSkillError` when
`by_agent=True`. Only an explicit human action (`edith skills unprotect`) re-enables
agent edits. Tested in `tests/test_skills.py`.

---

## 3. Memory "junk drawer" — collisions, wrong tool picked

**Upstream cause (verified):** Hermes built-in store (`hermes_state.py`) is **FTS5
text-only (no vectors)** in a **single shared `state.db`** with no per-project
namespace and no dedup; vector search only exists via external plugins.

**E.D.I.T.H. fix — `edith/memory/store.py`:** 3-layer store (Working/Episodic/Procedural)
that is **profile-namespaced** (no cross-task bleed), does **cosine dedup on write**
(`dedup_threshold`), and combines FTS5/LIKE prefilter **with local vector ranking**.
Tested: `test_profiles_are_isolated`, `test_dedup_skips_near_duplicate`.

---

## 4. Context drift from token compaction

**Upstream cause:** OpenClaw compacts long conversations and loses system instructions
(it has a pre-compaction flush to `MEMORY.md`, but drift is still the top complaint).

**E.D.I.T.H. fix — `edith/core/context.py`:** `ContextBuilder` watches a token
high-water mark and **flushes durable state to `WORKING.md` + episodic memory before**
truncation, then auto-reloads it on the next build.

---

## 5. Token blowup on fresh sessions

**Upstream cause:** large skill catalogs loaded eagerly.

**E.D.I.T.H. fix:** progressive 3-level skill loading (`SkillLevel.SUMMARY/PARAMS/BODY`)
enforced in the registry; context carries **summaries only** until a body is needed.

---

## 6. Prompt-injection → host compromise & unauthorized actions

**Upstream cause:** OpenClaw needs broad host access; an injected instruction can run
shell or message unauthorized contacts.

**E.D.I.T.H. fix:** (a) injection scan on every memory write
(`MemoryStore.remember`, `InjectionBlocked`); (b) hardened **Docker sandbox** default
with cap-drop / no-new-privileges / read-only / `--network none` / pids+mem limits
(`edith/sandbox/backends.py`); (c) destructive-command regex as defense-in-depth;
(d) explicit per-capability **permission matrix** (`edith/core/config.py`).

---

## 7. Community wishes

| Wish | E.D.I.T.H. |
|---|---|
| P2P / distributed multi-agent mesh (OpenClaw) | `edith/ruflo/bridge.py` swarm topologies (mesh/hierarchical) |
| Persistent horizontal agent teams (Hermes) | ruflo bridge + native team fallback (shared task list) |
| Deterministic skill protection (Hermes) | `edith skills protect` (item 2) |
| Token-aware skill routing (Hermes) | progressive loading (item 5) |
| Low-latency ambient voice (both) | roadmap — see `docs/ROADMAP.md` |

---

## 8. J.A.R.V.I.S. / F.R.I.D.A.Y. capabilities mapped to real features

| Fictional capability | E.D.I.T.H. analogue |
|---|---|
| JARVIS distributed survival (scatter across network) | ruflo swarm + namespaced memory persistence |
| JARVIS multi-domain tool coordination | channel gateway + tool dispatch in `core/agent.py` |
| FRIDAY network monitoring / security overrides | authorized recon toolkit (`security/recon.py`), scope-gated |
| FRIDAY real-time pattern analysis | stealth browser + tool loop for live web recon |
| FRIDAY hardened containment protocols | sandbox backends + permission matrix |
