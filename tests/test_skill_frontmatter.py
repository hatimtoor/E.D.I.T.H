"""agentskills.io SKILL.md frontmatter: portable persist + import of external packs."""
from pathlib import Path

from edith.skills import Skill, SkillRegistry


def test_persisted_skill_md_has_frontmatter(tmp_path):
    r = SkillRegistry(root=str(tmp_path / "skills"))
    r.create(Skill(name="deploy", summary="deploy the app", body="run make deploy"))
    md = next((tmp_path / "skills").glob("*/SKILL.md")).read_text(encoding="utf-8")
    assert md.startswith("---")
    assert "name: deploy" in md and "description: deploy the app" in md
    assert "run make deploy" in md.split("---", 2)[-1]   # body after frontmatter


def test_import_external_pack(tmp_path):
    pack = tmp_path / "ext"
    pack.mkdir()
    (pack / "SKILL.md").write_text(
        "---\nname: osint-recon\ndescription: do passive recon\n---\n\n## Steps\n1. enumerate\n",
        encoding="utf-8")
    r = SkillRegistry(root=str(tmp_path / "skills"))
    s = r.import_skill(str(pack))
    assert s.name == "osint-recon" and s.summary == "do passive recon"
    assert "enumerate" in r.load("osint-recon")


def test_roundtrip_via_frontmatter_only(tmp_path):
    # persist, delete the sidecar, reload from SKILL.md frontmatter alone
    root = tmp_path / "skills"
    r = SkillRegistry(root=str(root))
    r.create(Skill(name="note", summary="a note skill", body="hello body"))
    for meta in root.glob("*/meta.json"):
        meta.unlink()
    r2 = SkillRegistry(root=str(root))
    assert "note" in r2.names()
    assert r2._skills["note"].summary == "a note skill"
    assert "hello body" in r2.load("note")
