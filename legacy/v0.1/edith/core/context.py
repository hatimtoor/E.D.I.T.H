"""Context builder + pre-compaction flush.

Fixes OpenClaw's documented "context drift": when the gateway compacts a long
conversation it loses system instructions and repeats corrected mistakes. E.D.I.T.H
detects the approaching token ceiling and flushes the durable facts to WORKING.md
(and episodic memory) BEFORE truncation, then reloads them after.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from edith.core.llm import Message
from edith.memory import MemoryLayer, MemoryStore
from edith.skills import SkillLevel, SkillRegistry


def estimate_tokens(text: str) -> int:
    # cheap heuristic: ~4 chars/token. Good enough for budget gating.
    return max(1, len(text) // 4)


@dataclass
class ContextBudget:
    max_tokens: int = 180_000
    flush_at: float = 0.75          # flush when we cross 75% of budget
    reserve_for_reply: int = 8_000


@dataclass
class ContextBuilder:
    memory: MemoryStore
    skills: SkillRegistry
    system_prompt: str = ""
    budget: ContextBudget = field(default_factory=ContextBudget)
    working_file: str = "WORKING.md"

    def build(self, user_input: str, history: list[Message]) -> list[Message]:
        msgs: list[Message] = []
        sys_parts = [self.system_prompt] if self.system_prompt else []

        # progressive skills: only SUMMARY level in context -> fixes token blowup
        sys_parts.append("# Available skills (summaries; load body on demand)\n"
                         + self.skills.catalog(SkillLevel.SUMMARY))

        # relevant episodic memory for this turn (namespaced, deduped at write time)
        recalled = self.memory.recall(user_input, layer=MemoryLayer.EPISODIC, limit=5)
        if recalled:
            sys_parts.append("# Relevant memory\n"
                             + "\n".join(f"- {r.content}" for r in recalled))

        # restore any prior WORKING.md state (post-compaction recovery)
        wf = Path(self.working_file)
        if wf.exists():
            sys_parts.append("# Working state (recovered)\n" + wf.read_text(encoding="utf-8"))

        msgs.append(Message("system", "\n\n".join(p for p in sys_parts if p)))
        msgs.extend(history)
        msgs.append(Message("user", user_input))

        # FIX(OpenClaw drift): pre-compaction flush if we're over the high-water mark
        total = sum(estimate_tokens(m.content) for m in msgs)
        if total > self.budget.max_tokens * self.budget.flush_at:
            self._flush(history)
        return msgs

    def _flush(self, history: list[Message]) -> None:
        """Persist durable facts before the context gets truncated."""
        # naive but effective: keep the last assistant turn + write a state snapshot.
        recent = "\n".join(f"[{m.role}] {m.content[:500]}" for m in history[-6:])
        snapshot = (
            "# E.D.I.T.H working state (auto-flushed before compaction)\n\n"
            "## Recent turns\n" + recent + "\n"
        )
        Path(self.working_file).write_text(snapshot, encoding="utf-8")
        # also store a compact summary into episodic memory for long-term recall
        try:
            self.memory.remember(
                f"Conversation checkpoint: {recent[:800]}",
                layer=MemoryLayer.EPISODIC, key="checkpoint",
            )
        except Exception:
            pass
