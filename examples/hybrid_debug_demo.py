from skill_adapter import SkillConfig, SkillRuntime

runtime = SkillRuntime(
    config=SkillConfig(
        skill_dirs=["./examples/skills"],
        activation_threshold=0.15,
        retrieval_mode="bm25_bge_m3",
        bge_m3_model_name="BAAI/bge-m3",
    )
)

query = "help me route this coding request"
selection = runtime.route(query=query, debug=True)
print("selection.selected_skills=", selection.selected_skills)
print("selection.trace=", selection.trace)

prepared = runtime.prepare(
    query=query,
    payload={"messages": [{"role": "user", "content": query}]},
    mode="messages",
    debug=True,
)
print("prepared.trace=", prepared.trace)
