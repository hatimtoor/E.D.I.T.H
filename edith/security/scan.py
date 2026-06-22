"""Authorized active scanning — HTTP fingerprint, sensitive-path probe, dependency CVE audit.

Host-targeting functions pass through `assert_in_scope()` first (scope-gated). The CVE audit
queries OSV.dev about a *software package* (not an attack on a host), so it needs no scope.
Dependency-free (urllib); `_fetch`/`_osv_query` are module-level for easy test monkeypatching.
"""
from __future__ import annotations

import re
import urllib.request

from edith.security.authorization import AuthorizationScope, assert_in_scope

SECURITY_HEADERS = [
    "strict-transport-security", "content-security-policy", "x-frame-options",
    "x-content-type-options", "referrer-policy", "permissions-policy",
]
_SENSITIVE_PATHS = ["/.git/HEAD", "/.env", "/admin", "/server-status",
                    "/.well-known/security.txt", "/robots.txt", "/actuator/health"]
_UA = {"User-Agent": "E.D.I.T.H-recon"}


def _fetch(url: str, *, timeout: float = 5.0) -> tuple[int, dict, str]:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        headers = {k.lower(): v for k, v in r.headers.items()}
        body = r.read(4096).decode("utf-8", "replace")
        return getattr(r, "status", 200), headers, body


def _osv_query(payload: dict, *, timeout: float = 8.0) -> dict:
    import json
    req = urllib.request.Request("https://api.osv.dev/v1/query",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace") or "{}")


def http_fingerprint(target: str, scope: AuthorizationScope, *, scheme: str = "https") -> dict:
    assert_in_scope(target, scope, action="http-fingerprint")
    try:
        status, headers, body = _fetch(f"{scheme}://{target}/")
    except Exception as e:
        return {"error": str(e)}
    title = ""
    m = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
    if m:
        title = m.group(1).strip()[:120]
    return {"status": status, "server": headers.get("server"),
            "powered_by": headers.get("x-powered-by"), "title": title,
            "missing_security_headers": [h for h in SECURITY_HEADERS if h not in headers]}


def probe_paths(target: str, scope: AuthorizationScope, *, scheme: str = "https",
                paths: list[str] | None = None) -> list[dict]:
    assert_in_scope(target, scope, action="path-probe")
    found = []
    for p in (paths or _SENSITIVE_PATHS):
        try:
            status, _, _ = _fetch(f"{scheme}://{target}{p}", timeout=4)
            if status == 200:
                found.append({"path": p, "status": status})
        except Exception:
            pass
    return found


def cve_audit(package: str, version: str, *, ecosystem: str = "PyPI") -> dict:
    """Look up known vulnerabilities for a package@version via OSV.dev (no scope needed)."""
    try:
        data = _osv_query({"package": {"name": package, "ecosystem": ecosystem},
                           "version": version})
    except Exception as e:
        return {"error": str(e)}
    vulns = data.get("vulns", []) or []
    return {"package": package, "version": version, "vuln_count": len(vulns),
            "ids": [v.get("id") for v in vulns][:20]}
