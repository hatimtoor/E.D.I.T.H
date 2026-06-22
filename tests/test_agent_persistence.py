"""Agent wires SessionDB: messages persist and are searchable across agent instances."""
from edith.core.agent import Agent
from edith.core.config import Config, MemoryConfig
from edith.core.state import SessionDB


def _cfg(tmp_path):
    return Config(home=str(tmp_path / "home"),
                  memory=MemoryConfig(db_path=str(tmp_path / "home" / "memory.sqlite"),
                                      embed_dim=128))


def test_agent_creates_session_and_persists_user_message(tmp_path):
    cfg = _cfg(tmp_path)
    a = Agent(config=cfg)
    a.state.add_message(a.session.id, "user", "remember the launch code alpha-seven")
    sid = a.session.id
    a.close()
    # reopen the same on-disk state with a fresh DB handle
    d = SessionDB(str(tmp_path / "home" / "state.sqlite"))
    assert any(s.id == sid for s in d.list_sessions(include_archived=True))
    hits = d.search("launch code alpha")
    assert hits and "alpha-seven" in hits[0]["content"]
    d.close()
