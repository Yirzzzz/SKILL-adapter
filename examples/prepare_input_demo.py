from skill_adapter import SkillRuntime

runtime = SkillRuntime(skill_dirs=["./examples/skills"])

prepared = runtime.prepare(
    query="你好，介绍一下你自己",
    payload={"input": "你好，介绍一下你自己"},
    mode="input",
    debug=True,
)

print("prepared.payload=", prepared.payload)
print("prepared.trace=", prepared.trace)
