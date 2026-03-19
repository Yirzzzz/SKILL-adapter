from copy import deepcopy
from typing import Any, Dict, List

from .models import SkillMetadata


def build_augmentation_context(metadata: SkillMetadata, full_skill_markdown: str) -> str:
    # Full markdown is lazily loaded only for selected skills.
    return (
        "[Skill Adapter Context]\n"
        f"skill_id: {metadata.skill_id}\n"
        f"name: {metadata.name}\n"
        f"description: {metadata.description}\n"
        f"use_when: {', '.join(metadata.use_when)}\n"
        "instructions:\n"
        f"{full_skill_markdown.strip()}\n"
        "[/Skill Adapter Context]"
    )


def augment_payload(payload: Dict[str, Any], mode: str, contexts: List[str]) -> Dict[str, Any]:
    out = deepcopy(payload)
    merged_context = "\n\n".join(contexts)

    if mode == "messages":
        messages = list(out.get("messages", []))
        system_msg = {
            "role": "system",
            "content": merged_context,
            "name": "skill_adapter",
        }
        out["messages"] = [system_msg, *messages]
        return out

    if mode == "input":
        original = str(out.get("input", ""))
        out["input"] = f"{merged_context}\n\n[User Query]\n{original}\n[/User Query]"
        return out

    raise ValueError("mode must be either 'messages' or 'input'")
