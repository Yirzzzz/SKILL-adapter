from copy import deepcopy
from typing import Any, Dict, List, Optional

from .augmentation import augment_payload, build_augmentation_context
from .config import SkillConfig
from .loading import SkillLoader
from .models import PreparedPayload, SkillSelection
from .registry import SkillRegistry
from .retrieval.factory import build_retriever
from .routing import SkillRouter


class SkillRuntime:
    def __init__(
        self,
        skill_dirs: Optional[List[str]] = None,
        *,
        config: Optional[SkillConfig] = None,
    ) -> None:
        if config is None:
            if skill_dirs is None:
                raise ValueError("skill_dirs is required when config is not provided")
            config = SkillConfig.from_dirs(skill_dirs)
        self.config = config
        self.registry = SkillRegistry.build(self.config.skill_dirs)
        self.router = SkillRouter(
            config=self.config,
            retriever=build_retriever(self.config),
        )
        self.loader = SkillLoader()

    def route(self, query: str, debug: Optional[bool] = None) -> SkillSelection:
        _ = debug if debug is not None else self.config.debug
        return self.router.route(query=query, registry=self.registry)

    def prepare(
        self,
        query: str,
        payload: Dict[str, Any],
        mode: str,
        debug: Optional[bool] = None,
    ) -> PreparedPayload:
        _ = debug if debug is not None else self.config.debug
        original_payload = deepcopy(payload)
        selection = self.route(query=query, debug=debug)

        trace: Dict[str, Any] = dict(selection.trace)
        trace.update(
            {
                "selected_skills": selection.selected_skills,
                "candidates": selection.candidates,
                "reason": selection.reason,
                "fallback": selection.fallback,
                "loaded": False,
                "mode": mode,
            }
        )

        if selection.fallback or not selection.selected_skills:
            return PreparedPayload(payload=original_payload, trace=trace)

        try:
            contexts: List[str] = []
            for item in selection.selected_skills:
                metadata = self.registry.get(item["skill"])
                full_markdown = self.loader.load_skill_markdown(metadata)
                context = build_augmentation_context(metadata, full_markdown)
                contexts.append(context)

            prepared = augment_payload(original_payload, mode=mode, contexts=contexts)
            trace["loaded"] = True
            trace["fallback"] = False
            return PreparedPayload(payload=prepared, trace=trace)
        except Exception as exc:
            trace["fallback"] = True
            trace["loaded"] = False
            trace["reason"] = f"fallback due to prepare failure: {exc}"
            return PreparedPayload(payload=original_payload, trace=trace)
