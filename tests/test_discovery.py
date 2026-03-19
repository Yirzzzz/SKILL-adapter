from pathlib import Path

from skill_adapter.discovery import discover_skill_dirs, discover_skill_files


def test_discovery_finds_valid_skill_dirs() -> None:
    root = Path("./.tmp_test_cases_discovery_1/skills")
    (root / "a").mkdir(parents=True, exist_ok=True)
    (root / "a" / "SKILL.md").write_text("# A", encoding="utf-8")
    (root / "b").mkdir(parents=True, exist_ok=True)
    (root / "b" / "SKILL.md").write_text("# B", encoding="utf-8")

    discovered = discover_skill_dirs([str(root)])
    assert sorted([d.name for d in discovered]) == ["a", "b"]


def test_discovery_ignores_dirs_without_skill_md() -> None:
    root = Path("./.tmp_test_cases_discovery_2/skills")
    (root / "good").mkdir(parents=True, exist_ok=True)
    (root / "good" / "SKILL.md").write_text("# Good", encoding="utf-8")
    (root / "bad").mkdir(parents=True, exist_ok=True)

    discovered = discover_skill_dirs([str(root)])
    assert [d.name for d in discovered] == ["good"]


def test_discovery_supports_subdir_any_md_name() -> None:
    root = Path("./.tmp_test_cases_discovery_3/skills")
    (root / "math-skill").mkdir(parents=True, exist_ok=True)
    (root / "math-skill" / "anything.md").write_text("# Math", encoding="utf-8")
    (root / "README.md").write_text("# Ignore me", encoding="utf-8")

    files = discover_skill_files([str(root)])
    assert any(f.name == "anything.md" for f in files)
    assert all(f.name != "README.md" for f in files)
