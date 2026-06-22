"""Concrete channel adapters. Importing this registers the live ones."""
from edith.gateway.channels.telegram import TelegramChannel
from edith.gateway.channels.whatsapp import WhatsAppChannel
from edith.gateway.channels.webhook import WebhookChannel
from edith.gateway.registry import register_channel

register_channel("telegram", TelegramChannel)
register_channel("whatsapp", WhatsAppChannel)
register_channel("webhook", WebhookChannel)

__all__ = ["TelegramChannel", "WhatsAppChannel", "WebhookChannel"]
