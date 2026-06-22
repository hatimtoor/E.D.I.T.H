"""Closed-loop learning — the self-improvement headline (ported from Hermes background_review).

After a turn, E.D.I.T.H reflects on the exchange and crystallizes durable learnings into memory
and skills — WITHOUT touching the live conversation or its prompt cache. Two safety rules from
the research:
  1. Review runs in a restricted context whitelisted to memory+skills only.
  2. It never deletes; it only adds/updates, and protected skills are immutable.

Trajectories (the turn transcript) are exported as ShareGPT JSONL for later fine-tuning.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from edith.core.llm import LLMClient, LLMError, Message
from edith.memory import MemoryLayer, MemoryStore
from edith.skills import ProtectedSkillError, Skill, SkillRegistry

_REVIEW_WHITELIST = {"remember", "save_skill"}   # the only effects a review may have

_REVIEW_PROMPT = """You are E.D.I.T.H's background reviewer. Look at the exchange below and decide \
what (if anything) is worth remembering for next time. Be conservative but useful.

Reply with STRICT JSON only:
{"memories": ["durable fact ..."], "skill": {"name": "...", "summary": "...", "body": "..."}|null}

- "memories": stable user preferences, environment facts, corrections. [] if nothing.
- "skill": a reusable procedure ONLY if the exchange taught a repeatable workflow, else null.

EXCHANGE:
"""


@dataclass
class LearningResult:
    memories_added: int = 0
    skill_saved: str | None = None
    errors: list[str] = field(default_factory=list)


@dataclass
class Learner:
    memory: MemoryStore
    skills: SkillRegistry
    llm: LLMClient | None = None              # None -> heuristic-only (no LLM needed)
    trajectory_path: str = ".edith/trajectories.jsonl"

    # ── trajectory export (always cheap, no LLM) ────────────────────
    def export_trajectory(self, turns: list[Message], *, completed: bool = True) -> None:
        """Append the turn transcript in ShareGPT format for later fine-tuning."""
        role_map = {"system": "system", "user": "human", "assistant": "gpt", "tool": "tool"}
        convo = [{"from": role_map.get(m.role, m.role), "value": m.content} for m in turns if m.content]
        rec = {"conversations": convo, "completed": completed, "ts": time.time()}
        p = Path(self.trajectory_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ── reflection ──────────────────────────────────────────────────
    def review(self, user_input: str, reply: str) -> LearningResult:
        """Reflect on one exchange and crystallize learnings (LLM if available, else heuristic)."""
        res = LearningResult()
        plan = self._llm_plan(user_input, reply) if self.llm else self._heuristic_plan(user_input, reply)
        for fact in plan.get("memories", []) or []:
            if not isinstance(fact, str) or not fact.strip():
                continue
            try:
                if self.memory.remember(fact, layer=MemoryLayer.EPISODIC) is not None:
                    res.memories_added += 1
            except Exception as e:
                res.errors.append(f"memory: {type(e).__name__}")
        sk = plan.get("skill")
        if isinstance(sk, dict) and sk.get("name") and sk.get("body"):
            try:
                self.skills.create(Skill(name=sk["name"], summary=sk.get("summary", ""),
                                         body=sk["body"], source="learned"))
                res.skill_saved = sk["name"]
            except ProtectedSkillError:
                res.errors.append("skill: protected (not overwritten)")
            except Exception as e:
                res.errors.append(f"skill: {type(e).__name__}")
        return res

    def _llm_plan(self, user_input: str, reply: str) -> dict:
        try:
            r = self.llm.chat([Message("user", _REVIEW_PROMPT + f"USER: {user_input}\nEDITH: {reply}")],
                              max_tokens=600, temperature=0)
            m = re.search(r"\{.*\}", r.text, re.DOTALL)
            return json.loads(m.group(0)) if m else {}
        except (LLMError, json.JSONDecodeError, Exception):
            return self._heuristic_plan(user_input, reply)

    def _heuristic_plan(self, user_input: str, reply: str) -> dict:
        """No-LLM fallback: capture explicit user preferences ("I prefer/always/never ...")."""
        memories = []
        for m in re.finditer(r"(?i)\b(i (?:prefer|always|never|like|want|use|am)\b[^.?!\n]{3,120})",
                             user_input):
            memories.append(m.group(1).strip())
        return {"memories": memories[:3], "skill": None}
