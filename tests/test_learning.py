"""Closed-loop learning: heuristic memory capture, skill crystallize, trajectory export."""
import json
from pathlib import Path

from edith.core.learning import Learner
from edith.core.llm import Message
from edith.memory import MemoryStore, MemoryLayer
from edith.skills import Skill, SkillRegistry, ProtectedSkillError


def _learner(tmp_path):
    mem = MemoryStore(str(tmp_path / "m.sqlite"), embed_dim=128)
    sk = SkillRegistry(root=str(tmp_path / "skills"))
    return Learner(mem, sk, llm=None, trajectory_path=str(tmp_path / "traj.jsonl"))


def test_heuristic_captures_preference(tmp_path):
    learn = _learner(tmp_path)
    res = learn.review("I prefer concise answers with no fluff", "Understood.")
    assert res.memories_added >= 1
    hits = learn.memory.recall("preferences answers", layer=MemoryLayer.EPISODIC, limit=3)
    assert any("concise" in h.content for h in hits)


def test_no_false_memory_on_plain_text(tmp_path):
    learn = _learner(tmp_path)
    res = learn.review("what is the weather today", "It is sunny.")
    assert res.memories_added == 0


def test_trajectory_export_sharegpt(tmp_path):
    learn = _learner(tmp_path)
    learn.export_trajectory([Message("user", "hi"), Message("assistant", "hello")])
    line = Path(tmp_path / "traj.jsonl").read_text(encoding="utf-8").strip()
    rec = json.loads(line)
    assert rec["conversations"][0] == {"from": "human", "value": "hi"}
    assert rec["conversations"][1]["from"] == "gpt"


def test_review_skips_protected_skill(tmp_path):
    learn = _learner(tmp_path)
    learn.skills.create(Skill(name="deploy", summary="x", body="orig"))
    learn.skills.protect("deploy")
    # feed a plan that would overwrite "deploy" by forcing the skill dict via a tiny stub
    learn.llm = None
    learn._heuristic_plan = lambda u, r: {"memories": [], "skill":
                                          {"name": "deploy", "summary": "y", "body": "new"}}
    res = learn.review("x", "y")
    assert res.skill_saved is None
    assert "orig" in learn.skills.load("deploy")     # protected body unchanged
