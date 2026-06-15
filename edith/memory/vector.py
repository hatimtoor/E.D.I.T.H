"""A dependency-free local embedder + cosine similarity.

Uses a deterministic hashing embedder (the "hashing trick") so the memory layer works
with zero external services or API keys. Swap in a real embedding model later by
implementing the same `embed(text) -> list[float]` contract.
"""
from __future__ import annotations

import hashlib
import math
import re

_TOKEN = re.compile(r"[a-z0-9]+")


def embed(text: str, dim: int = 256) -> list[float]:
    """Deterministic bag-of-words hashing embedding, L2-normalized."""
    vec = [0.0] * dim
    for tok in _TOKEN.findall(text.lower()):
        h = int.from_bytes(hashlib.blake2b(tok.encode(), digest_size=8).digest(), "little")
        idx = h % dim
        sign = 1.0 if (h >> 63) & 1 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))  # both already L2-normalized


def pack(vec: list[float]) -> bytes:
    import struct

    return struct.pack(f"<{len(vec)}f", *vec)


def unpack(blob: bytes) -> list[float]:
    import struct

    n = len(blob) // 4
    return list(struct.unpack(f"<{n}f", blob))
