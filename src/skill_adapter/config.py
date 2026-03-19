from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass
class SkillConfig:
    skill_dirs: List[str]
    top_k: int = 3
    bm25_top_k: int = 5
    semantic_top_k: int = 5
    max_active_skills: int = 1
    activation_threshold: float = 0.35
    bm25_weight: float = 0.5
    semantic_weight: float = 0.5
    embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    enable_semantic_retrieval: bool = True
    enable_bm25_retrieval: bool = True
    debug: bool = False

    def __post_init__(self) -> None:
        if not self.skill_dirs:
            raise ValueError("skill_dirs must not be empty")
        if self.top_k <= 0:
            raise ValueError("top_k must be > 0")
        if self.bm25_top_k <= 0:
            raise ValueError("bm25_top_k must be > 0")
        if self.semantic_top_k <= 0:
            raise ValueError("semantic_top_k must be > 0")
        if self.max_active_skills <= 0:
            raise ValueError("max_active_skills must be > 0")
        if not 0 <= self.activation_threshold <= 1:
            raise ValueError("activation_threshold must be in [0, 1]")
        if self.bm25_weight < 0 or self.semantic_weight < 0:
            raise ValueError("retrieval weights must be >= 0")
        if self.bm25_weight == 0 and self.semantic_weight == 0:
            raise ValueError("at least one retrieval weight must be > 0")

    @classmethod
    def from_dirs(cls, skill_dirs: Iterable[str], **kwargs: object) -> "SkillConfig":
        normalized = [str(Path(p)) for p in skill_dirs]
        return cls(skill_dirs=normalized, **kwargs)
