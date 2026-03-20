import ast

from skill_adapter.models import SkillMetadata
from skill_adapter.retrieval.bm25 import BM25Retriever
from skill_adapter.tokenizer import tokenize_text


def _skill(skill_id: str, name: str, description: str) -> SkillMetadata:
    return SkillMetadata(
        skill_id=skill_id,
        name=name,
        description=description,
        retrieval_text=f"{name}\n{description}",
        use_when=[],
        examples=[],
        path=f"/tmp/{skill_id}/SKILL.md",
    )


def _extract_matched_tokens(reason: str) -> list[str]:
    prefix = "bm25 matched_tokens="
    assert reason.startswith(prefix)
    return ast.literal_eval(reason[len(prefix) :])


def test_tokenize_text_filters_stopwords_in_weak_semantic_query() -> None:
    tokens = tokenize_text("\u4f60\u7684\u5e95\u5c42\u903b\u8f91\u662f\u4ec0\u4e48")
    assert "\u4f60" not in tokens
    assert "\u7684" not in tokens
    assert "\u4f60\u7684" not in tokens
    assert "\u4ec0\u4e48" not in tokens


def test_tokenize_text_keeps_meaningful_tokens() -> None:
    tokens = tokenize_text("\u4f60\u7684\u9876\u5c42\u8bbe\u8ba1\u662f\u4ec0\u4e48")
    assert "\u9876\u5c42" in tokens
    assert "\u8bbe\u8ba1" in tokens


def test_bm25_matched_tokens_do_not_include_stopwords() -> None:
    retriever = BM25Retriever()
    skills = [
        _skill(
            "logic-design",
            "\u67b6\u6784\u8bbe\u8ba1",
            "\u5e95\u5c42\u903b\u8f91\u4e0e\u9876\u5c42\u8bbe\u8ba1",
        ),
        _skill(
            "route-rules",
            "\u8def\u7531\u89c4\u5219",
            "\u8def\u7531\u68c0\u7d22\u4e0e\u8bed\u4e49\u5339\u914d",
        ),
    ]

    candidates = retriever.retrieve("\u4f60\u7684\u5e95\u5c42\u903b\u8f91\u662f\u4ec0\u4e48", skills, top_k=2)
    assert candidates

    for candidate in candidates:
        matched_tokens = _extract_matched_tokens(candidate.reason)
        assert "\u4f60" not in matched_tokens
        assert "\u4f60\u7684" not in matched_tokens
        assert "\u7684" not in matched_tokens
        assert "\u4ec0\u4e48" not in matched_tokens
