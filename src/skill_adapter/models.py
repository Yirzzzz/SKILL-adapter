from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SkillMetadata:
    skill_id: str
    name: str
    description: str
    retrieval_text: str
    use_when: List[str]
    examples: List[str]
    path: str


@dataclass
class SkillCandidate:
    metadata: SkillMetadata
    score: float
    reason: str
    bm25_score: float = 0.0
    semantic_score: float = 0.0
    final_score: float = 0.0


@dataclass
class SkillSelection:
    selected_skills: List[Dict[str, Any]]
    candidates: List[Dict[str, Any]]
    reason: Optional[str]
    fallback: bool
    trace: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PreparedPayload:
    payload: Dict[str, Any]
    trace: Dict[str, Any]
