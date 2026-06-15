"""Channel adapters — the OpenClaw-style gateway surface.

v0.1 ships the abstract base + a local CLI channel. Network adapters (WhatsApp/Telegram/
Discord/Signal/...) implement the same `Channel` interface; the agent core never changes.
"""
from edith.channels.base import Channel, InboundMessage, OutboundMessage, CLIChannel

__all__ = ["Channel", "InboundMessage", "OutboundMessage", "CLIChannel"]
