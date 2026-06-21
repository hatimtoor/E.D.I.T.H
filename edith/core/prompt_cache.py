"""Sacred prompt caching — ported pattern from Hermes `agent/prompt_caching.py`.

Marks the system prompt + the last 3 non-system messages with Anthropic `cache_control`
(4 breakpoints max, single TTL). Keeping the prefix byte-stable lets the provider reuse the
cache across turns — a large token-cost + latency saving. Pure functions; never mutate input.
"""
from __future__ import annotations

from typing import Any

MAX_BREAKPOINTS = 4


def _marker(cache_ttl: str) -> dict:
    return {"type": "ephemeral"} if cache_ttl == "5m" else {"type": "ephemeral", "ttl": cache_ttl}


def _mark_content(content: Any, marker: dict) -> Any:
    """Return content with cache_control on its last text block (string -> wrapped list)."""
    if content is None or content == "":
        return content
    if isinstance(content, str):
        return [{"type": "text", "text": content, "cache_control": marker}]
    if isinstance(content, list) and content:
        out = list(content)
        if isinstance(out[-1], dict):
            out[-1] = {**out[-1], "cache_control": marker}
        return out
    return content


def prepare_anthropic_caching(system: str | None, convo: list[dict], *, cache_ttl: str = "5m"
                              ) -> tuple[list[dict] | None, list[dict]]:
    """Given a system string + user/assistant messages, return (system_blocks, convo) with
    cache_control applied to the system prompt and the last (4 - used) non-system messages.
    """
    marker = _marker(cache_ttl)
    used = 0
    system_param: list[dict] | None = None
    if system:
        system_param = [{"type": "text", "text": system, "cache_control": marker}]
        used += 1
    remaining = MAX_BREAKPOINTS - used
    new_convo = [dict(m) for m in convo]
    if remaining > 0:
        for m in new_convo[-remaining:]:
            m["content"] = _mark_content(m.get("content"), marker)
    return system_param, new_convo
