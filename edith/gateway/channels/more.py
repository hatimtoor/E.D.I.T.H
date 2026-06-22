"""All remaining channel adapters — dependency-free (raw HTTP REST / stdlib sockets).

Each implements a real `send` via the platform's REST/webhook API; `poll`/`parse_webhook`
are provided where the platform allows pull/webhook inbound. Socket/SDK-heavy platforms
(Discord/Slack/IRC/Twitch) send via REST and take inbound via their gateway/webhook runner.
`to` semantics are noted per class. Credentials come from env (see registry `needs`).
"""
from __future__ import annotations

import os

from edith.channels.base import InboundMessage, OutboundMessage
from edith.gateway.base import BaseChannel


# ── helpers ─────────────────────────────────────────────────────────
def _env(*names: str) -> bool:
    return all(os.getenv(n) for n in names)


# ── Discord (REST send; inbound via gateway/webhook runner) ─────────
class DiscordChannel(BaseChannel):
    name = "discord"           # `to` = channel id

    def is_configured(self): return bool(os.getenv("EDITH_DISCORD_TOKEN"))

    def send(self, to, message: OutboundMessage):
        self._http_post(f"https://discord.com/api/v10/channels/{to}/messages",
                        {"content": message.text},
                        headers={"Authorization": f"Bot {os.getenv('EDITH_DISCORD_TOKEN')}"})

    @staticmethod
    def parse_webhook(p: dict):
        d = p.get("d") or p
        if d.get("content"):
            return [InboundMessage("discord", str(d.get("channel_id", "")), d["content"])]
        return []


# ── Slack (chat.postMessage; inbound via Events API webhook) ────────
class SlackChannel(BaseChannel):
    name = "slack"             # `to` = channel id

    def is_configured(self): return bool(os.getenv("EDITH_SLACK_BOT_TOKEN"))

    def send(self, to, message: OutboundMessage):
        self._http_post("https://slack.com/api/chat.postMessage",
                        {"channel": to, "text": message.text},
                        headers={"Authorization": f"Bearer {os.getenv('EDITH_SLACK_BOT_TOKEN')}"})

    @staticmethod
    def parse_webhook(p: dict):
        e = p.get("event", {})
        if e.get("type") == "message" and e.get("text") and not e.get("bot_id"):
            return [InboundMessage("slack", e.get("channel", ""), e["text"], meta={"user": e.get("user")})]
        return []


# ── Signal (signal-cli REST daemon) ─────────────────────────────────
class SignalChannel(BaseChannel):
    name = "signal"

    def is_configured(self): return _env("EDITH_SIGNAL_URL", "EDITH_SIGNAL_NUMBER")

    def send(self, to, message: OutboundMessage):
        self._http_post(f"{os.getenv('EDITH_SIGNAL_URL')}/v2/send",
                        {"message": message.text, "number": os.getenv("EDITH_SIGNAL_NUMBER"),
                         "recipients": [to]})

    def poll(self):
        if not self.is_configured():
            return []
        data = self._http_get(f"{os.getenv('EDITH_SIGNAL_URL')}/v1/receive/"
                              f"{os.getenv('EDITH_SIGNAL_NUMBER')}")
        out = []
        for item in (data if isinstance(data, list) else []):
            env = item.get("envelope", {})
            dm = env.get("dataMessage") or {}
            if dm.get("message"):
                out.append(InboundMessage("signal", env.get("source", ""), dm["message"]))
        return out


# ── iMessage (BlueBubbles REST) ─────────────────────────────────────
class IMessageChannel(BaseChannel):
    name = "imessage"

    def is_configured(self): return _env("EDITH_BLUEBUBBLES_URL", "EDITH_BLUEBUBBLES_PASSWORD")

    def send(self, to, message: OutboundMessage):
        url = (f"{os.getenv('EDITH_BLUEBUBBLES_URL')}/api/v1/message/text"
               f"?password={os.getenv('EDITH_BLUEBUBBLES_PASSWORD')}")
        self._http_post(url, {"chatGuid": to, "message": message.text})


# ── Matrix (client-server API) ──────────────────────────────────────
class MatrixChannel(BaseChannel):
    name = "matrix"            # `to` = room id

    def is_configured(self): return _env("EDITH_MATRIX_HS", "EDITH_MATRIX_TOKEN")

    def send(self, to, message: OutboundMessage):
        import time
        hs, tok = os.getenv("EDITH_MATRIX_HS"), os.getenv("EDITH_MATRIX_TOKEN")
        txn = str(int(time.time() * 1000))
        self._http_post(
            f"{hs}/_matrix/client/v3/rooms/{to}/send/m.room.message/{txn}?access_token={tok}",
            {"msgtype": "m.text", "body": message.text})


