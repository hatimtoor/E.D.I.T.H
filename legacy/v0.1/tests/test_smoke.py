"""Import smoke + sandbox guard + config overlay. Must pass with zero extra deps/keys."""
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


def test_sandbox_blocks_destructive():
    from edith.sandbox.backends import LocalBackend
    with pytest.raises(PermissionError):
        LocalBackend().run("rm -rf / ")


def test_vector_embeddings_are_normalized():
    from edith.memory.vector import embed, cosine
    v = embed("hello world", 64)
    assert abs(cosine(v, v) - 1.0) < 1e-6
