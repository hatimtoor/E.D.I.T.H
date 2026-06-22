"""Context engine — pluggable conversation compaction (narrow-waist ABC).

Ported concept from Hermes `agent/context_engine.py`: track token usage, and when the window
crosses a threshold, compress the *middle* of the conversation while protecting the head
(keeps the prompt-cache prefix stable) and the most recent turns. Default impl summarizes the
middle into one note. Third-party engines drop in by subclassing ContextEngine.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from edith.core.llm import Message


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)  # ~4 chars/token heuristic


@dataclass
class ContextEngine(ABC):
    max_tokens: int = 180_000
    threshold_percent: float = 0.75      # compress when usage crosses this
    protect_first_n: int = 3             # head messages kept verbatim (cache prefix)
    protect_last_n: int = 6              # most recent messages kept verbatim

    def total_tokens(self, messages: list[Message]) -> int:
        return sum(estimate_tokens(m.content) for m in messages)

    def should_compress(self, messages: list[Message]) -> bool:
        return self.total_tokens(messages) > self.max_tokens * self.threshold_percent

    @abstractmethod
    def compress(self, messages: list[Message]) -> list[Message]:
        ...


class ContextCompressor(ContextEngine):
    """Default engine: replace the unprotected middle with a single summary message.

    Layout preserved: [system?] + first_n + <summary> + last_n. The system message and the
    head stay byte-identical so the sacred prompt cache prefix is never invalidated.
    """

    def compress(self, messages: list[Message]) -> list[Message]:
        if not messages:
            return messages
        head_off = 1 if messages[0].role == "system" else 0
        system = messages[:head_off]
        body = messages[head_off:]
        keep_first = self.protect_first_n
        keep_last = self.protect_last_n
        if len(body) <= keep_first + keep_last:
            return messages  # nothing in the middle to compress
        first = body[:keep_first]
        middle = body[keep_first:len(body) - keep_last]
        last = body[len(body) - keep_last:]
        summary = self._summarize(middle)
        return system + first + [Message("user", summary)] + last

    def _summarize(self, middle: list[Message]) -> str:
        # Deterministic, offline summary (no LLM dependency). An LLM-backed engine can
        # override this to produce a higher-quality recap.
        lines = [f"- [{m.role}] {m.content[:160]}" for m in middle if m.content]
        body = "\n".join(lines[:40])
        return ("[context compacted — earlier conversation summary]\n" + body)
