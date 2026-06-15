"""Authorization scope — the gate every offensive action must clear.

Scope file (config/authorization.yaml), NOT committed:

    engagement: "ACME pentest 2026-06"
    authorized_by: "jane@acme.example"
    expires: "2026-12-31"
    targets: ["10.0.0.0/24", "*.lab.acme.example", "192.168.1.50"]
    rules_of_engagement: ["no DoS", "business hours only"]
"""
from __future__ import annotations

import fnmatch
import ipaddress
import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

log = logging.getLogger("edith.security")


class OutOfScopeError(PermissionError):
    """Raised when an action targets a host outside the authorized scope."""


@dataclass
class AuthorizationScope:
    engagement: str = ""
    authorized_by: str = ""
    expires: str | None = None
    targets: list[str] = field(default_factory=list)
    rules_of_engagement: list[str] = field(default_factory=list)

    def is_active(self) -> bool:
        if not self.targets or not self.authorized_by:
            return False
        if self.expires:
            try:
                if date.fromisoformat(self.expires) < date.today():
                    return False
            except ValueError:
                return False
        return True

    def covers(self, target: str) -> bool:
        target = target.strip().lower()
        for entry in self.targets:
            entry = entry.strip().lower()
            if _ip_match(target, entry) or fnmatch.fnmatch(target, entry):
                return True
        return False


def _ip_match(target: str, entry: str) -> bool:
    try:
        if "/" in entry:
            return ipaddress.ip_address(target) in ipaddress.ip_network(entry, strict=False)
        return ipaddress.ip_address(target) == ipaddress.ip_address(entry)
    except ValueError:
        return False


def load_scope(path: str = "config/authorization.yaml") -> AuthorizationScope:
    p = Path(path)
    if not p.exists():
        return AuthorizationScope()
    import yaml
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return AuthorizationScope(
        engagement=data.get("engagement", ""), authorized_by=data.get("authorized_by", ""),
        expires=data.get("expires"), targets=list(data.get("targets", [])),
        rules_of_engagement=list(data.get("rules_of_engagement", [])))


def assert_in_scope(target: str, scope: AuthorizationScope, *, action: str = "scan") -> None:
    """Raise OutOfScopeError unless `target` is covered by an active scope.
    The single choke point — every recon/exploit helper calls it first.
    """
    if not scope.is_active():
        log.warning("offensive action '%s' refused: no active authorization scope", action)
        raise OutOfScopeError(
            "no active authorization scope. Create config/authorization.yaml with a signed "
            "engagement (targets + authorized_by [+ expires]) before any offensive action.")
    if not scope.covers(target):
        log.warning("offensive action '%s' refused: '%s' out of scope '%s'",
                    action, target, scope.engagement)
        raise OutOfScopeError(
            f"'{target}' is NOT in the authorized scope for '{scope.engagement}'. "
            f"Refusing to {action}. Authorized targets: {scope.targets}")
