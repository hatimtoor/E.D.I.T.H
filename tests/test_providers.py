"""Provider profile registry + LLMClient resolution (no network)."""
import pytest

from edith.core.llm import LLMClient, LLMError
from edith.core.providers import get_provider, list_providers, register_provider, ProviderProfile


def test_builtin_profiles_present():
    names = list_providers()
    for n in ("anthropic", "openai", "openrouter", "ollama", "lmstudio", "deepseek", "nous"):
        assert n in names


def test_alias_resolves():
    assert get_provider("claude").name == "anthropic"
    assert get_provider("gpt").name == "openai"


def test_client_picks_profile_and_mode():
    c = LLMClient("deepseek:deepseek-chat")
    assert c.profile.api_mode == "openai"
    assert c.profile.base_url == "https://api.deepseek.com/v1"


def test_local_provider_needs_no_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    c = LLMClient("ollama:llama3.1")
    assert c._resolve_key() == "ollama"   # placeholder, no real key required


def test_missing_cloud_key_raises(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    c = LLMClient("deepseek:deepseek-chat")
    with pytest.raises(LLMError):
        c.chat([])  # no key -> clean error before any network call


def test_register_new_provider():
    register_provider(ProviderProfile("acme", "openai", base_url="https://acme/v1",
                                      env_key="ACME_KEY"))
    assert get_provider("acme").base_url == "https://acme/v1"
