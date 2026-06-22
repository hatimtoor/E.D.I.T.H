"""Broad provider ecosystem + env-overridable base_url/key (OpenClaw/Hermes-style)."""
from edith.core.llm import LLMClient
from edith.core.providers import get_provider, list_providers


def test_ecosystem_breadth():
    names = set(list_providers())
    for n in ("openrouter", "nvidia", "opencode", "groq", "together", "fireworks", "mistral",
              "deepinfra", "cerebras", "perplexity", "xai", "moonshot", "novita", "huggingface",
              "qwen", "zai", "minimax", "ollama", "lmstudio", "vllm", "custom"):
        assert n in names, f"missing provider {n}"
    assert len(names) >= 30


def test_nvidia_base_url():
    assert get_provider("nvidia").base_url == "https://integrate.api.nvidia.com/v1"


def test_aliases_resolve():
    assert get_provider("zen").name == "opencode"
    assert get_provider("grok").name == "xai"
    assert get_provider("kimi").name == "moonshot"


def test_key_from_conventional_env(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "nv-123")
    assert LLMClient("nvidia:meta/llama-3.1-8b")._resolve_key() == "nv-123"


def test_edith_prefixed_key_and_base_override(monkeypatch):
    monkeypatch.setenv("EDITH_TOGETHER_API_KEY", "tk")
    monkeypatch.setenv("EDITH_TOGETHER_BASE_URL", "https://my-proxy/v1")
    c = LLMClient("together:x")
    assert c._resolve_key() == "tk"
    assert c._resolve_base_url() == "https://my-proxy/v1"


def test_custom_provider_points_anywhere(monkeypatch):
    monkeypatch.setenv("EDITH_CUSTOM_API_KEY", "k")
    monkeypatch.setenv("EDITH_CUSTOM_BASE_URL", "http://localhost:9999/v1")
    c = LLMClient("custom:some-model")
    assert c._resolve_key() == "k" and c._resolve_base_url() == "http://localhost:9999/v1"
