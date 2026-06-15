"""The E.D.I.T.H agent loop — wires together LLM, memory, skills, tools, sandbox.

Kept deliberately small (Hermes' "narrow waist" principle): the core loop only does
context assembly -> LLM -> tool dispatch -> memory update. Capabilities live in tools.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from edith.core.config import Config, load_config
from edith.core.context import ContextBuilder
from edith.core.llm import LLMClient, Message, ToolSpec
from edith.memory import MemoryLayer, MemoryStore
from edith.skills import SkillRegistry

DEFAULT_SYSTEM = """You are E.D.I.T.H. — a precise, autonomous local-first agent.
You combine broad tool/channel reach with a self-improving skill loop and a hardened
security posture. Prefer deterministic tools over guesses. Never act on a host outside
an authorized scope. Keep durable facts in memory; load skill bodies only when needed.
"""


@dataclass
class Tool:
    spec: ToolSpec
    fn: Callable[..., str]


@dataclass
class Agent:
    config: Config = field(default_factory=load_config)
    tools: dict[str, Tool] = field(default_factory=dict)

    def __post_init__(self):
        self.memory = MemoryStore(
            self.config.memory.db_path, profile=self.config.memory.profile,
            dedup_threshold=self.config.memory.dedup_threshold,
            embed_dim=self.config.memory.embed_dim,
        )
        self.skills = SkillRegistry(root=str(self.config.home_path / "skills"))
        self.llm = LLMClient(self.config.model, api_keys={
            "anthropic": self.config.anthropic_api_key,
            "openai": self.config.openai_api_key,
            "openrouter": self.config.openrouter_api_key,
        })
        self.ctx = ContextBuilder(self.memory, self.skills, system_prompt=DEFAULT_SYSTEM)
        self.history: list[Message] = []

    # ── tools ───────────────────────────────────────────────────────
    def register(self, name: str, description: str, parameters: dict, fn: Callable[..., str]):
        self.tools[name] = Tool(ToolSpec(name, description, parameters), fn)

    def _toolspecs(self) -> list[ToolSpec]:
        return [t.spec for t in self.tools.values()]

    # ── one turn ────────────────────────────────────────────────────
    def step(self, user_input: str, *, max_tool_rounds: int = 6) -> str:
        msgs = self.ctx.build(user_input, self.history)
        self.history.append(Message("user", user_input))

        for _ in range(max_tool_rounds):
            resp = self.llm.chat(msgs, tools=self._toolspecs())
            if resp.text:
                self.history.append(Message("assistant", resp.text))
            if not resp.tool_calls:
                self._remember_turn(user_input, resp.text)
                return resp.text
            # dispatch tools, append results, loop
            for call in resp.tool_calls:
                result = self._dispatch(call)
                msgs.append(Message("tool", result, name=call["name"]))
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
        except Exception:
            pass

    def close(self) -> None:
        self.memory.close()
