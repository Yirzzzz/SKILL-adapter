from skill_adapter import SkillRuntime

runtime = SkillRuntime(skill_dirs=["./examples/skills"])

messages = [
    {"role": "user", "content": "请总结这篇论文，重点看贡献和局限"},
]
prepared = runtime.prepare(
    query="请总结这篇论文，重点看贡献和局限",
    payload={"messages": messages},
    mode="messages",
    debug=True,
)

print("prepared.payload=", prepared.payload)
print("prepared.trace=", prepared.trace)
