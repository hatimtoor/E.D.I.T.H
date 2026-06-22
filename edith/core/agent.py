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
        # memory backend behind the MemoryProvider ABC (default local; pluggable)
        from edith.memory import LocalMemoryProvider, get_memory_provider
        prov_cls = get_memory_provider(self.config.memory.provider)
        try:
            self.memory_provider = prov_cls(self.memory) if prov_cls else LocalMemoryProvider(self.memory)
            if not self.memory_provider.is_available():
                self.memory_provider = LocalMemoryProvider(self.memory)
        except Exception:
            self.memory_provider = LocalMemoryProvider(self.memory)
        self.skills = SkillRegistry(root=str(home / "skills"))
        self.llm = LLMClient(self.config.model, api_keys={
            "anthropic": self.config.anthropic_api_key,
            "openai": self.config.openai_api_key,
            "openrouter": self.config.openrouter_api_key,
        })
        self.ctx = ContextBuilder(self.memory, self.skills, system_prompt=DEFAULT_SYSTEM,
                                  working_file=str(home / "WORKING.md"))
        self.history: list[Message] = []
        # persistent session/message state (survives restarts, FTS-searchable)
        from edith.core.state import SessionDB
        self.state = SessionDB(str(home / "state.sqlite"))
        self.session = self.state.create_session(source="cli", model=self.config.model)
        # closed-loop learning (heuristic by default = zero extra LLM cost; trajectory export on)
        from edith.core.learning import Learner
        self.learner = Learner(self.memory, self.skills, llm=None,
                               trajectory_path=str(home / "trajectories.jsonl"))

    def register(self, name: str, description: str, parameters: dict, fn: Callable[..., str]):
        self.tools[name] = Tool(ToolSpec(name, description, parameters), fn)

    def load_default_tools(self):
        """Wire the built-in toolset (web, memory, shell, security, files) so the
        agent can actually *do things*, not just chat."""
        from edith.tools import register_default_tools
        self._toolbox = register_default_tools(self)
        return self._toolbox

    def _toolspecs(self) -> list[ToolSpec]:
        return [t.spec for t in self.tools.values()]

    def step(self, user_input: str, *, max_tool_rounds: int = 6) -> str:
        msgs = self.ctx.build(user_input, self.history)
        self.history.append(Message("user", user_input))
        self.state.add_message(self.session.id, "user", user_input)

        for _ in range(max_tool_rounds):
            resp = self.llm.chat(msgs, tools=self._toolspecs())
            if resp.text:
                self.history.append(Message("assistant", resp.text))
                self.state.add_message(self.session.id, "assistant", resp.text)
            if not resp.tool_calls:
                self._remember_turn(user_input, resp.text)
                try:                                   # learn + export; never crash the turn
                    self.learner.export_trajectory(self.history)
                    self.learner.review(user_input, resp.text)
                except Exception as e:
                    log.debug("learning step failed: %s", e)
                self.history = self.history[-_HISTORY_CAP:]
                return resp.text
            for call in resp.tool_calls:
                result = self._dispatch(call)
                self.state.add_message(self.session.id, "tool", result, tool_name=call["name"])
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
            self.memory_provider.sync_turn(user_input, reply)   # routes through the provider ABC
        except Exception as e:
            log.debug("memory checkpoint failed: %s", e)

    def close(self) -> None:
        self.memory.close()
        self.state.close()
