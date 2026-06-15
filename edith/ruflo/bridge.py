"""RufloBridge — optional swarm/memory orchestration with graceful fallback.

Probes for a local `ruflo` CLI; if absent it marks itself inactive and callers use the
provided local fallbacks. Keeps E.D.I.T.H fully functional with OR without ruflo.
"""
from __future__ import annotations

import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
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
            return "ruflo: detected — swarm + shared memory available via CLI"
        return ("ruflo: not detected — using local fallback (in-process tasks + local "
                "MemoryStore). Install ruflo to enable distributed swarm.")

    def swarm_init(self, agents: list[str], *, topology: str | None = None) -> SwarmHandle:
        topo = topology or self.default_topology
        if self._available:
            try:
                subprocess.run(["ruflo", "swarm", "init", "--topology", topo,
                                "--agents", ",".join(agents)],
                               capture_output=True, timeout=30, check=True)
                return SwarmHandle(topo, agents, "ruflo")
            except Exception:
                pass
        return SwarmHandle(topo, agents, "local")

    def run_parallel(self, jobs: list[Callable[[], object]]) -> list[object]:
        with ThreadPoolExecutor(max_workers=min(8, len(jobs) or 1)) as ex:
            return list(ex.map(lambda f: f(), jobs))

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
