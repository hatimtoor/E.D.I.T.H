"""Import smoke + sandbox guard + config overlay + permission gate. No deps/keys needed."""
import importlib

import pytest

MODULES = [
    "edith", "edith.core.config", "edith.core.llm", "edith.core.context",
    "edith.core.agent", "edith.memory", "edith.memory.store", "edith.memory.vector",
    "edith.skills", "edith.skills.registry", "edith.browser", "edith.browser.stealth",
    "edith.security", "edith.security.authorization", "edith.security.recon",
    "edith.sandbox", "edith.sandbox.backends", "edith.ruflo", "edith.ruflo.bridge",
    "edith.channels", "edith.channels.base",
]


@pytest.mark.parametrize("mod", MODULES)
def test_imports_clean(mod):
    importlib.import_module(mod)


def test_config_env_overlay(monkeypatch):
    monkeypatch.setenv("EDITH_MODEL", "openai:gpt-4o")
    from edith.core.config import load_config
    assert load_config().model == "openai:gpt-4o"


def test_local_backend_needs_host_permission():
    from edith.sandbox.backends import LocalBackend
    from edith.core.config import PermissionLevel
    with pytest.raises(PermissionError):
        LocalBackend(permission_level=PermissionLevel.SANDBOXED).run("echo hi")


def test_sandbox_blocks_destructive():
    from edith.sandbox.backends import LocalBackend
    from edith.core.config import PermissionLevel
    with pytest.raises(PermissionError):
        LocalBackend(permission_level=PermissionLevel.HOST).run("rm -rf / ")


def test_channel_group_session_keyed_on_group():
    from edith.channels.base import InboundMessage
    a = InboundMessage("discord", "alice", "hi", is_group=True, group_id="g1")
    b = InboundMessage("discord", "bob", "yo", is_group=True, group_id="g1")
    assert a.session_key() == b.session_key()       # same group -> same session
    assert InboundMessage("discord", "alice", "x").session_key() == "main"


def test_vector_embeddings_are_normalized():
    from edith.memory.vector import embed, cosine
    v = embed("hello world", 64)
    assert abs(cosine(v, v) - 1.0) < 1e-6
