"""3-layer memory: Working / Episodic / Procedural.

Fixes: Hermes "junk drawer" vector collisions -> profile namespacing + dedup;
OpenClaw prompt-injection via memory -> injection scan on every write.
"""
from edith.memory.store import MemoryStore, MemoryLayer, MemoryRecord
from edith.memory.provider import (
    MemoryProvider, LocalMemoryProvider,
    register_memory_provider, get_memory_provider, list_memory_providers,
)

__all__ = [
    "MemoryStore", "MemoryLayer", "MemoryRecord",
    "MemoryProvider", "LocalMemoryProvider",
    "register_memory_provider", "get_memory_provider", "list_memory_providers",
]
