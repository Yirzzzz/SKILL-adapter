from pathlib import Path

from skill_adapter.registry import SkillRegistry
from test_utils import make_case_dir


def test_registry_collects_build_errors_without_interrupting() -> None:
    skills_root = make_case_dir() / "skills"
    good_dir = skills_root / "good"
    bad_dir = skills_root / "bad"
    good_dir.mkdir(parents=True)
    bad_dir.mkdir(parents=True)

    (good_dir / "SKILL.md").write_text(
        "---\nname: Good Skill\ndescription: works\n---\n",
        encoding="utf-8",
    )
    (bad_dir / "SKILL.md").write_text("---\nname: broken\ndescription: [\n---\n", encoding="utf-8")

    registry = SkillRegistry.build([str(skills_root)])

    assert "good" in registry.skills
    assert len(registry.build_errors) == 1
    assert Path(registry.build_errors[0]["path"]).name == "SKILL.md"
