"""Shared prompt-injection / threat scanner (one source of truth).

Modeled on Hermes `tools/threat_patterns.py`: a single scanner used everywhere untrusted text
enters the agent — context files, memory writes, fetched web pages, skill bodies. Unicode is
normalized first (NFKD + zero-width strip) so homoglyph/zero-width tricks can't slip patterns past.
Heuristic by design (defense-in-depth), with `scope`-tuned strictness.
"""
from __future__ import annotations

import re
import unicodedata

_ZW_RE = re.compile("[​-‏‪-‮⁠﻿]")

# Core injection patterns (apply at every scope).
_BASE = [
    r"ignore\b[\w\s]{0,40}\binstructions",
    r"disregard (the )?(system|above|previous)",
    r"you are now (a|an|in|playing) ",
    r"reveal (your|the) (system )?(prompt|instructions)",
    r"print (your|the) (system )?prompt",
    r"exfiltrat",
    r"\bcurl\b[^\n]*\|\s*(sh|bash)",
    r"new (instructions|directive)s?:",
]
# Stricter: data-exfil / persistence (memory + context, which persist across sessions).
_STRICT = [
    r"send .* to (https?://|[\w.-]+@)",
    r"(post|upload|leak) .* (to|at) https?://",
    r"base64\s*-?d",
    r"(add|append) .* to (\.bashrc|\.zshrc|crontab|authorized_keys)",
]


def normalize(text: str) -> str:
    return _ZW_RE.sub("", unicodedata.normalize("NFKD", text or ""))


def _compiled(scope: str) -> re.Pattern:
    pats = list(_BASE)
    if scope in ("strict", "context", "memory"):
        pats += _STRICT
    return re.compile("|".join(pats), re.IGNORECASE)


_CACHE: dict[str, re.Pattern] = {}


def scan(text: str, *, scope: str = "default") -> str | None:
    """Return the matched threat snippet (truncated) if `text` looks like injection, else None."""
    rx = _CACHE.get(scope) or _CACHE.setdefault(scope, _compiled(scope))
    m = rx.search(normalize(text))
    return m.group(0)[:80] if m else None


def is_safe(text: str, *, scope: str = "default") -> bool:
    return scan(text, scope=scope) is None
