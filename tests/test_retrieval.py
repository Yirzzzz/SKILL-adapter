from skill_adapter.config import SkillConfig
from skill_adapter.models import SkillMetadata
from skill_adapter.retrieval.bm25 import BM25Retriever
from skill_adapter.retrieval.hybrid import HybridRetriever
from skill_adapter.retrieval.semantic import SemanticRetriever


class FakeEmbeddingBackend:
    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self.vectors = vectors

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self.vectors[text] for text in texts]


def _skill(skill_id: str, name: str, description: str) -> SkillMetadata:
    return SkillMetadata(
        skill_id=skill_id,
        name=name,
        description=description,
        retrieval_text=f"{name}\n{description}",
        use_when=[],
        examples=[],
        path=f"/tmp/{skill_id}/SKILL.md",
    )


def test_bm25_retrieval_hits_obvious_chinese_keyword_query() -> None:
    retriever = BM25Retriever()
    skills = [
        _skill("paper-summary", "论文总结", "总结学术论文并提炼贡献与局限"),
        _skill("code-explain", "代码讲解", "解释源码实现和模块结构"),
    ]

    candidates = retriever.retrieve("请总结这篇论文的贡献", skills, top_k=2)
    assert candidates[0].metadata.skill_id == "paper-summary"
    assert candidates[0].bm25_score > candidates[1].bm25_score


def test_semantic_retrieval_hits_semantically_similar_query() -> None:
    skills = [
        _skill("paper-summary", "Paper Summary", "Summarize academic papers"),
        _skill("code-explain", "Code Explain", "Explain source code and architecture"),
    ]
    vectors = {
        skills[0].retrieval_text: [1.0, 0.0],
        skills[1].retrieval_text: [0.0, 1.0],
        "help me understand this implementation": [0.0, 0.95],
    }
    retriever = SemanticRetriever(FakeEmbeddingBackend(vectors))

    candidates = retriever.retrieve("help me understand this implementation", skills, top_k=2)
    assert candidates[0].metadata.skill_id == "code-explain"
    assert candidates[0].semantic_score > candidates[1].semantic_score


def test_hybrid_retrieval_fuses_bm25_and_semantic_candidates() -> None:
    skills = [
        _skill("paper-summary", "Paper Summary", "Summarize academic papers"),
        _skill("code-explain", "Code Explain", "Explain source code and architecture"),
        _skill("research-qa", "Research QA", "Answer questions about research work"),
    ]
    query = "summarize this paper"
    vectors = {
        skills[0].retrieval_text: [0.2, 0.1],
        skills[1].retrieval_text: [0.0, 1.0],
        skills[2].retrieval_text: [1.0, 0.0],
        query: [0.95, 0.0],
    }
    config = SkillConfig(
        skill_dirs=["./skills"],
        top_k=3,
        bm25_top_k=1,
        semantic_top_k=1,
        bm25_weight=0.5,
        semantic_weight=0.5,
    )
    retriever = HybridRetriever(
        config=config,
        semantic_retriever=SemanticRetriever(FakeEmbeddingBackend(vectors)),
    )

    result = retriever.retrieve(query, skills, top_k=3)
    fused_ids = [candidate.metadata.skill_id for candidate in result.fused_candidates]

    assert result.bm25_candidates[0].metadata.skill_id == "paper-summary"
    assert result.semantic_candidates[0].metadata.skill_id == "research-qa"
    assert "paper-summary" in fused_ids
    assert "research-qa" in fused_ids
