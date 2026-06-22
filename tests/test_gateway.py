"""Gateway: routing + per-session agent cache + channel catalog + adapters (no network)."""
from edith.channels.base import InboundMessage, OutboundMessage
from edith.gateway.runtime import Gateway
from edith.gateway.channels.webhook import WebhookChannel
from edith.gateway.channels.telegram import TelegramChannel
from edith.gateway.channels.whatsapp import WhatsAppChannel


class FakeAgent:
    def __init__(self, key): self.key = key; self.steps = 0; self.closed = False
    def step(self, text, **kw): self.steps += 1; return f"reply to {text!r}"
    def close(self): self.closed = True


def test_catalog_has_all_target_channels():
    import edith.gateway.channels  # registers live ones
    from edith.gateway.registry import CHANNELS, live_channels
    for must in ("telegram", "whatsapp", "discord", "slack", "signal", "matrix", "imessage",
                 "line", "wecom", "sms", "email"):
        assert must in CHANNELS
    assert {"telegram", "whatsapp", "webhook"} <= set(live_channels())


def test_dispatch_routes_and_caches_per_session():
    made = {}
    def factory(key):
        made[key] = made.get(key, 0) + 1
        return FakeAgent(key)
    gw = Gateway(agent_factory=factory)
    a = gw.dispatch(InboundMessage("webhook", "alice", "hi"))
    b = gw.dispatch(InboundMessage("webhook", "alice", "again"))
    assert a.text.startswith("reply to") and b.text
    assert made["main"] == 1   # same DM session -> one cached agent


def test_group_sessions_isolated():
    gw = Gateway(agent_factory=lambda k: FakeAgent(k))
    gw.dispatch(InboundMessage("telegram", "u1", "x", is_group=True, group_id="g1"))
    gw.dispatch(InboundMessage("telegram", "u2", "y", is_group=True, group_id="g2"))
    assert set(gw._cache) == {"telegram:g1", "telegram:g2"}


def test_run_loop_polls_and_replies():
    ch = WebhookChannel()
    ch.push(InboundMessage("webhook", "bob", "ping"))
    gw = Gateway(agent_factory=lambda k: FakeAgent(k), channels=[ch])
    gw.run(_max_iters=1, poll_interval=0)
    assert ch.sent and ch.sent[0][1].text == "reply to 'ping'"


def test_telegram_send_builds_request(monkeypatch):
    calls = {}
    monkeypatch.setattr(TelegramChannel, "_http_post",
                        staticmethod(lambda url, payload, **kw: calls.update(url=url, payload=payload) or {}))
    ch = TelegramChannel(token="T")
    ch.send("123", OutboundMessage("hello"))
    assert "sendMessage" in calls["url"] and calls["payload"]["chat_id"] == "123"


def test_telegram_poll_normalizes(monkeypatch):
    upd = {"result": [{"update_id": 5, "message": {"message_id": 1, "text": "yo",
            "chat": {"id": 99, "type": "private"}}}]}
    monkeypatch.setattr(TelegramChannel, "_http_get", staticmethod(lambda url, **kw: upd))
    ch = TelegramChannel(token="T")
    msgs = ch.poll()
    assert msgs[0].text == "yo" and msgs[0].sender == "99" and ch._offset == 6


def test_whatsapp_webhook_parse():
    payload = {"entry": [{"changes": [{"value": {"messages": [
        {"type": "text", "from": "1555", "text": {"body": "hey"}, "id": "wamid"}]}}]}]}
    msgs = WhatsAppChannel.parse_webhook(payload)
    assert msgs[0].sender == "1555" and msgs[0].text == "hey"
