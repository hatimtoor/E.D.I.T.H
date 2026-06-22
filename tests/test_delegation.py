"""Multi-agent delegation: isolated children, blocked tools, summary-only, lineage."""
from edith.core.agent import Agent
from edith.core.config import Config, MemoryConfig
from edith.core.delegation import DELEGATE_BLOCKED_TOOLS, delegate
from edith.core.state import SessionDB


def _agent(tmp_path):
    cfg = Config(home=str(tmp_path / "home"),
                 memory=MemoryConfig(db_path=str(tmp_path / "home" / "m.sqlite"), embed_dim=128))
    a = Agent(config=cfg)
    a.load_default_tools()
    return a


def test_parent_has_delegate_tool_children_do_not(tmp_path, monkeypatch):
    a = _agent(tmp_path)
    assert "delegate_task" in a.tools
    # a child built by delegation must NOT keep blocked tools
    captured = {}

    def fake_step(self, goal, **kw):
        captured["tools"] = set(self.tools)
        return f"done: {goal}"
    monkeypatch.setattr(Agent, "step", fake_step)
    res = delegate(a, "investigate X")
    assert res[0].summary == "done: investigate X"
    assert DELEGATE_BLOCKED_TOOLS.isdisjoint(captured["tools"])   # children stripped
    a.close()


def test_child_session_lineage(tmp_path, monkeypatch):
    a = _agent(tmp_path)
    monkeypatch.setattr(Agent, "step", lambda self, goal, **kw: "ok")
    delegate(a, "task A")
    db = SessionDB(str(tmp_path / "home" / "state.sqlite"))
    subs = [s for s in db.list_sessions(include_archived=True) if s.source == "subagent"]
    assert subs and subs[0].parent_session_id == a.session.id
    db.close()
    a.close()


def test_parallel_delegation_returns_all(tmp_path, monkeypatch):
    a = _agent(tmp_path)
    monkeypatch.setattr(Agent, "step", lambda self, goal, **kw: f"summary[{goal}]")
    res = delegate(a, ["g1", "g2", "g3"])
    assert {r.goal for r in res} == {"g1", "g2", "g3"}
    assert all(r.ok for r in res)
    a.close()
