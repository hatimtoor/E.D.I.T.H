"""ruflo orchestration bridge.

ruflo exposes MCP tools (memory_store, memory_search, swarm_init, agent_spawn,
hooks_route). When the MCP server is connected, E.D.I.T.H delegates swarm
coordination and shared memory to it. When it is NOT connected (the common case),
this bridge transparently falls back to E.D.I.T.H's local MemoryStore + an in-process
task runner, so nothing breaks.
"""
from edith.ruflo.bridge import RufloBridge

__all__ = ["RufloBridge"]
