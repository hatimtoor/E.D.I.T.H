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
# ── broad ecosystem (all OpenAI-compatible; base_url/key env-overridable) ──────────
# Any provider's base URL or key can be overridden via EDITH_<NAME>_BASE_URL /
# EDITH_<NAME>_API_KEY, so unlisted or self-hosted OpenAI-compatible endpoints work too.
def _oa(name, base, env_key, **kw):
    register_provider(ProviderProfile(name, "openai", base_url=base, env_key=env_key, **kw))


_oa("nvidia", "https://integrate.api.nvidia.com/v1", "NVIDIA_API_KEY")          # free NIM models
_oa("opencode", "https://opencode.ai/zen/v1", "OPENCODE_API_KEY", aliases=("opencode-zen", "zen"))
_oa("mistral", "https://api.mistral.ai/v1", "MISTRAL_API_KEY")
_oa("together", "https://api.together.xyz/v1", "TOGETHER_API_KEY")
_oa("fireworks", "https://api.fireworks.ai/inference/v1", "FIREWORKS_API_KEY")
_oa("deepinfra", "https://api.deepinfra.com/v1/openai", "DEEPINFRA_API_KEY")
_oa("cerebras", "https://api.cerebras.ai/v1", "CEREBRAS_API_KEY")
_oa("perplexity", "https://api.perplexity.ai", "PERPLEXITY_API_KEY", aliases=("pplx",))
_oa("xai", "https://api.x.ai/v1", "XAI_API_KEY", aliases=("grok",))
_oa("moonshot", "https://api.moonshot.ai/v1", "MOONSHOT_API_KEY", aliases=("kimi",))
_oa("novita", "https://api.novita.ai/v3/openai", "NOVITA_API_KEY")
_oa("hyperbolic", "https://api.hyperbolic.xyz/v1", "HYPERBOLIC_API_KEY")
_oa("sambanova", "https://api.sambanova.ai/v1", "SAMBANOVA_API_KEY")
_oa("huggingface", "https://router.huggingface.co/v1", "HF_TOKEN", aliases=("hf",))
_oa("qwen", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1", "DASHSCOPE_API_KEY",
    aliases=("dashscope", "alibaba"))
_oa("zai", "https://api.z.ai/api/paas/v4", "ZAI_API_KEY", aliases=("zhipu", "glm"))
_oa("minimax", "https://api.minimaxi.chat/v1", "MINIMAX_API_KEY")
_oa("stepfun", "https://api.stepfun.com/v1", "STEPFUN_API_KEY")
_oa("venice", "https://api.venice.ai/api/v1", "VENICE_API_KEY")
_oa("chutes", "https://llm.chutes.ai/v1", "CHUTES_API_KEY")
_oa("ollama-cloud", "https://ollama.com/v1", "OLLAMA_API_KEY")
# generic escape hatch: point at ANY OpenAI-compatible endpoint via env
_oa("custom", None, "EDITH_CUSTOM_API_KEY", aliases=("openai-compatible",))

# local, keyless, OpenAI-compatible servers
register_provider(ProviderProfile("ollama", "openai", base_url="http://localhost:11434/v1",
                                   auth="none"))
register_provider(ProviderProfile("lmstudio", "openai", base_url="http://localhost:1234/v1",
                                   auth="none"))
register_provider(ProviderProfile("vllm", "openai", base_url="http://localhost:8000/v1",
                                   auth="none"))
register_provider(ProviderProfile("llamacpp", "openai", base_url="http://localhost:8080/v1",
                                   auth="none", aliases=("llama-cpp",)))
