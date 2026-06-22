"""Generic webhook / in-process channel — dependency-free, works immediately.

Inbound messages are pushed into a queue (by an HTTP webhook handler or directly in tests);
outbound replies are collected. Doubles as the inbound bridge for webhook-only platforms
(e.g. WhatsApp Cloud) and as a fully testable local channel.
"""
from __future__ import annotations

from collections import deque

from edith.channels.base import InboundMessage, OutboundMessage
from edith.gateway.base import BaseChannel


class WebhookChannel(BaseChannel):
    name = "webhook"

    def __init__(self, **config):
        super().__init__(**config)
        self._inbox: deque[InboundMessage] = deque()
        self.sent: list[tuple[str, OutboundMessage]] = []

    def push(self, message: InboundMessage) -> None:
        """Feed an inbound message (from an HTTP handler or a test)."""
        self._inbox.append(message)

    def poll(self) -> list[InboundMessage]:
        out = list(self._inbox)
        self._inbox.clear()
        return out

    def send(self, to: str, message: OutboundMessage) -> None:
        self.sent.append((to, message))
