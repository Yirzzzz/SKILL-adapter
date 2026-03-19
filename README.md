# SKILL-adapter 🧩

![image-20260320000755640](./assets/image-20260320000755640.png)

## 这是什么 ✨

`skill-adapter` 是一个 **query-first routing + payload preparation** 的适配层 SDK。你不需要迁移到新框架，只需要在现有 `client.xxx.create(...)` 调用前多包一层 `prepare()`。



## 为什么需要它 🤔

很多已有 chat/agent/llm 项目没有 skill 机制，出现可用性高的 SKILL 难以一键复用，并且直接改框架成本也极高。

因此，`skill-adapter` 提供了一个快速复用 SKILL 的能力，它只做两件事：

- `route(query)`: 基于技能 metadata （name & discription）做检索召回 （BM25 关键词召回 + sentence embedding 语义召回）；
- `prepare(query, payload, mode)`: 选中 skill 后 lazy load `SKILL.md`，再把 augmentation 注入原始请求载荷；

- 保持你现有的模型调用方式
- 通过最小代码改动加上 skill 能力
- skill 失效时自动 fallback 到原始 payload，不阻断主流程



## 快速部署 🔧

```bash
git clone https://github.com/Yirzzzz/SKILL-adapter.git
cd SKILL-adapter
pip install -e .
```



## 1 分钟接入示例 🚀

```python
# 原来代码
response = client.chat.completions.create(
    model='Qwen/Qwen3-8B', # ModelScope Model-Id, required
    messages=[
        {
          'role': 'user',
          'content': '9.9和9.11谁大'
        }
    ],
    stream=True,
    extra_body=extra_body
)

# 接入后代码
from skill_adapter import SkillRuntime

runtime = SkillRuntime(skill_dirs=["./skills"]) # 定义skills路径

prepared = runtime.prepare(
    query="9.9和9.11谁大",
    payload={"messages": [{"role": "user", "content": "9.9和9.11谁大"}]},
    mode="messages",
    debug=True,
)

response = client.chat.completions.create(
    model="Qwen/Qwen3-8B",
    **prepared.payload,
    stream=True,
    extra_body=extra_body
)
```



## route 示例 🛣️

通过该代码可以查看 SKILL 检索召回的结果

```python
selection = runtime.route(query="请总结这篇论文", debug=True)
print(selection.selected_skills)
print(selection.candidates)
print(selection.reason)
```

除此之外，项目提供一个基于 `FastAPI` 的本地 web 可视化页面， 🌐，用于观察：

- query 调整后的召回变化
- BM25 候选、semantic 候选、fused ranking
- raw score / final score
- 最终 selected skill
- prepare 后 payload
- trace / registry errors / retrieval errors

运行方式：

```bash
pip install -e ".[viz]"
uvicorn examples.retrieval_web.app:app --reload --port 8000
```

然后访问：

```text
http://127.0.0.1:8000
```

页面支持：
- 修改 query
- 调整 `top_k` / `bm25_top_k` / `semantic_top_k`
- 调整 `activation_threshold`
- 调整 `bm25_weight` / `semantic_weight`
- 开关 BM25 / semantic retrieval
- 查看 selected skill 的全文预览
- 对比 `route()` 与 `prepare()` 的 trace



## prepare(messages) 示例 💬

```python
prepared = runtime.prepare(
    query="解释这段代码",
    payload={"messages": [{"role": "user", "content": "解释这段代码"}]},
    mode="messages",
    debug=True,
)

response = client.chat.completions.create(
    model="Qwen/Qwen3-8B",
    **prepared.payload,
)
```

## prepare(input) 示例 📝

```python
prepared = runtime.prepare(
    query="你好，介绍一下你自己",
    payload={"input": "你好，介绍一下你自己"},
    mode="input",
    debug=True,
)

response = client.responses.create(
    model="gpt-5",
    **prepared.payload,
)
```

## trace/debug 示例 🧪

```python
{
  "query": "请总结这篇论文",
  "bm25_candidates": [
    {"skill": "paper-summary", "score": 3.12, "reason": "bm25 matched_tokens=['论', '论文']"}
  ],
  "semantic_candidates": [
    {"skill": "paper-summary", "score": 0.91, "reason": "semantic similarity on retrieval_text"}
  ],
  "fused_candidates": [
    {
      "skill": "paper-summary",
      "bm25_score": 3.12,
      "semantic_score": 0.91,
      "final_score": 2.015,
      "reason": "hybrid fusion raw_bm25=3.12 raw_semantic=0.91"
    }
  ],
  "selected_skills": [{"skill": "paper-summary", "score": 2.015}],
  "activation_threshold": 0.35,
  "fallback": False,
  "loaded": True,
  "mode": "messages",
  "reason": "paper-summary has the highest fused score"
}
```

如果语义模型不可用，系统不会打断主流程，而是记录在 trace 里：

```python
{
  "retrieval_errors": [
    "semantic retrieval unavailable: sentence-transformers is required for semantic retrieval"
  ]
}
```



## 项目结构与模块说明 🏗️

```text
skill-adapter/
  README.md
  pyproject.toml
  src/skill_adapter/
    __init__.py
    runtime.py          # 对外核心：route + prepare
    config.py           # SkillConfig
    models.py           # 数据结构
    discovery.py        # 本地 skill 目录扫描
    parser.py           # SKILL.md metadata 解析
    registry.py         # metadata 索引
    tokenizer.py        # 中英混合轻量 tokenizer
    routing.py          # hybrid retrieval + activation
    loading.py          # lazy load selected skills
    augmentation.py     # payload 增强
    retrieval/
      __init__.py
      base.py
      bm25.py           # BM25 检索
      semantic.py       # embedding 语义检索
      hybrid.py         # 融合排序
  examples/
    route_demo.py
    hybrid_debug_demo.py
    prepare_messages_demo.py
    prepare_input_demo.py
    skills/
      paper-summary/SKILL.md
      web-summary/SKILL.md
      code-explain/SKILL.md
 
```

