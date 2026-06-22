"""Channel catalog + registry.

CHANNELS lists every messaging platform we target — the full set Hermes and OpenClaw support,
plus widely-requested ones — with status (live | planned), transport, and required credentials.
`register_channel` attaches a concrete adapter class to a spec when implemented.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChannelSpec:
    name: str
    transport: str                # poll | webhook | websocket | cli
    needs: list[str] = field(default_factory=list)   # required env vars / config
    status: str = "planned"       # live | planned
    note: str = ""
    adapter: type | None = None   # set when an adapter is registered


# Full target set (Hermes ∪ OpenClaw ∪ popular requests). status flips to "live"
# as adapters land. This is the roadmap + the source of truth for `gateway channels`.
CHANNELS: dict[str, ChannelSpec] = {s.name: s for s in [
    ChannelSpec("cli", "cli", [], "live", "local terminal channel"),
    ChannelSpec("webhook", "webhook", [], "live", "generic HTTP/in-process bridge"),
    ChannelSpec("telegram", "poll", ["EDITH_TELEGRAM_TOKEN"], "live", "Bot API (getUpdates)"),
    ChannelSpec("whatsapp", "webhook", ["EDITH_WHATSAPP_TOKEN", "EDITH_WHATSAPP_PHONE_ID"],
                "live", "WhatsApp Cloud API (send live; inbound via webhook)"),
    # ── planned (uniform adapter pattern; quick follow-ups) ──────────
    ChannelSpec("discord", "websocket", ["EDITH_DISCORD_TOKEN"], "planned"),
    ChannelSpec("slack", "websocket", ["EDITH_SLACK_BOT_TOKEN", "EDITH_SLACK_APP_TOKEN"], "planned"),
    ChannelSpec("signal", "poll", ["EDITH_SIGNAL_URL"], "planned", "signal-cli daemon"),
    ChannelSpec("imessage", "poll", [], "planned", "macOS Messages / BlueBubbles"),
    ChannelSpec("matrix", "poll", ["EDITH_MATRIX_HS", "EDITH_MATRIX_TOKEN"], "planned"),
    ChannelSpec("googlechat", "webhook", ["EDITH_GCHAT_WEBHOOK"], "planned"),
    ChannelSpec("msteams", "webhook", ["EDITH_TEAMS_APP_ID", "EDITH_TEAMS_APP_PASSWORD"], "planned"),
    ChannelSpec("feishu", "webhook", ["EDITH_FEISHU_APP_ID", "EDITH_FEISHU_APP_SECRET"], "planned"),
    ChannelSpec("wecom", "webhook", ["EDITH_WECOM_CORPID", "EDITH_WECOM_SECRET"], "planned"),
    ChannelSpec("dingtalk", "webhook", ["EDITH_DINGTALK_TOKEN"], "planned"),
    ChannelSpec("line", "webhook", ["EDITH_LINE_TOKEN"], "planned"),
    ChannelSpec("nostr", "websocket", ["EDITH_NOSTR_NSEC"], "planned", "NIP-04 DMs"),
    ChannelSpec("twitch", "websocket", ["EDITH_TWITCH_TOKEN"], "planned"),
    ChannelSpec("irc", "websocket", ["EDITH_IRC_SERVER"], "planned"),
    ChannelSpec("sms", "webhook", ["EDITH_TWILIO_SID", "EDITH_TWILIO_TOKEN"], "planned", "Twilio"),
    ChannelSpec("email", "poll", ["EDITH_IMAP_HOST", "EDITH_SMTP_HOST"], "planned", "IMAP/SMTP"),
    ChannelSpec("mattermost", "websocket", ["EDITH_MATTERMOST_URL"], "planned"),
    ChannelSpec("nextcloud-talk", "poll", ["EDITH_NCTALK_URL"], "planned"),
    ChannelSpec("qqbot", "websocket", ["EDITH_QQ_APPID"], "planned"),
    ChannelSpec("synology-chat", "webhook", ["EDITH_SYNOLOGY_WEBHOOK"], "planned"),
    ChannelSpec("voice-call", "webhook", ["EDITH_TWILIO_SID"], "planned", "Twilio/Telnyx/Plivo"),
]}


def register_channel(name: str, adapter: type) -> None:
    spec = CHANNELS.get(name)
    if spec:
        spec.adapter = adapter
        spec.status = "live"
    else:
        CHANNELS[name] = ChannelSpec(name, "poll", status="live", adapter=adapter)


def get_channel(name: str) -> ChannelSpec | None:
    return CHANNELS.get(name)


def live_channels() -> list[str]:
    return sorted(n for n, s in CHANNELS.items() if s.status == "live")
