"""Tool-call repair — recover tool calls that models emit as TEXT instead of the
structured `tool_calls` field (ported concept from Hermes/OpenClaw tool-call-repair).

Some OpenRouter models (e.g. owl-alpha/LongCat, some Qwen/Hermes variants) return their
tool call inside the message content using a model-specific syntax. We detect the common
formats and convert them into our standard call dicts so the agent can dispatch them.
"""
from __future__ import annotations

import json
import re

_LONGCAT = re.compile(r"<longcat_tool_call>\s*([\w.\-]+)(.*?)</longcat_tool_call>", re.DOTALL)
_LONGCAT_ARG = re.compile(
    r"<longcat_arg_key>(.*?)</longcat_arg_key>\s*<longcat_arg_value>(.*?)</longcat_arg_value>",
    re.DOTALL)
_TOOLCALL_JSON = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)
_FENCED_JSON = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _coerce_args(obj: dict) -> dict:
    return obj.get("arguments") or obj.get("parameters") or obj.get("args") or {}


def parse_text_tool_calls(text: str) -> list[dict]:
    """Extract tool calls embedded in message text. Returns standard call dicts or []."""
    if not text:
        return []
    calls: list[dict] = []

    # 1. LongCat / owl-alpha key/value XML
    for m in _LONGCAT.finditer(text):
        name = m.group(1).strip()
        args = {k.strip(): v.strip() for k, v in _LONGCAT_ARG.findall(m.group(2))}
        calls.append({"name": name, "arguments": args, "id": f"rep{len(calls)}"})
    if calls:
        return calls

    # 2. <tool_call>{json}</tool_call> (Hermes / Qwen / Nous style)
    for m in _TOOLCALL_JSON.finditer(text):
        try:
            obj = json.loads(m.group(1))
            if obj.get("name"):
                calls.append({"name": obj["name"], "arguments": _coerce_args(obj),
                              "id": f"rep{len(calls)}"})
        except json.JSONDecodeError:
            pass
    if calls:
        return calls

    # 3. fenced ```json {"name":..,"arguments":..} ``` or {"tool_call": {...}}
    for m in _FENCED_JSON.finditer(text):
        try:
            obj = json.loads(m.group(1))
            obj = obj.get("tool_call", obj)
            if isinstance(obj, dict) and obj.get("name"):
                calls.append({"name": obj["name"], "arguments": _coerce_args(obj),
                              "id": f"rep{len(calls)}"})
        except json.JSONDecodeError:
            pass
    return calls


def strip_tool_call_text(text: str) -> str:
    """Remove tool-call syntax from text so the leftover prose stays clean."""
    for rx in (_LONGCAT, _TOOLCALL_JSON, _FENCED_JSON):
        text = rx.sub("", text)
    return text.strip()
