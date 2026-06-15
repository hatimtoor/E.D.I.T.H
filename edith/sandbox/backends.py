"""Command-execution backends with a safety boundary.

  LocalBackend  - host execution; requires HOST/AUTONOMOUS permission level
  DockerBackend - throwaway container: dropped caps, no-new-privs, read-only, no network,
                  non-root user, pids/mem limits
  SSHBackend    - remote box you control; command is shell-quoted

A destructive-pattern blocklist is defense-in-depth, NOT the primary control (the
sandbox boundary is). The Docker backend is the safe default.
"""
from __future__ import annotations

import re
import shlex
import subprocess
from dataclasses import dataclass

from edith.core.config import PermissionLevel


@dataclass
class ExecResult:
    code: int
    stdout: str
    stderr: str
    backend: str


# Expanded patterns (still heuristic; the sandbox is the real boundary).
_DANGER = re.compile(
    r"(rm\s+(-\w+\s+)*/(\*)?(\s|;|\||&|$))"        # rm ... / (any flags / glob)
    r"|(:\(\)\s*\{\s*:\s*\|\s*:)"                  # fork bomb
    r"|(\bmkfs\b)|(\bshred\b)|(\bwipefs\b)"
    r"|(\bdd\b.*\bof=/dev/)"
    r"|(>\s*/dev/sd)"
    r"|(>\s*/etc/(passwd|shadow|sudoers))"
    r"|(\bchmod\s+(-\w+\s+)*777\s+/)",
    re.IGNORECASE,
)


class _Backend:
    name = "base"

    def _guard(self, command: str) -> None:
        if _DANGER.search(command):
            raise PermissionError(f"refused destructive command pattern: {command!r}")

    def run(self, command: str, *, timeout: int = 60) -> ExecResult:  # pragma: no cover
        raise NotImplementedError


class LocalBackend(_Backend):
    name = "local"

    def __init__(self, permission_level: int = PermissionLevel.READ_ONLY):
        self._perm = permission_level

    def run(self, command: str, *, timeout: int = 60) -> ExecResult:
        if self._perm < PermissionLevel.HOST:
            raise PermissionError(
                "LocalBackend requires HOST or AUTONOMOUS permission level; "
                "use DockerBackend for sandboxed execution.")
        self._guard(command)
        p = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        return ExecResult(p.returncode, p.stdout, p.stderr, self.name)


class DockerBackend(_Backend):
    name = "docker"

    def __init__(self, image: str = "python:3.12-slim", workdir: str = "/work"):
        self.image = image
        self.workdir = workdir

    def run(self, command: str, *, timeout: int = 120) -> ExecResult:
        self._guard(command)
        docker_cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--read-only",
            "--user", "65534:65534",                  # nobody:nogroup, not root
            "--tmpfs", f"{self.workdir}:rw,exec,uid=65534,gid=65534",
            "--pids-limit", "256",
            "--memory", "512m",
            "-w", self.workdir,
            self.image, "sh", "-c", command,
        ]
        try:
            p = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=timeout)
            return ExecResult(p.returncode, p.stdout, p.stderr, self.name)
        except FileNotFoundError:
            return ExecResult(127, "", "docker not installed", self.name)


class SSHBackend(_Backend):
    name = "ssh"

    def __init__(self, host: str, user: str | None = None):
        self.host = host
        self.user = user

    def run(self, command: str, *, timeout: int = 60) -> ExecResult:
        self._guard(command)
        dest = f"{self.user}@{self.host}" if self.user else self.host
        # shell-quote the remote command; `--` stops flag parsing on the destination.
        ssh_cmd = ["ssh", "-o", "BatchMode=yes", "--", dest, f"sh -c {shlex.quote(command)}"]
        p = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
        return ExecResult(p.returncode, p.stdout, p.stderr, self.name)


def get_backend(kind: str = "docker", **kwargs) -> _Backend:
    return {"local": LocalBackend, "docker": DockerBackend, "ssh": SSHBackend}[kind](**kwargs)
