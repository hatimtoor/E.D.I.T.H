"""Session state: sessions, messages, counts, FTS search, subagent lineage."""
from edith.core.state import SessionDB


def db(tmp_path):
    return SessionDB(str(tmp_path / "state.sqlite"))


def test_session_roundtrip_and_counts(tmp_path):
    d = db(tmp_path)
    s = d.create_session(source="cli", model="anthropic:claude-opus-4-8")
    d.add_message(s.id, "user", "what is the capital of France")
    d.add_message(s.id, "assistant", "Paris")
    d.add_message(s.id, "tool", "result", tool_name="web_search")
    got = d.get_session(s.id)
    assert got.message_count == 3 and got.tool_count == 1
    msgs = d.get_messages(s.id)
    assert [m["role"] for m in msgs] == ["user", "assistant", "tool"]
    d.close()


def test_usage_accumulates(tmp_path):
    d = db(tmp_path)
    s = d.create_session()
    d.record_usage(s.id, input_tokens=100, output_tokens=20, cost=0.01)
    d.record_usage(s.id, input_tokens=50, output_tokens=10, cost=0.005)
    g = d.get_session(s.id)
    assert g.input_tokens == 150 and g.output_tokens == 30 and round(g.cost, 4) == 0.015
    d.close()


def test_fts_search_finds_message(tmp_path):
    d = db(tmp_path)
    s = d.create_session()
    d.add_message(s.id, "user", "the deployment key is in the vault")
    d.add_message(s.id, "user", "lunch is at noon")
    hits = d.search("deployment vault")
    assert hits and "deployment key" in hits[0]["content"]
    d.close()


def test_subagent_lineage(tmp_path):
    d = db(tmp_path)
    parent = d.create_session(source="cli")
    child = d.create_session(source="subagent", parent_session_id=parent.id)
    assert d.get_session(child.id).parent_session_id == parent.id
    d.close()


def test_archive_hides_from_list(tmp_path):
    d = db(tmp_path)
    s = d.create_session()
    d.archive_session(s.id)
    assert all(x.id != s.id for x in d.list_sessions())
    assert any(x.id == s.id for x in d.list_sessions(include_archived=True))
    d.close()
