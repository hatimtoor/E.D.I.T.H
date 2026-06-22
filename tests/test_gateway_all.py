"""All channel adapters: every planned channel is now live; sends build correct requests."""
import edith.gateway.channels  # registers all
from edith.channels.base import OutboundMessage
from edith.gateway.base import BaseChannel
from edith.gateway.registry import CHANNELS, live_channels
from edith.gateway.channels.more import (
    DiscordChannel, SlackChannel, DingTalkChannel, LineChannel, MatrixChannel, SignalChannel)


def test_no_planned_channels_remain():
    planned = [n for n, s in CHANNELS.items() if s.status != "live"]
    assert planned == [], f"still planned: {planned}"
    # spot-check breadth
    for n in ("discord", "slack", "signal", "matrix", "line", "sms", "email", "irc",
              "twitch", "wecom", "dingtalk", "feishu", "qqbot", "voice-call"):
        assert n in set(live_channels())


def _capture(monkeypatch):
    calls = {}
    monkeypatch.setattr(BaseChannel, "_http_post",
                        staticmethod(lambda url, payload, **kw: calls.update(
                            url=url, payload=payload, headers=kw.get("headers")) or {}))
    return calls


def test_discord_send(monkeypatch):
    monkeypatch.setenv("EDITH_DISCORD_TOKEN", "tok")
    c = _capture(monkeypatch)
    DiscordChannel().send("123", OutboundMessage("hi"))
    assert "/channels/123/messages" in c["url"] and c["payload"]["content"] == "hi"
    assert c["headers"]["Authorization"].startswith("Bot ")


def test_slack_send(monkeypatch):
    monkeypatch.setenv("EDITH_SLACK_BOT_TOKEN", "xoxb")
    c = _capture(monkeypatch)
    SlackChannel().send("C1", OutboundMessage("yo"))
    assert c["url"].endswith("chat.postMessage") and c["payload"]["channel"] == "C1"


def test_dingtalk_send(monkeypatch):
    monkeypatch.setenv("EDITH_DINGTALK_TOKEN", "t")
    c = _capture(monkeypatch)
    DingTalkChannel().send("x", OutboundMessage("m"))
    assert c["payload"] == {"msgtype": "text", "text": {"content": "m"}}


def test_matrix_send(monkeypatch):
    monkeypatch.setenv("EDITH_MATRIX_HS", "https://hs"); monkeypatch.setenv("EDITH_MATRIX_TOKEN", "t")
    c = _capture(monkeypatch)
    MatrixChannel().send("!room:hs", OutboundMessage("hello"))
    assert "/rooms/!room:hs/send/m.room.message/" in c["url"]
    assert c["payload"]["body"] == "hello"


def test_line_webhook_parse():
    p = {"events": [{"type": "message", "message": {"type": "text", "text": "hey"},
                     "source": {"userId": "U1"}}]}
    msgs = LineChannel.parse_webhook(p)
    assert msgs[0].sender == "U1" and msgs[0].text == "hey"


def test_signal_not_configured_no_poll():
    assert SignalChannel().poll() == []
