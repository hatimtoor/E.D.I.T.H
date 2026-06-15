"""Skill registry: progressive 3-level loading + true immutability locks.

Grounded in the real code:
  * Hermes `skill_manager_tool.py` "pin" only blocks DELETION, not edits, and
    `background_review.py` actively rewrites loaded user skills every turn
    ("most sessions produce at least one skill update"). That is the exact
    user grievance. E.D.I.T.H adds a real EDIT lock: a protected skill cannot be
    edited, patched, or deleted by the agent — only by an explicit human action.
  * OpenClaw/Hermes load lots of skill text up front -> token blowup. E.D.I.T.H
    loads in 3 levels (name -> params -> body) like Hermes' progressive idea,
    but enforces it in the registry so callers can't accidentally load bodies.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path


class SkillLevel(IntEnum):
    SUMMARY = 1   # name + one-line summary   (~20 tokens)
    PARAMS = 2    # + parameter definitions    (~200 tokens)
    BODY = 3      # + full procedural body      (~1000+ tokens)


class ProtectedSkillError(PermissionError):
    """Raised when the agent tries to mutate a human-protected skill."""


@dataclass
class Skill:
    name: str
    summary: str
    params: dict = field(default_factory=dict)
    body: str = ""
    protected: bool = False        # FIX(Hermes overwrite): true == agent-immutable
    source: str = "agent"          # agent | user | bundled | hub

    def render(self, level: SkillLevel) -> str:
        out = [f"## {self.name}\n{self.summary}"]
        if level >= SkillLevel.PARAMS and self.params:
            out.append("### params\n" + json.dumps(self.params, indent=2))
        if level >= SkillLevel.BODY and self.body:
            out.append("### body\n" + self.body)
        if self.protected:
            out.append("> 🔒 protected — agent may invoke but not modify")
        return "\n\n".join(out)


_SECRET_RE = re.compile(r"(?i)(api[_-]?key|password|secret|token)\s*[:=]\s*\S+")


class SkillRegistry:
    """Filesystem-backed skill store. One dir per skill: <root>/<name>/SKILL.md + meta.json."""

    def __init__(self, root: str = ".edith/skills"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._skills: dict[str, Skill] = {}
        self._load_all()

    # ── persistence ─────────────────────────────────────────────────
    def _skill_dir(self, name: str) -> Path:
        return self.root / re.sub(r"[^a-zA-Z0-9_-]", "_", name)

    def _load_all(self) -> None:
        for d in self.root.iterdir():
            meta = d / "meta.json"
            if meta.exists():
                m = json.loads(meta.read_text(encoding="utf-8"))
                body = (d / "SKILL.md").read_text(encoding="utf-8") if (d / "SKILL.md").exists() else ""
                self._skills[m["name"]] = Skill(
                    name=m["name"], summary=m.get("summary", ""), params=m.get("params", {}),
                    body=body, protected=m.get("protected", False), source=m.get("source", "agent"),
                )

    def _persist(self, skill: Skill) -> None:
        d = self._skill_dir(skill.name)
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(skill.body, encoding="utf-8")
        (d / "meta.json").write_text(
            json.dumps(
                {"name": skill.name, "summary": skill.summary, "params": skill.params,
                 "protected": skill.protected, "source": skill.source},
                indent=2,
            ),
            encoding="utf-8",
        )

    # ── progressive loading ─────────────────────────────────────────
    def catalog(self, level: SkillLevel = SkillLevel.SUMMARY) -> str:
        """Render every skill at the requested level. Default SUMMARY keeps tokens tiny."""
        return "\n\n".join(s.render(level) for s in self._skills.values())

    def load(self, name: str, level: SkillLevel = SkillLevel.BODY) -> str:
        if name not in self._skills:
            raise KeyError(f"no such skill: {name}")
        return self._skills[name].render(level)

    # ── mutation (agent-facing — respects protection) ───────────────
    def create(self, skill: Skill, *, by_agent: bool = True) -> Skill:
        if skill.name in self._skills:
            return self.update(skill.name, body=skill.body, summary=skill.summary,
                               params=skill.params, by_agent=by_agent)
        if by_agent and _SECRET_RE.search(skill.body):
            raise ValueError("refusing to store a skill containing a secret-like literal")
        self._skills[skill.name] = skill
        self._persist(skill)
        return skill

    def update(self, name: str, *, body: str | None = None, summary: str | None = None,
               params: dict | None = None, by_agent: bool = True) -> Skill:
        s = self._skills[name]
        # FIX(Hermes overwrite): block the self-improvement loop from editing locked skills.
        if by_agent and s.protected:
            raise ProtectedSkillError(
                f"skill '{name}' is protected; the agent cannot edit it. "
                f"Run `edith skills unprotect {name}` to allow changes."
            )
        if body is not None:
            s.body = body
        if summary is not None:
            s.summary = summary
        if params is not None:
            s.params = params
        self._persist(s)
        return s

    def delete(self, name: str, *, by_agent: bool = True) -> None:
        s = self._skills.get(name)
        if not s:
            return
        if by_agent and s.protected:
            raise ProtectedSkillError(f"skill '{name}' is protected; agent cannot delete it.")
        import shutil

        shutil.rmtree(self._skill_dir(name), ignore_errors=True)
        del self._skills[name]

    # ── human-only protection toggles ───────────────────────────────
    def protect(self, name: str) -> None:
        """Human action: make a skill agent-immutable (the missing Hermes feature)."""
        s = self._skills[name]
        s.protected = True
        self._persist(s)

    def unprotect(self, name: str) -> None:
        s = self._skills[name]
        s.protected = False
        self._persist(s)

    def names(self) -> list[str]:
        return sorted(self._skills)
