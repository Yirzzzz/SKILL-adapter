import re
from typing import List, Optional, Protocol, Sequence, Set

from ..config import SkillConfig
from ..models import SkillCandidate, SkillMetadata
from .base import BaseRetriever, RetrievalResult
from .guidance import build_missing_model_guidance
from .semantic import build_routing_retrieval_text


class RerankerBackend(Protocol):
    backend_name: str

    def score(self, query: str, documents: Sequence[str]) -> List[float]:
        ...


class FlagEmbeddingRerankerBackend:
    backend_name = "bge_reranker"

    def __init__(self, model_name: str, use_fp16: bool = True) -> None:
        self.model_name = model_name
        self.use_fp16 = use_fp16
        self._model = None

    def _get_model(self):
        if self._model is None:
            guidance = build_missing_model_guidance("reranker")
            try:
                from FlagEmbedding import FlagReranker
            except ImportError as exc:
                raise RuntimeError(
                    f"FlagEmbedding is required for reranker retrieval. {guidance}"
                ) from exc

            try:
                self._model = FlagReranker(self.model_name, use_fp16=self.use_fp16)
            except Exception as exc:
                raise RuntimeError(
                    f"failed to initialize reranker model '{self.model_name}': {exc}. {guidance}"
                ) from exc
        return self._model

    def score(self, query: str, documents: Sequence[str]) -> List[float]:
        if not documents:
            return []
        model = self._get_model()
        pairs = [[query, doc] for doc in documents]
        output = model.compute_score(pairs)
        if isinstance(output, list):
            return [float(item) for item in output]
        return [float(output)]


class TokenOverlapRerankerBackend:
    backend_name = "token_overlap"

    def _tokens(self, text: str) -> Set[str]:
        return set(re.findall(r"[\u4e00-\u9fff]|[a-z0-9]+", text.lower()))

    def score(self, query: str, documents: Sequence[str]) -> List[float]:
        query_tokens = self._tokens(query)
        scores: List[float] = []
        for doc in documents:
            doc_tokens = self._tokens(doc)
            if not query_tokens or not doc_tokens:
                scores.append(0.0)
                continue
            overlap = len(query_tokens & doc_tokens)
            union = len(query_tokens | doc_tokens)
            scores.append(float(overlap) / float(union))
        return scores


class RerankPipelineRetriever(BaseRetriever):
    def __init__(
        self,
        config: SkillConfig,
        *,
        first_stage: BaseRetriever,
        retrieval_mode: str,
        reranker_backend: Optional[RerankerBackend] = None,
    ) -> None:
        self.config = config
        self.first_stage = first_stage
        self.retrieval_mode = retrieval_mode
        self.reranker_backend = reranker_backend or FlagEmbeddingRerankerBackend(
            model_name=config.reranker_model_name,
            use_fp16=config.bge_m3_use_fp16,
        )
        self.fallback_backend = TokenOverlapRerankerBackend()
        self._last_reranker_backend = self.reranker_backend.backend_name

    def debug_info(self) -> dict:
        first_stage_info = self.first_stage.debug_info() if hasattr(self.first_stage, "debug_info") else {}
        return {
            "retrieval_mode": self.retrieval_mode,
            "semantic_backend": first_stage_info.get("semantic_backend", "bge_m3"),
            "reranker_enabled": True,
            "reranker_model": self.config.reranker_model_name,
            "reranker_backend": self._last_reranker_backend,
            "rerank_top_k": self.config.rerank_top_k,
            "implementation_status": "active",
        }

    def retrieve(self, query: str, skills: List[SkillMetadata], top_k: int) -> RetrievalResult:
        result = RetrievalResult(query=query)
        if not query.strip() or not skills:
            return result

        first_stage_k = max(top_k, self.config.rerank_top_k)
        first_result = self.first_stage.retrieve(query=query, skills=skills, top_k=first_stage_k)
        result.bm25_candidates = first_result.bm25_candidates
        result.semantic_candidates = first_result.semantic_candidates
        result.errors.extend(first_result.errors)

        first_stage_candidates = first_result.fused_candidates[: self.config.rerank_top_k]
        if not first_stage_candidates:
            return result

        docs = [build_routing_retrieval_text(candidate.metadata) for candidate in first_stage_candidates]

        try:
            rerank_scores = self.reranker_backend.score(query, docs)
            backend_name = self.reranker_backend.backend_name
        except Exception as exc:
            if self.config.strict_retrieval:
                raise RuntimeError(f"reranker unavailable: {exc}") from exc
            result.errors.append(f"reranker unavailable: {exc}")
            rerank_scores = self.fallback_backend.score(query, docs)
            backend_name = self.fallback_backend.backend_name

        self._last_reranker_backend = backend_name
        reranked_candidates: List[SkillCandidate] = []
        for candidate, rerank_score in zip(first_stage_candidates, rerank_scores):
            final_score = round(float(rerank_score), 6)
            reranked_candidates.append(
                SkillCandidate(
                    metadata=candidate.metadata,
                    score=final_score,
                    final_score=final_score,
                    bm25_score=candidate.bm25_score,
                    semantic_score=candidate.semantic_score,
                    reason=(
                        f"rerank[{self.retrieval_mode}] backend={backend_name} "
                        f"first_stage={round(candidate.score, 4)} rerank={round(float(rerank_score), 4)}"
                    ),
                )
            )

        reranked_candidates.sort(key=lambda item: item.final_score, reverse=True)
        result.fused_candidates = reranked_candidates[:top_k]
        return result
