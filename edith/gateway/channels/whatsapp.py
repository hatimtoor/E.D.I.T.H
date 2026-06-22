"""WhatsApp channel — Cloud API via raw HTTP (no SDK).

send() posts to the Graph API. Inbound arrives via Meta webhook (the WebhookChannel feeds it);
`parse_webhook()` normalizes a Meta webhook payload into InboundMessage(s).
"""
from __future__ import annotations

import os

from edith.channels.base import InboundMessage, OutboundMessage
from edith.gateway.base import BaseChannel

_GRAPH = "https://graph.facebook.com/v20.0/{phone_id}/messages"


class WhatsAppChannel(BaseChannel):
    name = "whatsapp"

    def __init__(self, token: str | None = None, phone_id: str | None = None, **config):
        super().__init__(**config)
        self.token = token or os.getenv("EDITH_WHATSAPP_TOKEN")
        self.phone_id = phone_id or os.getenv("EDITH_WHATSAPP_PHONE_ID")

    def is_configured(self) -> bool:
        return bool(self.token and self.phone_id)

    def send(self, to: str, message: OutboundMessage) -> None:
        if not self.is_configured():
            raise RuntimeError("whatsapp not configured (EDITH_WHATSAPP_TOKEN/PHONE_ID)")
        self._http_post(
            _GRAPH.format(phone_id=self.phone_id),
            {"messaging_product": "whatsapp", "to": to, "type": "text",
             "text": {"body": message.text}},
            headers={"Authorization": f"Bearer {self.token}"})

    @staticmethod
    def parse_webhook(payload: dict) -> list[InboundMessage]:
        """Normalize a Meta WhatsApp webhook payload into InboundMessages."""
        out: list[InboundMessage] = []
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for m in value.get("messages", []):
                    if m.get("type") != "text":
                        continue
                    out.append(InboundMessage(
                        channel="whatsapp", sender=m.get("from", ""),
                        text=m.get("text", {}).get("body", ""),
                        meta={"id": m.get("id")}))
        return out
