"""Execution sandbox backends — fixes OpenClaw's host-compromise risk.
local / docker (hardened, default-safe) / ssh, with capability dropping and guards.
"""
from edith.sandbox.backends import LocalBackend, DockerBackend, SSHBackend, get_backend

__all__ = ["LocalBackend", "DockerBackend", "SSHBackend", "get_backend"]