# ── Simple JSON-webhook senders (bots/connectors) ───────────────────
class GoogleChatChannel(BaseChannel):
    name = "googlechat"
    def is_configured(self): return bool(os.getenv("EDITH_GCHAT_WEBHOOK"))
    def send(self, to, message): self._http_post(os.getenv("EDITH_GCHAT_WEBHOOK"), {"text": message.text})


class TeamsChannel(BaseChannel):
    name = "msteams"
    def is_configured(self): return bool(os.getenv("EDITH_TEAMS_WEBHOOK"))
    def send(self, to, message): self._http_post(os.getenv("EDITH_TEAMS_WEBHOOK"), {"text": message.text})


class FeishuChannel(BaseChannel):
    name = "feishu"
    def is_configured(self): return bool(os.getenv("EDITH_FEISHU_WEBHOOK"))
    def send(self, to, message):
        self._http_post(os.getenv("EDITH_FEISHU_WEBHOOK"),
                        {"msg_type": "text", "content": {"text": message.text}})


class WeComChannel(BaseChannel):
    name = "wecom"
    def is_configured(self): return bool(os.getenv("EDITH_WECOM_WEBHOOK"))
    def send(self, to, message):
        self._http_post(os.getenv("EDITH_WECOM_WEBHOOK"),
                        {"msgtype": "text", "text": {"content": message.text}})


class DingTalkChannel(BaseChannel):
    name = "dingtalk"
    def is_configured(self): return bool(os.getenv("EDITH_DINGTALK_TOKEN"))
    def send(self, to, message):
        self._http_post(f"https://oapi.dingtalk.com/robot/send?access_token="
                        f"{os.getenv('EDITH_DINGTALK_TOKEN')}",
                        {"msgtype": "text", "text": {"content": message.text}})


class SynologyChatChannel(BaseChannel):
    name = "synology-chat"
    def is_configured(self): return bool(os.getenv("EDITH_SYNOLOGY_WEBHOOK"))
    def send(self, to, message):
        import json as _j
        self._http_post_form(os.getenv("EDITH_SYNOLOGY_WEBHOOK"),
                             {"payload": _j.dumps({"text": message.text})})


# ── LINE (push API) ─────────────────────────────────────────────────
class LineChannel(BaseChannel):
    name = "line"              # `to` = user/group id
    def is_configured(self): return bool(os.getenv("EDITH_LINE_TOKEN"))
    def send(self, to, message):
        self._http_post("https://api.line.me/v2/bot/message/push",
                        {"to": to, "messages": [{"type": "text", "text": message.text}]},
                        headers={"Authorization": f"Bearer {os.getenv('EDITH_LINE_TOKEN')}"})

    @staticmethod
    def parse_webhook(p: dict):
        out = []
        for ev in p.get("events", []):
            if ev.get("type") == "message" and ev.get("message", {}).get("type") == "text":
                src = ev.get("source", {})
                out.append(InboundMessage("line", src.get("userId") or src.get("groupId", ""),
                                          ev["message"]["text"]))
        return out


# ── Mattermost (REST) ───────────────────────────────────────────────
class MattermostChannel(BaseChannel):
    name = "mattermost"        # `to` = channel id
    def is_configured(self): return _env("EDITH_MATTERMOST_URL", "EDITH_MATTERMOST_TOKEN")
    def send(self, to, message):
        self._http_post(f"{os.getenv('EDITH_MATTERMOST_URL')}/api/v4/posts",
                        {"channel_id": to, "message": message.text},
                        headers={"Authorization": f"Bearer {os.getenv('EDITH_MATTERMOST_TOKEN')}"})


# ── Nextcloud Talk (OCS) ────────────────────────────────────────────
class NextcloudTalkChannel(BaseChannel):
    name = "nextcloud-talk"    # `to` = conversation token
    def is_configured(self): return _env("EDITH_NCTALK_URL", "EDITH_NCTALK_USER", "EDITH_NCTALK_PASS")
    def send(self, to, message):
        url = f"{os.getenv('EDITH_NCTALK_URL')}/ocs/v2.php/apps/spreed/api/v1/chat/{to}"
        h = {"OCS-APIRequest": "true", "Accept": "application/json",
             **self._basic_auth(os.getenv("EDITH_NCTALK_USER"), os.getenv("EDITH_NCTALK_PASS"))}
        self._http_post(url, {"message": message.text}, headers=h)


# ── SMS (Twilio REST, form-encoded + basic auth) ────────────────────
class SmsChannel(BaseChannel):
    name = "sms"
    def is_configured(self): return _env("EDITH_TWILIO_SID", "EDITH_TWILIO_TOKEN", "EDITH_TWILIO_FROM")
    def send(self, to, message):
        sid = os.getenv("EDITH_TWILIO_SID")
        self._http_post_form(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            {"To": to, "From": os.getenv("EDITH_TWILIO_FROM"), "Body": message.text},
            headers=self._basic_auth(sid, os.getenv("EDITH_TWILIO_TOKEN")))


