from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class SkillMetadata:
    skill_id: str
    name: str
    description: str
    use_when: List[str]
    examples: List[str]
    path: str


@dataclass
class SkillCandidate:
    metadata: SkillMetadata
    score: float
    reason: str


@dataclass
class SkillSelection:
    selected_skills: List[Dict[str, Any]]
    candidates: List[Dict[str, Any]]
    reason: Optional[str]
    fallback: bool


@dataclass
class PreparedPayload:
    payload: Dict[str, Any]
    trace: Dict[str, Any]
