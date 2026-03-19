from typing import List

from .config import SkillConfig
from .models import SkillSelection
from .registry import SkillRegistry
from .retrieval.base import BaseRetriever


class SkillRouter:
    def __init__(self, config: SkillConfig, retriever: BaseRetriever) -> None:
        self.config = config
        self.retriever = retriever

    def route(self, query: str, registry: SkillRegistry) -> SkillSelection:
        metadata = registry.list_metadata()
        if not metadata:
            return SkillSelection(
                selected_skills=[],
                candidates=[],
                reason="no skill metadata available",
                fallback=True,
            )

        candidates = self.retriever.retrieve(query=query, skills=metadata, top_k=self.config.top_k)
        candidate_dicts = [
            {"skill": c.metadata.skill_id, "score": c.score, "reason": c.reason}
            for c in candidates
        ]

        selected = [c for c in candidates if c.score >= self.config.activation_threshold]
        selected = selected[: self.config.max_active_skills]

        if not selected:
            reason = "no candidate passed activation threshold"
            return SkillSelection(
                selected_skills=[],
                candidates=candidate_dicts,
                reason=reason,
                fallback=True,
            )

        selected_dicts = [{"skill": c.metadata.skill_id, "score": c.score} for c in selected]
        reason = f"selected {', '.join([c.metadata.skill_id for c in selected])}"
        return SkillSelection(
            selected_skills=selected_dicts,
            candidates=candidate_dicts,
            reason=reason,
            fallback=False,
        )