# ── Email (stdlib SMTP send + IMAP poll) ────────────────────────────
class EmailChannel(BaseChannel):
    name = "email"
    def is_configured(self): return _env("EDITH_SMTP_HOST", "EDITH_EMAIL_USER", "EDITH_EMAIL_PASS")

    def send(self, to, message: OutboundMessage):
        import smtplib
        from email.message import EmailMessage
        m = EmailMessage()
        m["From"] = os.getenv("EDITH_EMAIL_USER"); m["To"] = to
        m["Subject"] = "E.D.I.T.H"; m.set_content(message.text)
        host, port = os.getenv("EDITH_SMTP_HOST"), int(os.getenv("EDITH_SMTP_PORT", "587"))
        with smtplib.SMTP(host, port) as s:
            s.starttls()
            s.login(os.getenv("EDITH_EMAIL_USER"), os.getenv("EDITH_EMAIL_PASS"))
            s.send_message(m)


# ── Twitch (Helix send) ─────────────────────────────────────────────
class TwitchChannel(BaseChannel):
    name = "twitch"            # `to` = broadcaster id
    def is_configured(self): return _env("EDITH_TWITCH_TOKEN", "EDITH_TWITCH_CLIENT_ID",
                                         "EDITH_TWITCH_SENDER_ID")
    def send(self, to, message):
        self._http_post("https://api.twitch.tv/helix/chat/messages",
                        {"broadcaster_id": to, "sender_id": os.getenv("EDITH_TWITCH_SENDER_ID"),
                         "message": message.text},
                        headers={"Authorization": f"Bearer {os.getenv('EDITH_TWITCH_TOKEN')}",
                                 "Client-Id": os.getenv("EDITH_TWITCH_CLIENT_ID")})


# ── IRC (raw socket, short-lived send) ──────────────────────────────
class IrcChannel(BaseChannel):
    name = "irc"               # `to` = #channel or nick
    def is_configured(self): return _env("EDITH_IRC_SERVER", "EDITH_IRC_NICK")
    def send(self, to, message: OutboundMessage):
        import socket as _s
        host, _, port = os.getenv("EDITH_IRC_SERVER").partition(":")
        nick = os.getenv("EDITH_IRC_NICK")
        with _s.create_connection((host, int(port or 6667)), timeout=15) as c:
            c.sendall(f"NICK {nick}\r\nUSER {nick} 0 * :{nick}\r\n".encode())
            for line in message.text.splitlines() or [message.text]:
                c.sendall(f"PRIVMSG {to} :{line}\r\n".encode())
            c.sendall(b"QUIT\r\n")


# ── Nostr (NIP-04 DM) — requires the optional 'nostr' crypto lib ────
class NostrChannel(BaseChannel):
    name = "nostr"
    def is_configured(self): return bool(os.getenv("EDITH_NOSTR_NSEC"))
    def send(self, to, message: OutboundMessage):  # pragma: no cover - needs crypto + relay WS
        raise RuntimeError("nostr send needs the optional 'nostr'/'pynostr' lib + relay; "
                           "pip install pynostr and configure EDITH_NOSTR_RELAYS")


# ── QQ Bot (official REST) ──────────────────────────────────────────
class QQBotChannel(BaseChannel):
    name = "qqbot"             # `to` = channel id
    def is_configured(self): return _env("EDITH_QQ_TOKEN", "EDITH_QQ_APPID")
    def send(self, to, message):
        self._http_post(f"https://api.sgroup.qq.com/channels/{to}/messages",
                        {"content": message.text},
                        headers={"Authorization": f"QQBot {os.getenv('EDITH_QQ_TOKEN')}",
                                 "X-Union-Appid": os.getenv("EDITH_QQ_APPID")})


# ── Voice call (Twilio call w/ spoken text) ─────────────────────────
class VoiceCallChannel(BaseChannel):
    name = "voice-call"
    def is_configured(self): return _env("EDITH_TWILIO_SID", "EDITH_TWILIO_TOKEN", "EDITH_TWILIO_FROM")
    def send(self, to, message: OutboundMessage):
        sid = os.getenv("EDITH_TWILIO_SID")
        twiml = f"<Response><Say>{message.text}</Say></Response>"
        self._http_post_form(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json",
            {"To": to, "From": os.getenv("EDITH_TWILIO_FROM"), "Twiml": twiml},
            headers=self._basic_auth(sid, os.getenv("EDITH_TWILIO_TOKEN")))


ALL_ADAPTERS = [
    DiscordChannel, SlackChannel, SignalChannel, IMessageChannel, MatrixChannel,
    GoogleChatChannel, TeamsChannel, FeishuChannel, WeComChannel, DingTalkChannel,
    SynologyChatChannel, LineChannel, MattermostChannel, NextcloudTalkChannel, SmsChannel,
    EmailChannel, TwitchChannel, IrcChannel, NostrChannel, QQBotChannel, VoiceCallChannel,
]
