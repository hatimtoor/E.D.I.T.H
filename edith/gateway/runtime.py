"""Gateway runtime — routes inbound messages to per-session agents and replies.

Per-session Agent cache (LRU + idle TTL, like Hermes' gateway): each conversation key gets its
own Agent (own memory profile, history, session row). `dispatch()` is the pure routing unit
(testable without network); `run()` drives the poll loop across all enabled channels.
"""
from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Callable

from edith.channels.base import InboundMessage, OutboundMessage
from edith.gateway.base import BaseChannel


@dataclass
class Gateway:
    agent_factory: Callable[[str], object]    # (session_key) -> Agent (with tools loaded)
    channels: list[BaseChannel] = field(default_factory=list)
    max_agents: int = 128
    idle_ttl: float = 3600.0
    _cache: "OrderedDict[str, tuple]" = field(default_factory=OrderedDict, init=False)

    # ── per-session agent cache ─────────────────────────────────────
    def _agent_for(self, key: str):
        now = time.time()
        self._evict(now)
        if key in self._cache:
            agent, _ = self._cache.pop(key)
            self._cache[key] = (agent, now)
            return agent
        agent = self.agent_factory(key)
        self._cache[key] = (agent, now)
        if len(self._cache) > self.max_agents:
            _, (old, _) = self._cache.popitem(last=False)
            _safe_close(old)
        return agent

    def _evict(self, now: float) -> None:
        for key in [k for k, (_, ts) in self._cache.items() if now - ts > self.idle_ttl]:
            _, (agent, _) = key, self._cache.pop(key)
            _safe_close(agent)

    # ── routing (pure, testable) ────────────────────────────────────
    def dispatch(self, inbound: InboundMessage) -> OutboundMessage:
        agent = self._agent_for(inbound.session_key())
        reply = agent.step(inbound.text)
        return OutboundMessage(text=reply)

    # ── daemon loop ─────────────────────────────────────────────────
    def run(self, *, poll_interval: float = 2.0, _max_iters: int | None = None) -> None:
        live = [c for c in self.channels if c.is_configured()]
        i = 0
        while _max_iters is None or i < _max_iters:
            for ch in live:
                for inbound in ch.poll():
                    out = self.dispatch(inbound)
                    ch.send(inbound.sender, out)
            i += 1
            if _max_iters is None or i < _max_iters:
                time.sleep(poll_interval)

    def close(self) -> None:
        for _, (agent, _) in self._cache.items():
            _safe_close(agent)
        self._cache.clear()


def _safe_close(agent) -> None:
    try:
        agent.close()
    except Exception:
        pass
