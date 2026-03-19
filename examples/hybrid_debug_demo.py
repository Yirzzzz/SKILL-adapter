from skill_adapter import SkillRuntime

runtime = SkillRuntime(skill_dirs=["./examples/skills"])

query = "请总结这篇论文的贡献和局限"

selection = runtime.route(query=query, debug=True)
print("selection.selected_skills=", selection.selected_skills)
print("selection.trace=", selection.trace)

prepared = runtime.prepare(
    query=query,
    payload={"messages": [{"role": "user", "content": query}]},
    mode="messages",
    debug=True,
)
print("prepared.payload=", prepared.payload)
print("prepared.trace=", prepared.trace)
