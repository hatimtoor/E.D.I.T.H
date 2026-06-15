"""Tool registration + offline-safe tool behaviour (no network/LLM/docker needed)."""
from edith.core.agent import Agent
from edith.core.config import Config, MemoryConfig


def _agent(tmp_path):
    cfg = Config(home=str(tmp_path / "home"),
                 memory=MemoryConfig(db_path=str(tmp_path / "m.sqlite"), embed_dim=128))
    return Agent(config=cfg)


def test_default_tools_registered(tmp_path):
    a = _agent(tmp_path)
    box = a.load_default_tools()
    expected = {"web_fetch", "web_search", "remember", "recall", "run_command",
                "security_scan", "save_skill", "list_skills", "read_file", "write_file"}
    assert expected <= set(a.tools)
    a.close()
    assert box is not None


def test_memory_tools_roundtrip(tmp_path):
    a = _agent(tmp_path)
    box = a.load_default_tools()
    assert box.remember("the api gateway runs on port 8080") == "stored"
    assert "8080" in box.recall("which port is the gateway")
    a.close()


def test_file_tools_are_workspace_scoped(tmp_path):
    a = _agent(tmp_path)
    box = a.load_default_tools()
    assert "wrote" in box.write_file("notes/todo.txt", "hello")
    assert box.read_file("notes/todo.txt") == "hello"
    # path traversal is refused
    assert "error" in box.read_file("../../etc/passwd")
    a.close()


def test_security_tool_refuses_without_scope(tmp_path):
    a = _agent(tmp_path)
    box = a.load_default_tools()
    assert "refused" in box.security_scan("8.8.8.8")
    a.close()
