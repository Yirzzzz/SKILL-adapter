from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List


@dataclass
class SkillConfig:
    skill_dirs: List[str]
    top_k: int = 3
    max_active_skills: int = 1
    activation_threshold: float = 0.2
    debug: bool = False

    def __post_init__(self) -> None:
        if not self.skill_dirs:
            raise ValueError("skill_dirs must not be empty")
        if self.top_k <= 0:
            raise ValueError("top_k must be > 0")
        if self.max_active_skills <= 0:
            raise ValueError("max_active_skills must be > 0")
        if not 0 <= self.activation_threshold <= 1:
            raise ValueError("activation_threshold must be in [0, 1]")

    @classmethod
    def from_dirs(cls, skill_dirs: Iterable[str], **kwargs: object) -> "SkillConfig":
        normalized = [str(Path(p)) for p in skill_dirs]
        return cls(skill_dirs=normalized, **kwargs)
