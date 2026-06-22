"""Persistent session + message state (SQLite, WAL, FTS5).

Backbone for history, cross-session search, subagent lineage, and the gateway. Modeled on
Hermes' `hermes_state.py`: `sessions` (self-FK parent_session_id for subagent lineage + token/
cost columns) and `messages`, with an FTS5 mirror and a WAL→DELETE fallback for network mounts.
"""
from __future__ import annotations

import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Session:
    id: str
    source: str = "cli"          # cli | gateway:<platform> | subagent | cron
    user_id: str | None = None
    model: str = ""
    parent_session_id: str | None = None
    title: str = ""
    created: float = field(default_factory=time.time)
    updated: float = field(default_factory=time.time)
    message_count: int = 0
    tool_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    archived: int = 0


class SessionDB:
    def __init__(self, db_path: str = ".edith/state.sqlite"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self._set_wal()
        self._fts = self._init_schema()

    def _set_wal(self) -> None:
        try:
            self.db.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError:
            # network mounts (NFS/SMB/FUSE) reject WAL — fall back safely
            self.db.execute("PRAGMA journal_mode=DELETE")

    def _init_schema(self) -> bool:
        cur = self.db.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, source TEXT NOT NULL, user_id TEXT, model TEXT,
                parent_session_id TEXT REFERENCES sessions(id), title TEXT,
                created REAL NOT NULL, updated REAL NOT NULL,
                message_count INTEGER DEFAULT 0, tool_count INTEGER DEFAULT 0,
                input_tokens INTEGER DEFAULT 0, output_tokens INTEGER DEFAULT 0,
                cost REAL DEFAULT 0, archived INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id),
                role TEXT NOT NULL, content TEXT, tool_name TEXT, tool_call_id TEXT,
                created REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_msg_session ON messages(session_id, created);
            CREATE INDEX IF NOT EXISTS idx_sess_parent ON sessions(parent_session_id);
            """
        )
        fts_ok = True
        try:
            cur.execute("CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5("
                        "content, content='messages', content_rowid='id')")
            cur.executescript(
                """CREATE TRIGGER IF NOT EXISTS msg_ai AFTER INSERT ON messages BEGIN
                     INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
                   END;
                   CREATE TRIGGER IF NOT EXISTS msg_ad AFTER DELETE ON messages BEGIN
                     INSERT INTO messages_fts(messages_fts, rowid, content)
                       VALUES('delete', old.id, old.content);
                   END;"""
            )
        except sqlite3.OperationalError:
            fts_ok = False
        self.db.commit()
        return fts_ok

    # ── sessions ────────────────────────────────────────────────────
    def create_session(self, *, source: str = "cli", model: str = "", user_id: str | None = None,
                        parent_session_id: str | None = None, title: str = "") -> Session:
        s = Session(id=uuid.uuid4().hex[:16], source=source, model=model, user_id=user_id,
                    parent_session_id=parent_session_id, title=title)
        self.db.execute(
            "INSERT INTO sessions(id,source,user_id,model,parent_session_id,title,created,updated)"
            " VALUES(?,?,?,?,?,?,?,?)",
            (s.id, s.source, s.user_id, s.model, s.parent_session_id, s.title, s.created, s.updated))
        self.db.commit()
        return s

    def get_session(self, session_id: str) -> Session | None:
        r = self.db.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        return Session(**{k: r[k] for k in r.keys()}) if r else None

    def list_sessions(self, *, limit: int = 50, include_archived: bool = False) -> list[Session]:
        q = "SELECT * FROM sessions"
        if not include_archived:
            q += " WHERE archived=0"
        q += " ORDER BY updated DESC LIMIT ?"
        return [Session(**{k: r[k] for k in r.keys()})
                for r in self.db.execute(q, (limit,)).fetchall()]

    def archive_session(self, session_id: str) -> None:
        self.db.execute("UPDATE sessions SET archived=1, updated=? WHERE id=?",
                        (time.time(), session_id))
        self.db.commit()

    # ── messages ────────────────────────────────────────────────────
    def add_message(self, session_id: str, role: str, content: str, *,
                    tool_name: str | None = None, tool_call_id: str | None = None) -> int:
        now = time.time()
        cur = self.db.execute(
            "INSERT INTO messages(session_id,role,content,tool_name,tool_call_id,created)"
            " VALUES(?,?,?,?,?,?)", (session_id, role, content, tool_name, tool_call_id, now))
        self.db.execute(
            "UPDATE sessions SET message_count=message_count+1,"
            " tool_count=tool_count+?, updated=? WHERE id=?",
            (1 if role == "tool" else 0, now, session_id))
        self.db.commit()
        return cur.lastrowid

    def get_messages(self, session_id: str, *, limit: int = 1000) -> list[dict]:
        rows = self.db.execute(
            "SELECT role,content,tool_name,tool_call_id,created FROM messages"
            " WHERE session_id=? ORDER BY created LIMIT ?", (session_id, limit)).fetchall()
        return [dict(r) for r in rows]

    def record_usage(self, session_id: str, *, input_tokens: int = 0, output_tokens: int = 0,
                     cost: float = 0.0) -> None:
        self.db.execute(
            "UPDATE sessions SET input_tokens=input_tokens+?, output_tokens=output_tokens+?,"
            " cost=cost+?, updated=? WHERE id=?",
            (input_tokens, output_tokens, cost, time.time(), session_id))
        self.db.commit()

    # ── search ──────────────────────────────────────────────────────
    def search(self, query: str, *, limit: int = 20) -> list[dict]:
        """Full-text search across all messages (FTS5, with LIKE fallback)."""
        import re
        if self._fts:
            try:
                fts_q = " OR ".join(re.findall(r"[A-Za-z0-9]+", query)) or query
                rows = self.db.execute(
                    "SELECT m.session_id, m.role, m.content, m.created FROM messages m "
                    "JOIN messages_fts f ON m.id=f.rowid WHERE messages_fts MATCH ? "
                    "ORDER BY m.created DESC LIMIT ?", (fts_q, limit)).fetchall()
                return [dict(r) for r in rows]
            except sqlite3.OperationalError:
                pass
        rows = self.db.execute(
            "SELECT session_id, role, content, created FROM messages "
            "WHERE content LIKE ? ORDER BY created DESC LIMIT ?",
            (f"%{query}%", limit)).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self.db.close()
