import re
import sys
import types

from skill_adapter.config import SkillConfig
from skill_adapter.models import SkillMetadata
from skill_adapter.retrieval.hybrid import HybridRetriever
from skill_adapter.retrieval.semantic import (
    BgeM3EmbeddingBackend,
    SemanticRetriever,
    build_routing_retrieval_text,
)


def _skill(
    skill_id: str,
    name: str,
    description: str,
    use_when: list[str],
    examples: list[str],
) -> SkillMetadata:
    return SkillMetadata(
        skill_id=skill_id,
        name=name,
        description=description,
        retrieval_text=f"{name}\n{description}",
        use_when=use_when,
        examples=examples,
        path=f"/tmp/{skill_id}/SKILL.md",
    )


def _install_fake_flag_embedding(monkeypatch) -> None:
    class FakeBGEM3FlagModel:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def encode(self, texts, **kwargs):
            dense_vecs = []
            lexical_weights = []
            for text in texts:
                normalized = str(text).lower()
                tokens = re.findall(r"[a-z]+", normalized)
                lexical = {}
                for token in tokens:
                    lexical[token] = lexical.get(token, 0.0) + 1.0
                lexical_weights.append(lexical)
                dense_vecs.append(
                    [
                        float("route" in normalized),
                        float("code" in normalized),
                        float("paper" in normalized),
                    ]
                )
            return {"dense_vecs": dense_vecs, "lexical_weights": lexical_weights}

    fake_module = types.SimpleNamespace(BGEM3FlagModel=FakeBGEM3FlagModel)
    monkeypatch.setitem(sys.modules, "FlagEmbedding", fake_module)


def test_bge_m3_backend_can_initialize_and_encode(monkeypatch) -> None:
    _install_fake_flag_embedding(monkeypatch)
    backend = BgeM3EmbeddingBackend(model_name="BAAI/bge-m3", use_fp16=True)
    vectors = backend.encode(["route question", "paper question"])

    assert len(vectors) == 2
    assert all(vectors)


def test_bge_m3_semantic_retrieval_returns_scored_candidates(monkeypatch) -> None:
    _install_fake_flag_embedding(monkeypatch)
    backend = BgeM3EmbeddingBackend(model_name="BAAI/bge-m3")
    retriever = SemanticRetriever(
        backend,
        text_builder=build_routing_retrieval_text,
        use_embedding_cache=True,
    )
    skills = [
        _skill(
            "route-code",
            "Route Code",
            "Route code related questions",
            use_when=["when user asks code route logic"],
            examples=["route this implementation request"],
        ),
        _skill(
            "paper-summary",
            "Paper Summary",
            "Summarize paper content",
            use_when=["when user asks paper summary"],
            examples=["summarize this paper"],
        ),
    ]

    candidates = retriever.retrieve("help route this code request", skills, top_k=2)

    assert len(candidates) == 2
    assert candidates[0].metadata.skill_id == "route-code"
    assert isinstance(candidates[0].semantic_score, float)
    assert "semantic[bge_m3]" in candidates[0].reason


def test_hybrid_retrieval_works_with_bge_m3_semantic_backend(monkeypatch) -> None:
    _install_fake_flag_embedding(monkeypatch)
    backend = BgeM3EmbeddingBackend(model_name="BAAI/bge-m3")
    semantic = SemanticRetriever(backend, text_builder=build_routing_retrieval_text)
    config = SkillConfig(skill_dirs=["./skills"], semantic_backend="bge_m3")
    retriever = HybridRetriever(config=config, semantic_retriever=semantic)
    skills = [
        _skill(
            "route-code",
            "Route Code",
            "Route code related questions",
            use_when=["when user asks code route logic"],
            examples=["route this implementation request"],
        ),
        _skill(
            "paper-summary",
            "Paper Summary",
            "Summarize paper content",
            use_when=["when user asks paper summary"],
            examples=["summarize this paper"],
        ),
    ]

    result = retriever.retrieve("help route this code request", skills, top_k=2)

    assert result.semantic_candidates
    assert result.fused_candidates
    assert "semantic_backend=bge_m3" in result.fused_candidates[0].reason
