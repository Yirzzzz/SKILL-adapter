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
        base_trace = {
            "query": query,
            "bm25_candidates": [],
            "semantic_candidates": [],
            "fused_candidates": [],
            "selected_skills": [],
            "activation_threshold": self.config.activation_threshold,
            "fallback": True,
            "reason": "",
            "registry_errors": registry.build_errors,
            "retrieval_errors": [],
        }
        if not metadata:
            return SkillSelection(
                selected_skills=[],
                candidates=[],
                reason="no skill metadata available",
                fallback=True,
                trace={**base_trace, "reason": "no skill metadata available"},
            )

        retrieval = self.retriever.retrieve(query=query, skills=metadata, top_k=self.config.top_k)
        candidates = retrieval.fused_candidates
        candidate_dicts = [
            {
                "skill": c.metadata.skill_id,
                "score": c.score,
                "bm25_score": c.bm25_score,
                "semantic_score": c.semantic_score,
                "reason": c.reason,
            }
            for c in candidates
        ]
        trace = {
            **base_trace,
            "bm25_candidates": [
                {"skill": c.metadata.skill_id, "score": c.bm25_score, "reason": c.reason}
                for c in retrieval.bm25_candidates
            ],
            "semantic_candidates": [
                {"skill": c.metadata.skill_id, "score": c.semantic_score, "reason": c.reason}
                for c in retrieval.semantic_candidates
            ],
            "fused_candidates": [
                {
                    "skill": c.metadata.skill_id,
                    "bm25_score": c.bm25_score,
                    "semantic_score": c.semantic_score,
                    "final_score": c.final_score,
                    "reason": c.reason,
                }
                for c in candidates
            ],
            "retrieval_errors": retrieval.errors,
        }

        selected = [c for c in candidates if c.score >= self.config.activation_threshold]
        selected = selected[: self.config.max_active_skills]

        if not selected:
            reason = "no candidate passed activation threshold"
            trace["reason"] = reason
            return SkillSelection(
                selected_skills=[],
                candidates=candidate_dicts,
                reason=reason,
                fallback=True,
                trace=trace,
            )

        selected_dicts = [{"skill": c.metadata.skill_id, "score": c.score} for c in selected]
        selected_names = ", ".join([c.metadata.skill_id for c in selected])
        reason = f"{selected_names} has the highest fused score"
        trace["selected_skills"] = selected_dicts
        trace["fallback"] = False
        trace["reason"] = reason
        return SkillSelection(
            selected_skills=selected_dicts,
            candidates=candidate_dicts,
            reason=reason,
            fallback=False,
            trace=trace,
        )
