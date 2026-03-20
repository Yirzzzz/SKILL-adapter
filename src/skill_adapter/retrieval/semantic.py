from math import sqrt
from typing import Callable, Dict, List, Optional, Protocol

from ..models import SkillCandidate, SkillMetadata
from .guidance import build_missing_model_guidance


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


class BgeM3EmbeddingBackend:
    def __init__(self, model_name: str, use_fp16: bool = True) -> None:
        self.model_name = model_name
        self.use_fp16 = use_fp16
        self._model: Optional[object] = None

    def _get_model(self) -> object:
        if self._model is None:
            guidance = build_missing_model_guidance("bge_m3")
            try:
                from FlagEmbedding import BGEM3FlagModel
            except ImportError as exc:
                raise RuntimeError(
                    f"FlagEmbedding is required for bge-m3 retrieval. {guidance}"
                ) from exc

            try:
                self._model = BGEM3FlagModel(
                    model_name_or_path=self.model_name,
                    use_fp16=self.use_fp16,
                )
            except Exception as exc:
                raise RuntimeError(
                    f"failed to initialize bge-m3 model '{self.model_name}': {exc}. {guidance}"
                ) from exc
        return self._model

    def encode(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        model = self._get_model()
        outputs = model.encode(texts, return_dense=True, return_sparse=False, return_colbert_vecs=False)
        dense_vecs = outputs.get("dense_vecs") if isinstance(outputs, dict) else None
        if dense_vecs is None:
            raise RuntimeError("bge-m3 backend did not return dense_vecs")
        return [list(map(float, vector)) for vector in dense_vecs]


def build_routing_retrieval_text(skill: SkillMetadata) -> str:
    parts = [skill.name, skill.description]
    if skill.use_when:
        parts.append("Use When:\n- " + "\n- ".join(skill.use_when))
    if skill.examples:
        parts.append("Examples:\n- " + "\n- ".join(skill.examples))
    return "\n".join(part for part in parts if part).strip()


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
    def __init__(
        self,
        embedding_backend: EmbeddingBackend,
        *,
        text_builder: Optional[Callable[[SkillMetadata], str]] = None,
        use_embedding_cache: bool = True,
        backend_name: Optional[str] = None,
    ) -> None:
        self.embedding_backend = embedding_backend
        self.text_builder = text_builder or (lambda skill: skill.retrieval_text)
        self.use_embedding_cache = use_embedding_cache
        self.backend_name = backend_name or self._infer_backend_name(embedding_backend)
        self._skill_embedding_cache: Dict[str, List[float]] = {}

    def _infer_backend_name(self, backend: object) -> str:
        name = backend.__class__.__name__.lower()
        if "bgem3" in name or "bge" in name:
            return "bge_m3"
        if "sentence" in name:
            return "sentence_transformers"
        return "semantic"

    def _embedding_key(self, skill: SkillMetadata, text: str) -> str:
        return f"{skill.skill_id}:{text}"

    def _ensure_skill_embeddings(self, skills: List[SkillMetadata]) -> Dict[str, str]:
        texts: Dict[str, str] = {}
        missing_skills: List[SkillMetadata] = []
        for skill in skills:
            text = self.text_builder(skill)
            texts[skill.skill_id] = text
            if not self.use_embedding_cache:
                missing_skills.append(skill)
                continue
            key = self._embedding_key(skill, text)
            if key not in self._skill_embedding_cache:
                missing_skills.append(skill)

        if missing_skills:
            vectors = self.embedding_backend.encode([texts[skill.skill_id] for skill in missing_skills])
            for skill, vector in zip(missing_skills, vectors):
                text = texts[skill.skill_id]
                self._skill_embedding_cache[self._embedding_key(skill, text)] = vector
        return texts

    def retrieve(self, query: str, skills: List[SkillMetadata], top_k: int) -> List[SkillCandidate]:
        if not query.strip() or not skills:
            return []

        texts = self._ensure_skill_embeddings(skills)
        query_embedding = self.embedding_backend.encode([query])[0]

        candidates: List[SkillCandidate] = []
        for skill in skills:
            text = texts[skill.skill_id]
            embedding = self._skill_embedding_cache[self._embedding_key(skill, text)]
            score = _cosine_similarity(query_embedding, embedding)
            candidates.append(
                SkillCandidate(
                    metadata=skill,
                    score=round(score, 6),
                    semantic_score=round(score, 6),
                    reason=f"semantic[{self.backend_name}] similarity on retrieval_text",
                )
            )

        candidates.sort(key=lambda item: item.semantic_score, reverse=True)
        return candidates[:top_k]
