from abc import ABC, abstractmethod
from typing import List

from ..models import SkillCandidate, SkillMetadata


class BaseRetriever(ABC):
    @abstractmethod
    def retrieve(self, query: str, skills: List[SkillMetadata], top_k: int) -> List[SkillCandidate]:
        raise NotImplementedError
