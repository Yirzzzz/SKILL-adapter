from typing import List, Optional

from ..config import SkillConfig
from ..models import SkillCandidate, SkillMetadata
from .base import BaseRetriever, RetrievalResult
from .bm25 import BM25Retriever
from .semantic import EmbeddingBackend, SemanticRetriever

class HybridRetriever(BaseRetriever):
    def __init__(
        self,
        config: SkillConfig,
        *,
        bm25_retriever: Optional[BM25Retriever] = None,
        embedding_backend: Optional[EmbeddingBackend] = None,
        semantic_retriever: Optional[SemanticRetriever] = None,
    ) -> None:
        self.config = config
        self.bm25_retriever = bm25_retriever or BM25Retriever()
        if semantic_retriever is not None:
            self.semantic_retriever = semantic_retriever
        elif embedding_backend is not None:
            self.semantic_retriever = SemanticRetriever(embedding_backend)
        else:
            self.semantic_retriever = None

    def retrieve(self, query: str, skills: List[SkillMetadata], top_k: int) -> RetrievalResult:
        result = RetrievalResult(query=query)
        if not query.strip() or not skills:
            return result

        bm25_candidates: List[SkillCandidate] = []
        semantic_candidates: List[SkillCandidate] = []

        if self.config.enable_bm25_retrieval:
            bm25_candidates = self.bm25_retriever.retrieve(query, skills, self.config.bm25_top_k)

        if self.config.enable_semantic_retrieval and self.semantic_retriever is not None:
            try:
                semantic_candidates = self.semantic_retriever.retrieve(
                    query, skills, self.config.semantic_top_k
                )
            except Exception as exc:
                result.errors.append(f"semantic retrieval unavailable: {exc}")

        result.bm25_candidates = bm25_candidates
        result.semantic_candidates = semantic_candidates

        bm25_scores = {candidate.metadata.skill_id: candidate.bm25_score for candidate in bm25_candidates}
        semantic_scores = {
            candidate.metadata.skill_id: max(0.0, candidate.semantic_score)
            for candidate in semantic_candidates
        }

        skill_map = {skill.skill_id: skill for skill in skills}
        candidate_ids = list(dict.fromkeys([*bm25_scores.keys(), *semantic_scores.keys()]))
        fused_candidates: List[SkillCandidate] = []
        for skill_id in candidate_ids:
            bm25_score = bm25_scores.get(skill_id, 0.0)
            semantic_score = semantic_scores.get(skill_id, 0.0)
            final_score = (
                self.config.bm25_weight * bm25_score
                + self.config.semantic_weight * semantic_score
            )
            fused_candidates.append(
                SkillCandidate(
                    metadata=skill_map[skill_id],
                    score=round(final_score, 6),
                    final_score=round(final_score, 6),
                    bm25_score=round(bm25_score, 6),
                    semantic_score=round(semantic_score, 6),
                    reason=(
                        f"hybrid fusion raw_bm25={round(bm25_score, 4)} "
                        f"raw_semantic={round(semantic_score, 4)}"
                    ),
                )
            )

        fused_candidates.sort(key=lambda item: item.final_score, reverse=True)
        result.fused_candidates = fused_candidates[:top_k]
        return result
