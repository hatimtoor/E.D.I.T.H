"""Skills: progressive loading + the protection lock + secret scanning on update."""
import pytest

from edith.skills import Skill, SkillRegistry, SkillLevel, ProtectedSkillError


def reg(tmp_path):
    return SkillRegistry(root=str(tmp_path / "skills"))


def test_progressive_loading_levels(tmp_path):
    r = reg(tmp_path)
    r.create(Skill(name="deploy", summary="deploy the app",
                   params={"env": "string"}, body="long procedural body here"))
    assert "long procedural body" not in r.load("deploy", SkillLevel.SUMMARY)
    assert "env" in r.load("deploy", SkillLevel.PARAMS)
    assert "long procedural body" in r.load("deploy", SkillLevel.BODY)


def test_protected_skill_cannot_be_edited_by_agent(tmp_path):
    r = reg(tmp_path)
    r.create(Skill(name="prod-deploy", summary="careful!", body="original"))
    r.protect("prod-deploy")
    with pytest.raises(ProtectedSkillError):
        r.update("prod-deploy", body="agent rewrote this", by_agent=True)
    r.update("prod-deploy", body="human edit", by_agent=False)
    assert "human edit" in r.load("prod-deploy")


def test_protected_skill_cannot_be_deleted_by_agent(tmp_path):
    r = reg(tmp_path)
    r.create(Skill(name="keep", summary="s", body="b"))
    r.protect("keep")
    with pytest.raises(ProtectedSkillError):
        r.delete("keep", by_agent=True)


def test_secret_in_skill_is_refused_on_create_and_update(tmp_path):
    r = reg(tmp_path)
    with pytest.raises(ValueError):
        r.create(Skill(name="leak", summary="s", body="api_key=sk-supersecret123"))
    r.create(Skill(name="clean", summary="s", body="echo hi"))
    with pytest.raises(ValueError):
        r.update("clean", body="password = hunter2hunter2", by_agent=True)


def test_persistence_across_instances(tmp_path):
    r = reg(tmp_path)
    r.create(Skill(name="s1", summary="sum", body="body"))
    r.protect("s1")
    r2 = SkillRegistry(root=str(tmp_path / "skills"))
    assert "s1" in r2.names()
    assert r2._skills["s1"].protected
