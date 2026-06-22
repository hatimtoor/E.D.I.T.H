"""BaseChannel — the uniform adapter contract every platform implements.

Sync poll-model (the gateway loop calls poll() then send()). Dependency-free HTTP helpers
(urllib) so adapters need no heavy SDK; `_http_post`/`_http_get` are monkeypatchable in tests.
Reuses InboundMessage/OutboundMessage from edith.channels.base.
"""
from __future__ import annotations

import json
import urllib.request

from edith.channels.base import InboundMessage, OutboundMessage  # noqa: F401 (re-exported)


class BaseChannel:
    name: str = "base"

    def __init__(self, **config):
        self.config = config

    def is_configured(self) -> bool:
        """True if required credentials are present (override per channel)."""
        return True

    def poll(self) -> list[InboundMessage]:
        """Return any new inbound messages (poll transports). Default: none."""
        return []

    def send(self, to: str, message: OutboundMessage) -> None:
        raise NotImplementedError

    # ── dependency-free HTTP (overridable for tests) ────────────────
    @staticmethod
    def _http_post(url: str, payload: dict, *, headers: dict | None = None, timeout: int = 30) -> dict:
        data = json.dumps(payload).encode("utf-8")
        h = {"Content-Type": "application/json", **(headers or {})}
        req = urllib.request.Request(url, data=data, headers=h, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
        return json.loads(body) if body.strip().startswith(("{", "[")) else {"raw": body}

    @staticmethod
    def _http_get(url: str, *, timeout: int = 35) -> dict:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
        return json.loads(body) if body.strip().startswith(("{", "[")) else {"raw": body}
