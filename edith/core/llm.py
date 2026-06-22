"""Provider-agnostic LLM client.

Supports anthropic / openai / openrouter via a unified `chat()` interface. Heavy SDKs
are imported lazily so the package imports cleanly with no keys installed.
Model strings: "anthropic:claude-opus-4-8" or "openai:gpt-4o".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    name: str | None = None
    tool_call_id: str | None = None   # set on tool-result messages (multi-turn tool use)


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON schema


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    raw: Any = None


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, model: str, *, api_keys: dict[str, str | None] | None = None):
        if ":" in model:
            self.provider, self.model = model.split(":", 1)
        else:
            self.provider, self.model = "anthropic", model
        self.api_keys = api_keys or {}
        from edith.core.providers import get_provider
        self.profile = get_provider(self.provider)

    def _resolve_key(self) -> str | None:
        p = self.profile
        if p and p.auth == "none":
            return p.name  # local server ignores the value
        import os
        return (self.api_keys.get(self.provider)
                or (os.getenv(p.env_key) if p and p.env_key else None))

    def chat(self, messages: list[Message], *, tools: list[ToolSpec] | None = None,
             max_tokens: int = 4096, temperature: float = 0.7) -> LLMResponse:
        mode = self.profile.api_mode if self.profile else self.provider
        if mode == "anthropic":
            return self._anthropic(messages, tools, max_tokens, temperature)
        if mode == "openai":
            return self._openai(messages, tools, max_tokens, temperature)
        raise LLMError(f"unknown provider: {self.provider!r}")

    # ── anthropic ───────────────────────────────────────────────────
    def _anthropic(self, messages, tools, max_tokens, temperature) -> LLMResponse:
        key = self._resolve_key()
        if not key:
            raise LLMError("ANTHROPIC_API_KEY not set")
        try:
            import anthropic
        except ImportError as e:  # pragma: no cover
            raise LLMError("pip install 'edith[llm]' to use Anthropic") from e
        client = anthropic.Anthropic(api_key=key)

        system = "\n\n".join(m.content for m in messages if m.role == "system") or None
        convo: list[dict] = []
        for m in messages:
            if m.role in ("user", "assistant"):
                convo.append({"role": m.role, "content": m.content})
            elif m.role == "tool":
                # Anthropic has no standalone tool role; surface the result as a user turn.
                convo.append({"role": "user", "content": f"[tool result: {m.name}]\n{m.content}"})

        # sacred prompt caching: cache system + last-3 messages to reuse the prefix cache
        from edith.core.prompt_cache import prepare_anthropic_caching
        system_param, convo = prepare_anthropic_caching(system, convo)
        kwargs: dict[str, Any] = dict(model=self.model, max_tokens=max_tokens,
                                      temperature=temperature, messages=convo)
        if system_param:
            kwargs["system"] = system_param
        if tools:
            kwargs["tools"] = [{"name": t.name, "description": t.description,
                                "input_schema": t.parameters} for t in tools]
        resp = client.messages.create(**kwargs)
        text_parts, tool_calls = [], []
        for block in resp.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append({"name": block.name, "arguments": block.input, "id": block.id})
        return LLMResponse(text="".join(text_parts), tool_calls=tool_calls, raw=resp)

    # ── openai / openrouter ─────────────────────────────────────────
    def _openai(self, messages, tools, max_tokens, temperature) -> LLMResponse:
        # base_url + key come from the provider profile (declarative). Local servers
        # (auth="none") get a placeholder key. Validate BEFORE constructing the client.
        key = self._resolve_key()
        base_url = self.profile.base_url if self.profile else None
        if not key:
            raise LLMError(f"{self.provider.upper()}_API_KEY not set")
        try:
            import openai
        except ImportError as e:  # pragma: no cover
            raise LLMError("pip install 'edith[llm]' to use OpenAI/OpenRouter") from e
        client = openai.OpenAI(api_key=key, base_url=base_url)

        payload: list[dict] = []
        for m in messages:
            if m.role == "tool":
                payload.append({"role": "tool", "content": m.content,
                                "tool_call_id": m.tool_call_id or m.name or ""})
            else:
                payload.append({"role": m.role, "content": m.content})
        kwargs: dict[str, Any] = dict(model=self.model, max_tokens=max_tokens,
                                      temperature=temperature, messages=payload)
        if tools:
            kwargs["tools"] = [{"type": "function", "function": {
                "name": t.name, "description": t.description, "parameters": t.parameters,
            }} for t in tools]
        resp = client.chat.completions.create(**kwargs)
        choice = resp.choices[0].message
        tool_calls = []
        for tc in getattr(choice, "tool_calls", None) or []:
            import json
            tool_calls.append({"name": tc.function.name,
                               "arguments": json.loads(tc.function.arguments or "{}"),
                               "id": tc.id})
        return LLMResponse(text=choice.content or "", tool_calls=tool_calls, raw=resp)
