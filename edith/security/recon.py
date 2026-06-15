"""Authorized reconnaissance helpers. Every function calls `assert_in_scope()` first;
with no scope file they all refuse. Stdlib-only so the package stays installable.
"""
from __future__ import annotations

import socket
import ssl
from dataclasses import dataclass, field

from edith.security.authorization import AuthorizationScope, assert_in_scope


@dataclass
class HostReport:
    target: str
    resolved_ip: str | None = None
    open_ports: list[int] = field(default_factory=list)
    tls_info: dict = field(default_factory=dict)
    banners: dict[int, str] = field(default_factory=dict)


_COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 3306, 3389, 5432, 6379, 8080, 8443]


def resolve(target: str, scope: AuthorizationScope) -> str | None:
    assert_in_scope(target, scope, action="resolve")
    try:
        return socket.gethostbyname(target)
    except OSError:
        return None


def scan_ports(target: str, scope: AuthorizationScope, *, ports: list[int] | None = None,
               timeout: float = 0.6) -> HostReport:
    """TCP connect scan of an authorized host (no raw packets)."""
    assert_in_scope(target, scope, action="port-scan")
    report = HostReport(target=target)
    report.resolved_ip = resolve(target, scope)
    ip = report.resolved_ip or target
    # DNS-rebinding defense: the resolved IP must ALSO be in scope.
    if ip != target:
        assert_in_scope(ip, scope, action="port-scan (resolved IP)")
    for port in ports or _COMMON_PORTS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            if s.connect_ex((ip, port)) == 0:
                report.open_ports.append(port)
                report.banners[port] = _grab_banner(ip, port, timeout)
    if 443 in report.open_ports:
        report.tls_info = inspect_tls(target, scope)
    return report


def _grab_banner(ip: str, port: int, timeout: float) -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((ip, port))
            if port in (80, 8080):
                s.sendall(b"HEAD / HTTP/1.0\r\n\r\n")
            return s.recv(256).decode("latin-1", "replace").strip()
    except OSError:
        return ""


def inspect_tls(target: str, scope: AuthorizationScope, *, port: int = 443) -> dict:
    assert_in_scope(target, scope, action="tls-inspect")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with socket.create_connection((target, port), timeout=2) as raw:
            with ctx.wrap_socket(raw, server_hostname=target) as tls:
                return {"protocol": tls.version(), "cipher": tls.cipher(),
                        "cert": tls.getpeercert(binary_form=False) or {}}
    except OSError as e:
        return {"error": str(e)}
