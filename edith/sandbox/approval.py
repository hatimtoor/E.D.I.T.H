"""Layered command-approval matrix (ported from Hermes tools/approval.py).

Ordered checks — order matters:
  1. HARD GUARDS (un-bypassable): credential/SSH/shell-rc/config edits, sudo-via-stdin,
     and the destructive-pattern blocklist. These deny even in yolo/autonomous mode.
  2. MODE: off/yolo (bypass non-hard), cron (config-driven, never interactive),
     manual/smart (require an approval callback decision).

`evaluate()` returns a Decision the sandbox acts on. This is the single chokepoint so every
backend gets the same policy.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from edith.core.config import PermissionLevel


class Verdict(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"          # caller must consult the approval callback


@dataclass
class Decision:
    verdict: Verdict
    reason: str = ""


# Destructive patterns (same defense-in-depth set as the sandbox guard).
_DESTRUCTIVE = re.compile(
    r"(rm\s+(-\w+\s+)*/(\*)?(\s|;|\||&|$))|(:\(\)\s*\{\s*:\s*\|\s*:)|(\bmkfs\b)|(\bshred\b)"
    r"|(\bwipefs\b)|(\bdd\b.*\bof=/dev/)|(>\s*/dev/sd)", re.IGNORECASE)

# Hard guards — sensitive targets that are gated regardless of mode.
_HARD_GUARDS = [
    (re.compile(r"\bsudo\b.*(-S|--stdin)|(echo|printf|cat)\b[^\n|]*\|\s*sudo\b", re.IGNORECASE),
     "sudo password via stdin"),
    (re.compile(r"(^|[\s;>])(~|\$HOME|/home/[^/\s]+|/root)/\.(bashrc|zshrc|profile|bash_profile)"
                r"|authorized_keys|/\.ssh/|id_rsa|id_ed25519", re.IGNORECASE),
     "credential / shell-rc / SSH key edit"),
    (re.compile(r"\.env\b|config\.ya?ml|credentials|secrets?\.(json|ya?ml|toml)", re.IGNORECASE),
     "secrets/config file edit"),
]


def _matches_write(command: str) -> bool:
    # crude write detection for hard-guard scoping (redirection, editors, sed -i, tee, install)
    return bool(re.search(r">>?|\b(tee|sed\s+-i|cp|mv|rm|install|chmod|chown)\b|cat\s*>", command))


def evaluate(command: str, *, permission_level: int = PermissionLevel.SANDBOXED,
             mode: str = "manual", has_callback: bool = False) -> Decision:
    """Decide what to do with `command`. mode ∈ off|yolo|cron|manual|smart."""
    # 1. HARD GUARDS — fire before any mode/yolo bypass
    if _DESTRUCTIVE.search(command):
        return Decision(Verdict.DENY, "destructive command pattern (hard guard)")
    for rx, why in _HARD_GUARDS:
        if rx.search(command) and (_matches_write(command) or "sudo" in why):
            return Decision(Verdict.DENY, f"hard guard: {why}")

    # 2. MODE
    if mode in ("off", "yolo") or permission_level >= PermissionLevel.AUTONOMOUS:
        return Decision(Verdict.ALLOW, "yolo/autonomous (hard guards still applied)")
    if mode == "cron":
        # non-interactive: only allow if explicitly permitted to act on host
        return (Decision(Verdict.ALLOW, "cron host-permitted")
                if permission_level >= PermissionLevel.HOST
                else Decision(Verdict.DENY, "cron: no host permission"))
    # manual / smart -> need a human/aux decision via callback
    if has_callback:
        return Decision(Verdict.ASK, "requires approval")
    # no callback available: safe default is deny for risky, allow for benign
    return Decision(Verdict.DENY, "no approval callback; denied by default")


def is_risky(command: str) -> bool:
    """Quick check: would this command need approval (not plainly benign)?"""
    if _DESTRUCTIVE.search(command):
        return True
    if any(rx.search(command) for rx, _ in _HARD_GUARDS):
        return True
    return bool(re.search(r"\b(sudo|rm|mkfs|dd|curl|wget|chmod|chown|kill|reboot|shutdown)\b",
                          command))
