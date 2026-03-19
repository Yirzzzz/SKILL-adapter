from pathlib import Path

from skill_adapter import SkillRuntime
from skill_adapter.config import SkillConfig
from test_utils import make_case_dir


def _write_skill(root: Path, name: str, content: str) -> None:
    d = root / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(content, encoding="utf-8")


def test_route_fallback_on_low_score() -> None:
    skills_root = make_case_dir() / "skills"
    _write_skill(
        skills_root,
        "paper-summary",
        "# Paper Summary\nSummarize papers\n## Use When\n- summarize paper",
    )

    config = SkillConfig(
        skill_dirs=[str(skills_root)],
        top_k=3,
        max_active_skills=1,
        activation_threshold=0.95,
    )
    runtime = SkillRuntime(config=config)
    selection = runtime.route("hello world")
    assert selection.fallback is True
    assert selection.selected_skills == []

