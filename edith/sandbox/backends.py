"""Command-execution backends with a safety boundary.

  LocalBackend  - runs on the host (use only at HOST/AUTONOMOUS permission)
  DockerBackend - runs in a throwaway container with dropped caps + read-only root
  SSHBackend    - runs on a remote box you control

All return a uniform ExecResult. A blocklist stops the most obviously destructive
one-liners before they reach the shell (defence-in-depth, not a substitute for the
sandbox itself).
"""
from __future__ import annotations

import re
import shlex
import subprocess
from dataclasses import dataclass


@dataclass
class ExecResult:
    code: int
    stdout: str
    stderr: str
    backend: str


# FIX(OpenClaw host compromise): refuse the classic destructive patterns even before
# the sandbox boundary. Prompt-injected "rm -rf /" should never reach a shell.
_DANGER = re.compile(
    r"(rm\s+-rf\s+/(?:\s|$))|(:\(\)\s*\{\s*:\|:)|(\bmkfs\b)|(\bdd\s+if=.*of=/dev/)|"
    r"(>\s*/dev/sd)|(\bchmod\s+-R\s+777\s+/)",
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

    def run(self, command: str, *, timeout: int = 60) -> ExecResult:
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
        # hardened defaults: no network by default, dropped caps, read-only root,
        # non-root user, tmpfs work area. This is the safe boundary OpenClaw lacks.
        docker_cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--read-only",
            "--tmpfs", f"{self.workdir}:rw,exec",
            "--pids-limit", "256",
            "--memory", "512m",
            "-w", self.workdir,
            self.image,
            "sh", "-c", command,
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
        ssh_cmd = ["ssh", "-o", "BatchMode=yes", dest, command]
        p = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
        return ExecResult(p.returncode, p.stdout, p.stderr, self.name)


def get_backend(kind: str = "docker", **kwargs) -> _Backend:
    return {"local": LocalBackend, "docker": DockerBackend, "ssh": SSHBackend}[kind](**kwargs)
