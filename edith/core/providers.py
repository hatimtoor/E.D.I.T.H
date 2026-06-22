"""Provider profiles — the narrow-waist for LLM vendors (ported from Hermes providers/base.py).

A ProviderProfile is one declarative dataclass describing a vendor: which API shape it speaks,
its base URL, how it authenticates, and aliases. The LLMClient reads the profile instead of
carrying per-vendor boolean flags. New vendors = one register_provider() call, no core changes.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProviderProfile:
    name: str
    api_mode: str                      # "anthropic" | "openai"  (wire format)
    base_url: str | None = None        # None = vendor SDK default
    env_key: str | None = None         # env var holding the API key
    auth: str = "api_key"              # "api_key" | "none" (local servers)
    aliases: tuple[str, ...] = ()
    supports_vision: bool = True
    default_model: str | None = None


_REGISTRY: dict[str, ProviderProfile] = {}


def register_provider(profile: ProviderProfile) -> ProviderProfile:
    _REGISTRY[profile.name] = profile
    for a in profile.aliases:
        _REGISTRY[a] = profile
    return profile


def get_provider(name: str) -> ProviderProfile | None:
    return _REGISTRY.get(name)


def list_providers() -> list[str]:
    # unique by canonical name, sorted
    return sorted({p.name for p in _REGISTRY.values()})


# ── built-in profiles (declarative; the only place vendor specifics live) ──────────
register_provider(ProviderProfile("anthropic", "anthropic", env_key="ANTHROPIC_API_KEY",
                                   aliases=("claude",), default_model="claude-opus-4-8"))
register_provider(ProviderProfile("openai", "openai", env_key="OPENAI_API_KEY",
                                   aliases=("gpt",), default_model="gpt-4o"))
register_provider(ProviderProfile("openrouter", "openai",
                                   base_url="https://openrouter.ai/api/v1",
                                   env_key="OPENROUTER_API_KEY"))
register_provider(ProviderProfile("deepseek", "openai",
                                   base_url="https://api.deepseek.com/v1",
                                   env_key="DEEPSEEK_API_KEY", default_model="deepseek-chat"))
register_provider(ProviderProfile("nous", "openai",
                                   base_url="https://inference.nousresearch.com/v1",
                                   env_key="NOUS_API_KEY", aliases=("hermes",)))
register_provider(ProviderProfile("groq", "openai",
                                   base_url="https://api.groq.com/openai/v1",
                                   env_key="GROQ_API_KEY"))
register_provider(ProviderProfile("gemini", "openai",
                                   base_url="https://generativelanguage.googleapis.com/v1beta/openai",
                                   env_key="GEMINI_API_KEY", aliases=("google",)))
# local, keyless, OpenAI-compatible servers
register_provider(ProviderProfile("ollama", "openai", base_url="http://localhost:11434/v1",
                                   auth="none"))
register_provider(ProviderProfile("lmstudio", "openai", base_url="http://localhost:1234/v1",
                                   auth="none"))
