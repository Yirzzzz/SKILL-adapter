from skill_adapter import SkillConfig, SkillRuntime

runtime = SkillRuntime(
    config=SkillConfig(
        skill_dirs=["./examples/skills"],
        activation_threshold=0.15,
        retrieval_mode="bm25_sentence",
    )
)

query = "summarize this paper"
selection = runtime.route(query=query, debug=True)
print("selected_skills=", selection.selected_skills)
print("reason=", selection.reason)
print("trace=", selection.trace)
