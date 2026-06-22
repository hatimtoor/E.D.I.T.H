"""Context builder + pre-compaction flush.

Fixes OpenClaw's documented "context drift": when a long conversation is compacted it
loses system instructions and repeats corrected mistakes. E.D.I.T.H flushes durable
facts to WORKING.md (+ episodic memory) BEFORE truncation, then reloads after — and it
ACTUALLY truncates the message list so context can't grow unbounded.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from edith.core.context_engine import ContextEngine, ContextCompressor
from edith.core.llm import Message
from edith.memory import MemoryLayer, MemoryStore
from edith.skills import SkillLevel, SkillRegistry


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)  # ~4 chars/token, good enough for budget gating


@dataclass
class ContextBudget:
    max_tokens: int = 180_000
    flush_at: float = 0.75
    reserve_for_reply: int = 8_000


@dataclass
class ContextBuilder:
    memory: MemoryStore
    skills: SkillRegistry
    system_prompt: str = ""
    budget: ContextBudget = field(default_factory=ContextBudget)
    engine: ContextEngine = field(default_factory=ContextCompressor)
    working_file: str = "WORKING.md"   # Agent passes an absolute path under its home

    def build(self, user_input: str, history: list[Message]) -> list[Message]:
        sys_parts = [self.system_prompt] if self.system_prompt else []
        sys_parts.append("# Available skills (summaries; load body on demand)\n"
                         + self.skills.catalog(SkillLevel.SUMMARY))
        recalled = self.memory.recall(user_input, layer=MemoryLayer.EPISODIC, limit=5)
        if recalled:
            sys_parts.append("# Relevant memory\n"
                             + "\n".join(f"- {r.content}" for r in recalled))
        wf = Path(self.working_file)
        if wf.exists():
            sys_parts.append("# Working state (recovered)\n" + wf.read_text(encoding="utf-8"))

        msgs: list[Message] = [Message("system", "\n\n".join(p for p in sys_parts if p))]
        msgs.extend(history)
        msgs.append(Message("user", user_input))

        if self.engine.should_compress(msgs):
            self._flush(history)               # durable recovery snapshot first
            msgs = self.engine.compress(msgs)  # cache-safe middle compaction
        return msgs

    def _truncate(self, msgs: list[Message]) -> list[Message]:
        """Keep the system message + the most recent turns that fit the budget."""
        if not msgs:
            return msgs
        system = msgs[:1] if msgs[0].role == "system" else []
        rest = msgs[len(system):]
        budget = self.budget.max_tokens - self.budget.reserve_for_reply
        used = sum(estimate_tokens(m.content) for m in system)
        kept: list[Message] = []
        for m in reversed(rest):
            t = estimate_tokens(m.content)
            if used + t > budget:
                break
            kept.append(m)
            used += t
        kept.reverse()
        return system + kept

    def _flush(self, history: list[Message]) -> None:
        recent = "\n".join(f"[{m.role}] {m.content[:500]}" for m in history[-6:])
        snapshot = ("# E.D.I.T.H working state (auto-flushed before compaction)\n\n"
                    "## Recent turns\n" + recent + "\n")
        wf = Path(self.working_file)
        wf.parent.mkdir(parents=True, exist_ok=True)
        wf.write_text(snapshot, encoding="utf-8")
        try:
            self.memory.remember(f"Conversation checkpoint: {recent[:800]}",
                                 layer=MemoryLayer.EPISODIC, key="checkpoint")
        except Exception:
            pass
