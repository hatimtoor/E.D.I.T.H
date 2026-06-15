"""ruflo orchestration bridge (optional, build-time). Detects a local `ruflo` CLI and
delegates swarm/shared-memory to it; falls back to in-process tasks + local MemoryStore
when absent. ruflo is NOT a runtime dependency of E.D.I.T.H.
"""
from edith.ruflo.bridge import RufloBridge, SwarmHandle

__all__ = ["RufloBridge", "SwarmHandle"]
