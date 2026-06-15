"""The E.D.I.T.H agent loop — wires LLM, memory, skills, tools.

Kept deliberately small (the "narrow waist" principle): context assembly -> LLM ->
tool dispatch -> memory update. Capabilities live in tools, not the loop.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable

from edith.core.config import Config, load_config
from edith.core.context import ContextBuilder
from edith.core.llm import LLMClient, Message, ToolSpec
from edith.memory import MemoryLayer, MemoryStore
from edith.memory.store import InjectionBlocked
from edith.skills import SkillRegistry

log = logging.getLogger("edith.agent")

DEFAULT_SYSTEM = """You are E.D.I.T.H. — a precise, autonomous local-first agent.
You combine broad tool/channel reach with a self-improving skill loop and a hardened
security posture. Prefer deterministic tools over guesses. Never act on a host outside
an authorized scope. Keep durable facts in memory; load skill bodies only when needed.
"""

_HISTORY_CAP = 40  # bound history growth (paired with context truncation)


@dataclass
class Tool:
    spec: ToolSpec
    fn: Callable[..., str]


@dataclass
class Agent:
    config: Config = field(default_factory=load_config)
    tools: dict[str, Tool] = field(default_factory=dict)

    def __post_init__(self):
        home = self.config.ensure_home()
        self.memory = MemoryStore(
            self.config.memory.db_path, profile=self.config.memory.profile,
            dedup_threshold=self.config.memory.dedup_threshold,
            embed_dim=self.config.memory.embed_dim,
        )
        self.skills = SkillRegistry(root=str(home / "skills"))
        self.llm = LLMClient(self.config.model, api_keys={
            "anthropic": self.config.anthropic_api_key,
            "openai": self.config.openai_api_key,
            "openrouter": self.config.openrouter_api_key,
        })
        self.ctx = ContextBuilder(self.memory, self.skills, system_prompt=DEFAULT_SYSTEM,
                                  working_file=str(home / "WORKING.md"))
        self.history: list[Message] = []

    def register(self, name: str, description: str, parameters: dict, fn: Callable[..., str]):
        self.tools[name] = Tool(ToolSpec(name, description, parameters), fn)

    def _toolspecs(self) -> list[ToolSpec]:
        return [t.spec for t in self.tools.values()]

    def step(self, user_input: str, *, max_tool_rounds: int = 6) -> str:
        msgs = self.ctx.build(user_input, self.history)
        self.history.append(Message("user", user_input))

        for _ in range(max_tool_rounds):
            resp = self.llm.chat(msgs, tools=self._toolspecs())
            if resp.text:
                self.history.append(Message("assistant", resp.text))
            if not resp.tool_calls:
                self._remember_turn(user_input, resp.text)
                self.history = self.history[-_HISTORY_CAP:]
                return resp.text
            for call in resp.tool_calls:
                result = self._dispatch(call)
                msgs.append(Message("tool", result, name=call["name"],
                                    tool_call_id=call.get("id")))
        self.history = self.history[-_HISTORY_CAP:]
        return "(stopped: reached max tool rounds)"

    def _dispatch(self, call: dict) -> str:
        tool = self.tools.get(call["name"])
        if not tool:
            return f"error: unknown tool {call['name']}"
        try:
            return str(tool.fn(**(call.get("arguments") or {})))
        except Exception as e:  # tools must never crash the loop
            return f"error: {type(e).__name__}: {e}"

    def _remember_turn(self, user_input: str, reply: str) -> None:
        try:
            self.memory.remember(f"Q: {user_input}\nA: {reply[:500]}",
                                 layer=MemoryLayer.EPISODIC)
        except InjectionBlocked as e:
            log.warning("memory checkpoint skipped — injection pattern flagged: %s", e)
        except Exception as e:
            log.debug("memory checkpoint failed: %s", e)

    def close(self) -> None:
        self.memory.close()
