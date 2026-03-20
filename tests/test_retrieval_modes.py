import sys
import types
from pathlib import Path

import pytest

from skill_adapter import SkillConfig, SkillRuntime
from skill_adapter.retrieval.factory import build_retriever
from skill_adapter.retrieval.hybrid import HybridRetriever
from skill_adapter.retrieval.rerank_pipeline import RerankPipelineRetriever
from test_utils import make_case_dir


def _write_skill(root: Path, name: str, content: str) -> None:
    d = root / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(content, encoding="utf-8")


def _install_fake_flag_embedding(monkeypatch) -> None:
    class FakeBGEM3FlagModel:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def encode(self, texts, **kwargs):
            dense_vecs = []
            for text in texts:
                normalized = str(text).lower()
                dense_vecs.append(
                    [
                        float("route" in normalized),
                        float("code" in normalized),
                        float("paper" in normalized),
                    ]
                )
            return {"dense_vecs": dense_vecs}

    class FakeFlagReranker:
        def __init__(self, *args, **kwargs) -> None:
            self.args = args
            self.kwargs = kwargs

        def compute_score(self, pairs):
            scores = []
            for query, doc in pairs:
                q = str(query).lower()
                d = str(doc).lower()
                scores.append(float("route" in q and "route" in d) + float("code" in q and "code" in d))
            return scores

    fake_module = types.SimpleNamespace(BGEM3FlagModel=FakeBGEM3FlagModel, FlagReranker=FakeFlagReranker)
    monkeypatch.setitem(sys.modules, "FlagEmbedding", fake_module)


@pytest.mark.parametrize(
    "mode",
    [
        "bm25_sentence",
        "bm25_bge_m3",
        "bge_m3_rerank",
        "bm25_bge_m3_rerank",
    ],
)
def test_config_accepts_supported_retrieval_modes(mode: str) -> None:
    config = SkillConfig(skill_dirs=["./skills"], retrieval_mode=mode)
    assert config.retrieval_mode == mode


def test_builder_returns_hybrid_for_bm25_sentence() -> None:
    config = SkillConfig(skill_dirs=["./skills"], retrieval_mode="bm25_sentence")
    retriever = build_retriever(config)
    assert isinstance(retriever, HybridRetriever)
    assert retriever.debug_info()["retrieval_mode"] == "bm25_sentence"


def test_builder_returns_hybrid_for_bm25_bge_m3(monkeypatch) -> None:
    _install_fake_flag_embedding(monkeypatch)
    config = SkillConfig(skill_dirs=["./skills"], retrieval_mode="bm25_bge_m3")
    retriever = build_retriever(config)
    assert isinstance(retriever, HybridRetriever)
    assert retriever.debug_info()["semantic_backend"] == "bge_m3"


def test_builder_returns_rerank_pipeline_for_rerank_modes(monkeypatch) -> None:
    _install_fake_flag_embedding(monkeypatch)
    for mode in ["bge_m3_rerank", "bm25_bge_m3_rerank"]:
        config = SkillConfig(skill_dirs=["./skills"], retrieval_mode=mode)
        retriever = build_retriever(config)
        assert isinstance(retriever, RerankPipelineRetriever)


def test_bm25_sentence_mode_is_runnable_without_semantic_dependency() -> None:
    skills_root = make_case_dir() / "skills"
    _write_skill(
        skills_root,
        "paper-summary",
        "---\nname: Paper Summary\ndescription: Summarize paper\n---\n",
    )

    runtime = SkillRuntime(
        config=SkillConfig(
            skill_dirs=[str(skills_root)],
            retrieval_mode="bm25_sentence",
            activation_threshold=0.0,
        )
    )
    selection = runtime.route("summarize paper", debug=True)

    assert "retrieval_mode" in selection.trace
    assert selection.trace["retrieval_mode"] == "bm25_sentence"
    assert isinstance(selection.trace["retrieval_errors"], list)


def test_bm25_bge_m3_mode_is_runnable_with_mocked_backend(monkeypatch) -> None:
    _install_fake_flag_embedding(monkeypatch)
    skills_root = make_case_dir() / "skills"
    _write_skill(
        skills_root,
        "route-code",
        "---\nname: Route Code\ndescription: Route code tasks\n---\n",
    )
    _write_skill(
        skills_root,
        "paper-summary",
        "---\nname: Paper Summary\ndescription: Summarize paper\n---\n",
    )

    runtime = SkillRuntime(
        config=SkillConfig(
            skill_dirs=[str(skills_root)],
            retrieval_mode="bm25_bge_m3",
            activation_threshold=0.0,
        )
    )
    selection = runtime.route("help me route this code task", debug=True)

    assert selection.trace["retrieval_mode"] == "bm25_bge_m3"
    assert selection.trace["semantic_backend"] == "bge_m3"


def test_rerank_mode_is_runnable_with_mocked_reranker(monkeypatch) -> None:
    _install_fake_flag_embedding(monkeypatch)
    skills_root = make_case_dir() / "skills"
    _write_skill(
        skills_root,
        "route-code",
        "---\nname: Route Code\ndescription: Route code tasks\n---\n",
    )
    _write_skill(
        skills_root,
        "paper-summary",
        "---\nname: Paper Summary\ndescription: Summarize paper\n---\n",
    )

    runtime = SkillRuntime(
        config=SkillConfig(
            skill_dirs=[str(skills_root)],
            retrieval_mode="bge_m3_rerank",
            activation_threshold=0.0,
        )
    )
    selection = runtime.route("route code", debug=True)

    assert selection.trace["retrieval_mode"] == "bge_m3_rerank"
    assert selection.trace["reranker_enabled"] is True
    assert not any("not implemented" in err.lower() for err in selection.trace["retrieval_errors"])
    if selection.candidates:
        assert "rerank[bge_m3_rerank]" in selection.candidates[0]["reason"]


def test_missing_model_guidance_contains_mode_and_cache_hints() -> None:
    from skill_adapter.retrieval.guidance import build_missing_model_guidance

    bge = build_missing_model_guidance("bge_m3")
    rerank = build_missing_model_guidance("reranker")

    assert "bm25_sentence" in bge
    assert "HF_HOME" in bge
    assert "bm25_bge_m3" in rerank
    assert "HF_HOME" in rerank


def test_strict_retrieval_raises_when_bge_backend_unavailable(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "FlagEmbedding", types.SimpleNamespace())
    skills_root = make_case_dir() / "skills"
    _write_skill(
        skills_root,
        "route-code",
        "---\nname: Route Code\ndescription: Route code tasks\n---\n",
    )

    runtime = SkillRuntime(
        config=SkillConfig(
            skill_dirs=[str(skills_root)],
            retrieval_mode="bge_m3_rerank",
            activation_threshold=0.0,
            strict_retrieval=True,
        )
    )

    with pytest.raises(RuntimeError, match="semantic retrieval unavailable"):
        _ = runtime.route("route code", debug=True)
