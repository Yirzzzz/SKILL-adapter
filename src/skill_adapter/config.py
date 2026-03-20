from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Literal, Optional


RetrievalMode = Literal[
    "bm25_sentence",
    "bm25_bge_m3",
    "bge_m3_rerank",
    "bm25_bge_m3_rerank",
]


@dataclass
class SkillConfig:
    skill_dirs: List[str]
    retrieval_mode: RetrievalMode = "bm25_sentence"
    top_k: int = 3
    bm25_top_k: int = 5
    semantic_top_k: int = 5
    rerank_top_k: int = 20
    max_active_skills: int = 1
    activation_threshold: float = 0.35
    bm25_weight: float = 0.5
    semantic_weight: float = 0.5
    sentence_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    bge_m3_model_name: str = "BAAI/bge-m3"
    reranker_model_name: str = "BAAI/bge-reranker-v2-m3"
    bge_m3_use_fp16: bool = True
    embedding_model_name: Optional[str] = None
    semantic_backend: Optional[str] = None
    enable_semantic_retrieval: bool = True  # kept for backward compatibility
    enable_bm25_retrieval: bool = True  # kept for backward compatibility
    strict_retrieval: bool = False
    debug: bool = False

    def __post_init__(self) -> None:
        supported_modes = {
            "bm25_sentence",
            "bm25_bge_m3",
            "bge_m3_rerank",
            "bm25_bge_m3_rerank",
        }
        if not self.skill_dirs:
            raise ValueError("skill_dirs must not be empty")
        if self.retrieval_mode not in supported_modes:
            raise ValueError(f"unsupported retrieval_mode: {self.retrieval_mode}")
        if self.top_k <= 0:
            raise ValueError("top_k must be > 0")
        if self.bm25_top_k <= 0:
            raise ValueError("bm25_top_k must be > 0")
        if self.semantic_top_k <= 0:
            raise ValueError("semantic_top_k must be > 0")
        if self.rerank_top_k <= 0:
            raise ValueError("rerank_top_k must be > 0")
        if self.max_active_skills <= 0:
            raise ValueError("max_active_skills must be > 0")
        if not 0 <= self.activation_threshold <= 1:
            raise ValueError("activation_threshold must be in [0, 1]")
        if self.bm25_weight < 0 or self.semantic_weight < 0:
            raise ValueError("retrieval weights must be >= 0")
        if self.bm25_weight == 0 and self.semantic_weight == 0:
            raise ValueError("at least one retrieval weight must be > 0")

        if self.embedding_model_name:
            self.sentence_model_name = self.embedding_model_name
        if self.semantic_backend == "bge_m3" and self.retrieval_mode == "bm25_sentence":
            self.retrieval_mode = "bm25_bge_m3"

    @classmethod
    def from_dirs(cls, skill_dirs: Iterable[str], **kwargs: object) -> "SkillConfig":
        normalized = [str(Path(p)) for p in skill_dirs]
        return cls(skill_dirs=normalized, **kwargs)
