"""3-layer memory store backed by SQLite (FTS5 when available) + local vectors.

Layers: WORKING (current turn), EPISODIC (cross-session facts), PROCEDURAL (skills).
Fixes: profile namespacing (kills the "junk drawer"), cosine dedup on write,
prompt-injection scan (with unicode normalization to defeat homoglyph/zero-width bypass).
"""
from __future__ import annotations

import logging
import re
import sqlite3
import time
import unicodedata
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from edith.memory import vector

log = logging.getLogger("edith.memory")


class MemoryLayer(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"


@dataclass
class MemoryRecord:
    id: int
    profile: str
    layer: str
    key: str
    content: str
    score: float = 0.0


_INJECTION_PATTERNS = [
    r"ignore\b[\w\s]{0,40}\binstructions",
    r"disregard (the )?(system|above)",
    r"you are now (a|an|in) ",
    r"exfiltrat",
    r"send .* to (https?://|[\w.-]+@)",
    r"reveal (your|the) (system )?prompt",
    r"\bcurl\b.*\|\s*(sh|bash)",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)
_ZW_RE = re.compile("[​-‏‪-‮⁠﻿]")


def _normalize(text: str) -> str:
    """NFKD + strip zero-width chars so homoglyph/zero-width tricks can't dodge the scan."""
    return _ZW_RE.sub("", unicodedata.normalize("NFKD", text))


class InjectionBlocked(ValueError):
    pass


class MemoryStore:
    def __init__(self, db_path: str = ".edith/memory.sqlite", *, profile: str = "default",
                 dedup_threshold: float = 0.92, embed_dim: int = 256):
        self.profile = profile
        self.dedup_threshold = dedup_threshold
        self.embed_dim = embed_dim
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self._fts = self._init_schema()

    def _init_schema(self) -> bool:
        cur = self.db.cursor()
        cur.execute(
            """CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile TEXT NOT NULL, layer TEXT NOT NULL, key TEXT,
                content TEXT NOT NULL, vec BLOB, created REAL NOT NULL)"""
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_mem_scope ON memory(profile, layer)")
        fts_ok = True
        try:
            cur.execute("CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5("
                        "content, content='memory', content_rowid='id')")
            cur.executescript(
                """CREATE TRIGGER IF NOT EXISTS mem_ai AFTER INSERT ON memory BEGIN
                     INSERT INTO memory_fts(rowid, content) VALUES (new.id, new.content);
                   END;
                   CREATE TRIGGER IF NOT EXISTS mem_ad AFTER DELETE ON memory BEGIN
                     INSERT INTO memory_fts(memory_fts, rowid, content)
                       VALUES('delete', old.id, old.content);
                   END;"""
            )
        except sqlite3.OperationalError:
            fts_ok = False
        self.db.commit()
        return fts_ok

    def remember(self, content: str, *, layer: MemoryLayer = MemoryLayer.EPISODIC,
                 key: str | None = None, scan: bool = True) -> MemoryRecord | None:
        if scan and _INJECTION_RE.search(_normalize(content)):
            log.warning("memory write refused: injection pattern matched (profile=%s)", self.profile)
            raise InjectionBlocked("content matched an injection pattern; refused to persist")
        vec = vector.embed(content, self.embed_dim)
        for _row, score in self._scan_scope(layer, vec):
            if score >= self.dedup_threshold:
                return None  # near-duplicate, skip
        cur = self.db.cursor()
        cur.execute("INSERT INTO memory(profile, layer, key, content, vec, created) "
                    "VALUES (?,?,?,?,?,?)",
                    (self.profile, layer.value, key, content, vector.pack(vec), time.time()))
        self.db.commit()
        return MemoryRecord(cur.lastrowid, self.profile, layer.value, key or "", content, 1.0)

    def recall(self, query: str, *, layer: MemoryLayer | None = None, limit: int = 5,
               ) -> list[MemoryRecord]:
        qvec = vector.embed(query, self.embed_dim)
        scored: list[MemoryRecord] = []
        for row in self._candidates(query, layer):
            v = vector.unpack(row["vec"]) if row["vec"] else []
            score = vector.cosine(qvec, v) if v else 0.0
            scored.append(MemoryRecord(row["id"], row["profile"], row["layer"],
                                       row["key"] or "", row["content"], score))
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:limit]

    def _candidates(self, query: str, layer: MemoryLayer | None) -> list[sqlite3.Row]:
        cur = self.db.cursor()
        scope = "profile = ?"
        params: list = [self.profile]
        if layer:
            scope += " AND layer = ?"
            params.append(layer.value)
        if self._fts:
            try:
                fts_q = " OR ".join(re.findall(r"[A-Za-z0-9]+", query)) or query
                cur.execute(f"SELECT m.* FROM memory m JOIN memory_fts f ON m.id = f.rowid "
                            f"WHERE memory_fts MATCH ? AND {scope} LIMIT 200", [fts_q, *params])
                rows = cur.fetchall()
                if rows:
                    return rows
            except sqlite3.OperationalError:
                pass
        cur.execute(f"SELECT * FROM memory WHERE {scope} ORDER BY created DESC LIMIT 500", params)
        return cur.fetchall()

    def _scan_scope(self, layer: MemoryLayer, qvec: list[float]):
        cur = self.db.cursor()
        cur.execute("SELECT * FROM memory WHERE profile = ? AND layer = ? "
                    "ORDER BY created DESC LIMIT 500", (self.profile, layer.value))
        for row in cur.fetchall():
            v = vector.unpack(row["vec"]) if row["vec"] else []
            yield row, (vector.cosine(qvec, v) if v else 0.0)

    def clear_working(self) -> int:
        cur = self.db.cursor()
        cur.execute("DELETE FROM memory WHERE profile = ? AND layer = ?",
                    (self.profile, MemoryLayer.WORKING.value))
        self.db.commit()
        return cur.rowcount

    def count(self, layer: MemoryLayer | None = None) -> int:
        cur = self.db.cursor()
        if layer:
            cur.execute("SELECT COUNT(*) FROM memory WHERE profile=? AND layer=?",
                        (self.profile, layer.value))
        else:
            cur.execute("SELECT COUNT(*) FROM memory WHERE profile=?", (self.profile,))
        return cur.fetchone()[0]

    def close(self) -> None:
        self.db.close()
