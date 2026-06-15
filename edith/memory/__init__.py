"""3-layer memory: Working / Episodic / Procedural.

Fixes: Hermes "junk drawer" vector collisions -> profile namespacing + dedup;
OpenClaw prompt-injection via memory -> injection scan on every write.
"""
from edith.memory.store import MemoryStore, MemoryLayer, MemoryRecord

__all__ = ["MemoryStore", "MemoryLayer", "MemoryRecord"]
