import math
from collections import Counter
from typing import Dict, List

from ..models import SkillCandidate, SkillMetadata
from ..tokenizer import tokenize_text


class BM25Retriever:
    def __init__(self, *, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._doc_tokens_cache: Dict[str, List[str]] = {}

    def _tokenize_skill(self, skill: SkillMetadata) -> List[str]:
        cache_key = f"{skill.skill_id}:{skill.retrieval_text}"
        if cache_key not in self._doc_tokens_cache:
            self._doc_tokens_cache[cache_key] = tokenize_text(skill.retrieval_text)
        return self._doc_tokens_cache[cache_key]

    def retrieve(self, query: str, skills: List[SkillMetadata], top_k: int) -> List[SkillCandidate]:
        query_tokens = tokenize_text(query)
        if not query_tokens or not skills:
            return []

        corpus_tokens = [self._tokenize_skill(skill) for skill in skills]
        doc_freqs: Counter[str] = Counter()
        doc_lengths: List[int] = []
        tokenized_docs: List[Counter[str]] = []
        for doc in corpus_tokens:
            counts = Counter(doc)
            tokenized_docs.append(counts)
            doc_lengths.append(len(doc))
            doc_freqs.update(counts.keys())

        avg_doc_len = sum(doc_lengths) / max(1, len(doc_lengths))
        total_docs = len(skills)
        unique_query_tokens = list(dict.fromkeys(query_tokens))

        candidates: List[SkillCandidate] = []
        for skill, counts, doc_len in zip(skills, tokenized_docs, doc_lengths):
            score = 0.0
            matched_tokens: List[str] = []
            for token in unique_query_tokens:
                tf = counts.get(token, 0)
                if tf <= 0:
                    continue
                matched_tokens.append(token)
                doc_freq = doc_freqs.get(token, 0)
                idf = math.log(1 + (total_docs - doc_freq + 0.5) / (doc_freq + 0.5))
                denom = tf + self.k1 * (1 - self.b + self.b * doc_len / max(1.0, avg_doc_len))
                score += idf * ((tf * (self.k1 + 1)) / max(1e-9, denom))

            candidates.append(
                SkillCandidate(
                    metadata=skill,
                    score=round(score, 6),
                    bm25_score=round(score, 6),
                    reason=f"bm25 matched_tokens={matched_tokens[:8]}",
                )
            )

        candidates.sort(key=lambda item: item.bm25_score, reverse=True)
        return candidates[:top_k]
