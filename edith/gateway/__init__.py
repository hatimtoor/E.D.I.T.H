"""Messaging gateway — the OpenClaw-style reach layer.

A long-running daemon that runs channel adapters (Telegram, WhatsApp, Discord, Slack, …),
normalizes every platform into one message shape, routes to a per-session Agent, and replies.
Channels register in a catalog so we track everything Hermes + OpenClaw support and what's live.
"""
from edith.gateway.base import BaseChannel
from edith.gateway.registry import ChannelSpec, CHANNELS, register_channel, get_channel
from edith.gateway.runtime import Gateway

__all__ = ["BaseChannel", "ChannelSpec", "CHANNELS", "register_channel", "get_channel", "Gateway"]
