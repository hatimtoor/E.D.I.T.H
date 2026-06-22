"""MemoryProvider — the narrow-waist for memory backends (ported from Hermes memory_provider).

The agent talks to ONE MemoryProvider. The default wraps our local namespaced SQLite+vector
`MemoryStore`; external backends (LanceDB, mem0, Honcho, …) implement the same ABC and drop in
via `register_memory_provider`. Lifecycle mirrors Hermes: prefetch(query) before a turn,
sync_turn(user,asst) after, system_prompt_block() for static context.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from edith.memory.store import InjectionBlocked, MemoryLayer, MemoryStore


class MemoryProvider(ABC):
    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def prefetch(self, query: str, *, limit: int = 5) -> list[str]:
        """Relevant memories to inject before a turn (recall)."""

    @abstractmethod
    def sync_turn(self, user: str, assistant: str) -> None:
        """Persist what's worth keeping from a completed turn (write)."""

    def system_prompt_block(self) -> str:
        """Optional static text injected into the system prompt at session start."""
        return ""


class LocalMemoryProvider(MemoryProvider):
    """Default provider — wraps the built-in namespaced SQLite + vector store."""

    name = "local"

    def __init__(self, store: MemoryStore):
        self.store = store

    def is_available(self) -> bool:
        return True

    def prefetch(self, query: str, *, limit: int = 5) -> list[str]:
        return [r.content for r in self.store.recall(query, layer=MemoryLayer.EPISODIC, limit=limit)]

    def sync_turn(self, user: str, assistant: str) -> None:
        try:
            self.store.remember(f"Q: {user}\nA: {assistant[:500]}", layer=MemoryLayer.EPISODIC)
        except InjectionBlocked:
            pass  # flagged content is simply not persisted


_REGISTRY: dict[str, type[MemoryProvider]] = {"local": LocalMemoryProvider}


def register_memory_provider(name: str, cls: type[MemoryProvider]) -> None:
    _REGISTRY[name] = cls


def get_memory_provider(name: str) -> type[MemoryProvider] | None:
    return _REGISTRY.get(name)


def list_memory_providers() -> list[str]:
    return sorted(_REGISTRY)
