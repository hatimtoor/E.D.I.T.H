"""MemoryProvider ABC: default local provider + pluggable registration + agent routing."""
from edith.memory import (LocalMemoryProvider, MemoryStore, MemoryProvider,
                          register_memory_provider, get_memory_provider, list_memory_providers)


def test_local_provider_roundtrip(tmp_path):
    store = MemoryStore(str(tmp_path / "m.sqlite"), embed_dim=128)
    p = LocalMemoryProvider(store)
    assert p.is_available()
    p.sync_turn("the vault token is rotated weekly", "noted")
    assert any("vault token" in x for x in p.prefetch("vault token rotation"))


def test_registry_and_custom_provider():
    class DummyProvider(MemoryProvider):
        name = "dummy"
        def __init__(self, store=None): self.items = []
        def is_available(self): return True
        def prefetch(self, query, *, limit=5): return self.items[-limit:]
        def sync_turn(self, user, assistant): self.items.append(user)
    register_memory_provider("dummy", DummyProvider)
    assert "dummy" in list_memory_providers()
    assert get_memory_provider("dummy") is DummyProvider


def test_agent_uses_configured_provider(tmp_path):
    from edith.core.agent import Agent
    from edith.core.config import Config, MemoryConfig
    cfg = Config(home=str(tmp_path / "home"),
                 memory=MemoryConfig(db_path=str(tmp_path / "home" / "m.sqlite"),
                                     embed_dim=128, provider="local"))
    a = Agent(config=cfg)
    assert a.memory_provider.name == "local"
    a._remember_turn("I always deploy on fridays", "ok")
    assert any("fridays" in x for x in a.memory_provider.prefetch("deploy schedule"))
    a.close()


def test_unknown_provider_falls_back_to_local(tmp_path):
    from edith.core.agent import Agent
    from edith.core.config import Config, MemoryConfig
    cfg = Config(home=str(tmp_path / "h"),
                 memory=MemoryConfig(db_path=str(tmp_path / "h" / "m.sqlite"),
                                     embed_dim=128, provider="does-not-exist"))
    a = Agent(config=cfg)
    assert a.memory_provider.name == "local"
    a.close()
