"""RufloBridge — optional swarm/memory orchestration with graceful fallback.

Detection strategy: ruflo's MCP tools are invoked by the host (Claude Code) layer,
not importable here directly. So the bridge probes for a local `ruflo` CLI / daemon;
if absent it marks itself inactive and callers use the provided local fallbacks.
This keeps E.D.I.T.H fully functional with OR without ruflo.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable


@dataclass
class SwarmHandle:
    topology: str
    agents: list[str]
    backend: str  # "ruflo" | "local"


class RufloBridge:
    def __init__(self, *, enabled: bool = True, default_topology: str = "hierarchical"):
        self.enabled = enabled
        self.default_topology = default_topology
        self._available = self._detect() if enabled else False

    def _detect(self) -> bool:
        if shutil.which("ruflo") is None:
            return False
        try:
            subprocess.run(["ruflo", "--version"], capture_output=True, timeout=5)
            return True
        except Exception:
            return False

    @property
    def active(self) -> bool:
        return self._available

    def status(self) -> str:
        if not self.enabled:
            return "ruflo: disabled (EDITH_RUFLO_ENABLED=false)"
        if self._available:
            return "ruflo: connected — swarm + shared memory delegated to ruflo"
        return ("ruflo: not detected — using local fallback (in-process tasks + "
                "local MemoryStore). Install/connect ruflo to enable distributed swarm.")

    # ── swarm ───────────────────────────────────────────────────────
    def swarm_init(self, agents: list[str], *, topology: str | None = None) -> SwarmHandle:
        topo = topology or self.default_topology
        if self._available:
            try:
                subprocess.run(
                    ["ruflo", "swarm", "init", "--topology", topo, "--agents", ",".join(agents)],
                    capture_output=True, timeout=30, check=True,
                )
                return SwarmHandle(topo, agents, "ruflo")
            except Exception:
                pass
        return SwarmHandle(topo, agents, "local")

    def run_parallel(self, jobs: list[Callable[[], object]]) -> list[object]:
        """Local fallback parallelism (threads). ruflo path would dispatch to agents."""
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=min(8, len(jobs) or 1)) as ex:
            return list(ex.map(lambda f: f(), jobs))

    # ── shared memory passthrough ───────────────────────────────────
    def memory_store(self, key: str, value: str, local_store=None) -> None:
        if self._available:
            try:
                subprocess.run(["ruflo", "memory", "store", key, value],
                               capture_output=True, timeout=15, check=True)
                return
            except Exception:
                pass
        if local_store is not None:
            local_store.remember(value, key=key)
