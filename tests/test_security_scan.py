"""Active scan: scope-gated fingerprint/probe, OSV CVE audit (HTTP monkeypatched)."""
import edith.security.scan as scan
from edith.security.authorization import AuthorizationScope, OutOfScopeError


def _scope():
    return AuthorizationScope(engagement="lab", authorized_by="me@x.com", expires="2099-01-01",
                              targets=["127.0.0.1", "*.lab.local"])


def test_fingerprint_requires_scope():
    try:
        scan.http_fingerprint("8.8.8.8", _scope())
        assert False, "should refuse out-of-scope"
    except OutOfScopeError:
        pass


def test_fingerprint_reports_missing_headers(monkeypatch):
    monkeypatch.setattr(scan, "_fetch",
                        lambda url, **k: (200, {"server": "nginx"}, "<title>Home</title>"))
    r = scan.http_fingerprint("box.lab.local", _scope())
    assert r["server"] == "nginx" and r["title"] == "Home"
    assert "content-security-policy" in r["missing_security_headers"]


def test_probe_paths_finds_exposed(monkeypatch):
    def fake(url, **k):
        return (200, {}, "") if url.endswith("/.env") else (_ for _ in ()).throw(OSError())
    monkeypatch.setattr(scan, "_fetch", fake)
    found = scan.probe_paths("box.lab.local", _scope(), paths=["/.env", "/missing"])
    assert found == [{"path": "/.env", "status": 200}]


def test_cve_audit_no_scope_needed(monkeypatch):
    monkeypatch.setattr(scan, "_osv_query",
                        lambda payload, **k: {"vulns": [{"id": "GHSA-xxxx"}, {"id": "CVE-2026-1"}]})
    r = scan.cve_audit("requests", "2.0.0")
    assert r["vuln_count"] == 2 and "GHSA-xxxx" in r["ids"]
