from skill_adapter.models import SkillMetadata
from skill_adapter.retrieval.keyword import KeywordRetriever


def test_retrieval_hits_obvious_skill() -> None:
    retriever = KeywordRetriever()
    skills = [
        SkillMetadata(
            skill_id="paper-summary",
            name="Paper Summary",
            description="Summarize academic papers",
            use_when=["summarize paper"],
            examples=["请总结这篇论文"],
            path="/tmp/paper-summary",
        ),
        SkillMetadata(
            skill_id="code-explain",
            name="Code Explain",
            description="Explain source code",
            use_when=["explain code"],
            examples=["解释代码"],
            path="/tmp/code-explain",
        ),
    ]

    candidates = retriever.retrieve("请总结这篇论文", skills, top_k=2)
    assert candidates[0].metadata.skill_id == "paper-summary"
    assert candidates[0].score >= candidates[1].score
