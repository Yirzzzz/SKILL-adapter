from math import sqrt
from typing import Dict, List, Optional, Protocol

from ..models import SkillCandidate, SkillMetadata


class EmbeddingBackend(Protocol):
    def encode(self, texts: List[str]) -> List[List[float]]:
        ...


class SentenceTransformerEmbeddingBackend:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model: Optional[object] = None

    def _get_model(self) -> object:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "sentence-transformers is required for semantic retrieval"
                ) from exc
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        model = self._get_model()
        vectors = model.encode(texts, normalize_embeddings=True)
        return [list(map(float, vector)) for vector in vectors]


def _cosine_similarity(left: List[float], right: List[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


class SemanticRetriever:
    def __init__(self, embedding_backend: EmbeddingBackend) -> None:
        self.embedding_backend = embedding_backend
        self._skill_embedding_cache: Dict[str, List[float]] = {}

    def _embedding_key(self, skill: SkillMetadata) -> str:
        return f"{skill.skill_id}:{skill.retrieval_text}"

    def _ensure_skill_embeddings(self, skills: List[SkillMetadata]) -> None:
        missing_skills = [
            skill for skill in skills if self._embedding_key(skill) not in self._skill_embedding_cache
        ]
        if not missing_skills:
            return
        vectors = self.embedding_backend.encode([skill.retrieval_text for skill in missing_skills])
        for skill, vector in zip(missing_skills, vectors):
            self._skill_embedding_cache[self._embedding_key(skill)] = vector

    def retrieve(self, query: str, skills: List[SkillMetadata], top_k: int) -> List[SkillCandidate]:
        if not query.strip() or not skills:
            return []

        self._ensure_skill_embeddings(skills)
        query_embedding = self.embedding_backend.encode([query])[0]

        candidates: List[SkillCandidate] = []
        for skill in skills:
            score = _cosine_similarity(
                query_embedding, self._skill_embedding_cache[self._embedding_key(skill)]
            )
            candidates.append(
                SkillCandidate(
                    metadata=skill,
                    score=round(score, 6),
                    semantic_score=round(score, 6),
                    reason="semantic similarity on retrieval_text",
                )
            )
        candidates.sort(key=lambda item: item.semantic_score, reverse=True)
        return candidates[:top_k]
