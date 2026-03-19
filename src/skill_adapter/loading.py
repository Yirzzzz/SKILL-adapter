from pathlib import Path

from .models import SkillMetadata


class SkillLoader:
    def __init__(self) -> None:
        self.loaded_skills: list[str] = []

    def load_skill_markdown(self, metadata: SkillMetadata) -> str:
        self.loaded_skills.append(metadata.skill_id)
        p = Path(metadata.path)
        if p.is_file():
            return p.read_text(encoding="utf-8")
        return (p / "SKILL.md").read_text(encoding="utf-8")
