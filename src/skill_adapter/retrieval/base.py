from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

from ..models import SkillCandidate, SkillMetadata


@dataclass
class RetrievalResult:
    query: str
    bm25_candidates: List[SkillCandidate] = field(default_factory=list)
    semantic_candidates: List[SkillCandidate] = field(default_factory=list)
    fused_candidates: List[SkillCandidate] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class BaseRetriever(ABC):
    @abstractmethod
    def retrieve(self, query: str, skills: List[SkillMetadata], top_k: int) -> RetrievalResult:
        raise NotImplementedError

    def debug_info(self) -> dict:
        return {}
