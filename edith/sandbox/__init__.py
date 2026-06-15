"""Execution sandbox backends — fixes OpenClaw's host-compromise risk.

Backends mirror Hermes' hot-swappable idea (local / docker / ssh) but default to the
*safe* one (docker) on servers, with capability dropping and read-only roots.
"""
from edith.sandbox.backends import LocalBackend, DockerBackend, SSHBackend, get_backend

__all__ = ["LocalBackend", "DockerBackend", "SSHBackend", "get_backend"]
