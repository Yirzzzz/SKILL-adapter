from skill_adapter import SkillRuntime

runtime = SkillRuntime(skill_dirs=["./examples/skills"])

selection = runtime.route(query="请总结这篇论文", debug=True)
print("selected_skills=", selection.selected_skills)
print("candidates=", selection.candidates)
print("reason=", selection.reason)
print("fallback=", selection.fallback)
