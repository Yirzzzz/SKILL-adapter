from pathlib import Path

from skill_adapter import SkillRuntime
from skill_adapter.config import SkillConfig
from test_utils import make_case_dir


def _write_skill(root: Path, name: str, content: str) -> None:
    d = root / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(content, encoding="utf-8")


def test_only_selected_skill_is_lazy_loaded() -> None:
    skills_root = make_case_dir() / "skills"
    _write_skill(
        skills_root,
        "paper-summary",
        "# Paper Summary\nSummarize papers\n## Use When\n- summarize paper\n## Examples\n- summarize paper",
    )
    _write_skill(
        skills_root,
        "code-explain",
        "# Code Explain\nExplain code\n## Use When\n- explain code",
    )

    runtime = SkillRuntime(
        config=SkillConfig(skill_dirs=[str(skills_root)], activation_threshold=0.1, top_k=2)
    )

    _ = runtime.prepare(
        query="summarize paper",
        payload={"messages": [{"role": "user", "content": "summarize paper"}]},
        mode="messages",
    )

    assert runtime.loader.loaded_skills == ["paper-summary"]


def test_prepare_messages_augments_payload() -> None:
    skills_root = make_case_dir() / "skills"
    _write_skill(
        skills_root,
        "paper-summary",
        "# Paper Summary\nSummarize papers\n## Use When\n- summarize paper",
    )

    runtime = SkillRuntime(config=SkillConfig(skill_dirs=[str(skills_root)], activation_threshold=0.1))
    prepared = runtime.prepare(
        query="summarize paper",
        payload={"messages": [{"role": "user", "content": "summarize paper"}]},
        mode="messages",
    )

    assert prepared.trace["fallback"] is False
    assert prepared.trace["loaded"] is True
    assert prepared.payload["messages"][0]["role"] == "system"
    assert "Skill Adapter Context" in prepared.payload["messages"][0]["content"]


def test_prepare_input_augments_payload() -> None:
    skills_root = make_case_dir() / "skills"
    _write_skill(
        skills_root,
        "code-explain",
        "# Code Explain\nExplain code\n## Use When\n- explain code",
    )

    runtime = SkillRuntime(config=SkillConfig(skill_dirs=[str(skills_root)], activation_threshold=0.1))
    prepared = runtime.prepare(
        query="explain code",
        payload={"input": "please explain this code"},
        mode="input",
    )

    assert prepared.trace["fallback"] is False
    assert "Skill Adapter Context" in prepared.payload["input"]


def test_no_skill_keeps_original_payload() -> None:
    skills_root = make_case_dir() / "skills"
    _write_skill(skills_root, "paper-summary", "# Paper Summary\nSummarize paper")

    runtime = SkillRuntime(config=SkillConfig(skill_dirs=[str(skills_root)], activation_threshold=0.9))
    original_payload = {"messages": [{"role": "user", "content": "random query"}]}
    prepared = runtime.prepare(query="random query", payload=original_payload, mode="messages")

    assert prepared.trace["fallback"] is True
    assert prepared.payload == original_payload


def test_trace_structure() -> None:
    skills_root = make_case_dir() / "skills"
    _write_skill(
        skills_root,
        "paper-summary",
        "# Paper Summary\nSummarize papers\n## Use When\n- summarize paper",
    )

    runtime = SkillRuntime(config=SkillConfig(skill_dirs=[str(skills_root)], activation_threshold=0.1))
    prepared = runtime.prepare(
        query="summarize paper",
        payload={"messages": [{"role": "user", "content": "summarize paper"}]},
        mode="messages",
    )

    trace = prepared.trace
    for key in [
        "query",
        "bm25_candidates",
        "semantic_candidates",
        "fused_candidates",
        "selected_skills",
        "candidates",
        "reason",
        "fallback",
        "loaded",
        "mode",
        "activation_threshold",
    ]:
        assert key in trace
    assert isinstance(trace["selected_skills"], list)
    assert isinstance(trace["candidates"], list)
    assert isinstance(trace["bm25_candidates"], list)
    assert isinstance(trace["semantic_candidates"], list)
    assert isinstance(trace["fused_candidates"], list)
