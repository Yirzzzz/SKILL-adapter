import re
from typing import List, Set

from ..models import SkillCandidate, SkillMetadata
from .base import BaseRetriever

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


def _tokenize(text: str) -> Set[str]:
    return {token.lower() for token in _TOKEN_PATTERN.findall(text or "")}


class KeywordRetriever(BaseRetriever):
    def retrieve(self, query: str, skills: List[SkillMetadata], top_k: int) -> List[SkillCandidate]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        candidates: List[SkillCandidate] = []
        for meta in skills:
            name_tokens = _tokenize(meta.name)
            description_tokens = _tokenize(meta.description)
            overlap_name = query_tokens.intersection(name_tokens)
            overlap_desc = query_tokens.intersection(description_tokens)

            # Query-first retrieval over only two metadata fields: name + description.
            name_base = max(1, min(len(query_tokens), len(name_tokens)))
            desc_base = max(1, min(len(query_tokens), len(description_tokens)))
            name_score = len(overlap_name) / name_base
            desc_score = len(overlap_desc) / desc_base
            score = min(1.0, 0.3 * name_score + 0.7 * desc_score)

            overlaps = sorted(overlap_desc | overlap_name)
            reason = f"matched_tokens={overlaps[:8]}"
            candidates.append(SkillCandidate(metadata=meta, score=round(score, 4), reason=reason))

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[:top_k]

