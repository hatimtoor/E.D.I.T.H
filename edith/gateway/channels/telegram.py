"""Telegram channel — Bot API via raw HTTP (no SDK). poll() = getUpdates, send() = sendMessage."""
from __future__ import annotations

import os

from edith.channels.base import InboundMessage, OutboundMessage
from edith.gateway.base import BaseChannel

_API = "https://api.telegram.org/bot{token}/{method}"


class TelegramChannel(BaseChannel):
    name = "telegram"

    def __init__(self, token: str | None = None, **config):
        super().__init__(**config)
        self.token = token or os.getenv("EDITH_TELEGRAM_TOKEN")
        self._offset = 0

    def is_configured(self) -> bool:
        return bool(self.token)

    def _url(self, method: str) -> str:
        return _API.format(token=self.token, method=method)

    def poll(self) -> list[InboundMessage]:
        if not self.token:
            return []
        data = self._http_get(self._url(f"getUpdates?timeout=30&offset={self._offset}"))
        out: list[InboundMessage] = []
        for upd in data.get("result", []):
            self._offset = max(self._offset, upd.get("update_id", 0) + 1)
            msg = upd.get("message") or upd.get("channel_post")
            if not msg or "text" not in msg:
                continue
            chat = msg.get("chat", {})
            is_group = chat.get("type") in ("group", "supergroup")
            out.append(InboundMessage(
                channel=self.name, sender=str(chat.get("id")), text=msg["text"],
                is_group=is_group, group_id=str(chat.get("id")) if is_group else None,
                meta={"message_id": msg.get("message_id")}))
        return out

    def send(self, to: str, message: OutboundMessage) -> None:
        if not self.token:
            raise RuntimeError("telegram not configured (EDITH_TELEGRAM_TOKEN)")
        self._http_post(self._url("sendMessage"),
                        {"chat_id": to, "text": message.text, "parse_mode": "Markdown"})
