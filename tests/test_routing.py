from pathlib import Path

from skill_adapter import SkillRuntime
from skill_adapter.config import SkillConfig
from skill_adapter.retrieval.hybrid import HybridRetriever
from skill_adapter.retrieval.semantic import SemanticRetriever
from skill_adapter.routing import SkillRouter
from test_utils import make_case_dir


class FakeEmbeddingBackend:
    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self.vectors = vectors

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self.vectors[text] for text in texts]


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
    assert selection.trace["activation_threshold"] == 0.95
    assert selection.trace["query"] == "hello world"


def test_route_returns_hybrid_trace_details() -> None:
    skills_root = make_case_dir() / "skills"
    _write_skill(
        skills_root,
        "paper-summary",
        "---\nname: Paper Summary\ndescription: Summarize academic papers\n---\n",
    )
    _write_skill(
        skills_root,
        "code-explain",
        "---\nname: Code Explain\ndescription: Explain source code and architecture\n---\n",
    )

    config = SkillConfig(skill_dirs=[str(skills_root)], activation_threshold=0.3)
    runtime = SkillRuntime(config=config)
    vectors = {
        "Paper Summary\nSummarize academic papers": [1.0, 0.0],
        "Code Explain\nExplain source code and architecture": [0.0, 1.0],
        "summarize this paper": [0.95, 0.0],
    }
    runtime.router = SkillRouter(
        config=config,
        retriever=HybridRetriever(
            config=config,
            semantic_retriever=SemanticRetriever(FakeEmbeddingBackend(vectors)),
        ),
    )

    selection = runtime.route("summarize this paper", debug=True)

    assert selection.fallback is False
    assert selection.selected_skills[0]["skill"] == "paper-summary"
    assert selection.trace["bm25_candidates"][0]["skill"] == "paper-summary"
    assert selection.trace["semantic_candidates"][0]["skill"] == "paper-summary"
    assert selection.trace["fused_candidates"][0]["skill"] == "paper-summary"
