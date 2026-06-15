"""Authorization scope — the gate every offensive action must clear.

Scope file (config/authorization.yaml), NOT committed:

    engagement: "ACME pentest 2026-06"
    authorized_by: "jane@acme.example"
    expires: "2026-12-31"
    targets:
      - "10.0.0.0/24"
      - "*.lab.acme.example"
      - "192.168.1.50"
    rules_of_engagement:
      - "no DoS"
      - "business hours only"
"""
from __future__ import annotations

import fnmatch
import ipaddress
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


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
        """True if `target` (ip or hostname) falls within an authorized entry."""
        target = target.strip().lower()
        # try IP / CIDR matching first
        for entry in self.targets:
            entry = entry.strip().lower()
            if _ip_match(target, entry):
                return True
            if fnmatch.fnmatch(target, entry):  # hostname globs like *.lab.example
                return True
        return False


def _ip_match(target: str, entry: str) -> bool:
    try:
        if "/" in entry:
            net = ipaddress.ip_network(entry, strict=False)
            return ipaddress.ip_address(target) in net
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
        engagement=data.get("engagement", ""),
        authorized_by=data.get("authorized_by", ""),
        expires=data.get("expires"),
        targets=list(data.get("targets", [])),
        rules_of_engagement=list(data.get("rules_of_engagement", [])),
    )


def assert_in_scope(target: str, scope: AuthorizationScope, *, action: str = "scan") -> None:
    """Raise OutOfScopeError unless `target` is covered by an active scope.

    This is the single choke point. Every recon/exploit helper calls it first.
    """
    if not scope.is_active():
        raise OutOfScopeError(
            "no active authorization scope. Create config/authorization.yaml with a signed "
            "engagement (targets + authorized_by [+ expires]) before running any offensive action."
        )
    if not scope.covers(target):
        raise OutOfScopeError(
            f"'{target}' is NOT in the authorized scope for engagement "
            f"'{scope.engagement}'. Refusing to {action}. Authorized targets: {scope.targets}"
        )
