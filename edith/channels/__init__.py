"""Channel adapters — the OpenClaw-style gateway surface.

v0.1 ships the abstract base + a local CLI channel only. Network adapters
(WhatsApp/Telegram/Discord/Signal/...) implement the same `Channel` interface and
are added incrementally; the agent core never changes when a channel is added.
This is the "broad reach" half of E.D.I.T.H (OpenClaw's strength).
"""
from edith.channels.base import Channel, InboundMessage, OutboundMessage, CLIChannel

__all__ = ["Channel", "InboundMessage", "OutboundMessage", "CLIChannel"]
