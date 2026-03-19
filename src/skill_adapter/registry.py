from dataclasses import dataclass
from typing import Dict, List

from .discovery import discover_skill_files
from .models import SkillMetadata
from .parser import parse_skill_metadata_from_file


@dataclass
class SkillRegistry:
    skills: Dict[str, SkillMetadata]

    @classmethod
    def build(cls, skill_dirs: List[str]) -> "SkillRegistry":
        items: Dict[str, SkillMetadata] = {}
        for skill_file in discover_skill_files(skill_dirs):
            try:
                metadata = parse_skill_metadata_from_file(skill_file)
            except Exception:
                continue
            items[metadata.skill_id] = metadata
        return cls(skills=items)

    def list_metadata(self) -> List[SkillMetadata]:
        return list(self.skills.values())

    def get(self, skill_id: str) -> SkillMetadata:
        return self.skills[skill_id]
