# skill-adapter API Reference

本文档整理当前 `skill-adapter` 项目里对用户可用的接口、参数和返回结构。

适用范围：
- 当前 public API
- `SkillConfig` 可调参数
- `route()` / `prepare()` 返回结构
- trace 字段说明

不包含：
- 内部实现细节
- retrieval 模块内部类的二次开发接口约定
- augmentation 内部实现说明

## 1. 对外可用接口

当前对外导出定义见 [src/skill_adapter/__init__.py](/Users/yirz/PyCharmProject/SKILL-adapter/src/skill_adapter/__init__.py)：

```python
from skill_adapter import SkillRuntime, SkillConfig, SkillSelection, PreparedPayload
```

推荐用户只依赖以下两个核心入口：
- `SkillRuntime.route()`
- `SkillRuntime.prepare()`

## 2. SkillRuntime

实现位置：
- [src/skill_adapter/runtime.py](/Users/yirz/PyCharmProject/SKILL-adapter/src/skill_adapter/runtime.py)

### 2.1 初始化

```python
from skill_adapter import SkillRuntime

runtime = SkillRuntime(skill_dirs=["./skills"])
```

或：

```python
from skill_adapter import SkillRuntime, SkillConfig

config = SkillConfig(skill_dirs=["./skills"])
runtime = SkillRuntime(config=config)
```

### 2.2 构造参数

`SkillRuntime.__init__(skill_dirs=None, *, config=None)`

参数说明：

- `skill_dirs: Optional[List[str]]`
  - skill 根目录列表
  - 当不传 `config` 时必填
  - SDK 会扫描 `skills/<subdir>/**/*.md`

- `config: Optional[SkillConfig]`
  - 自定义配置对象
  - 如果传入，则优先使用该配置

行为说明：

- 如果只传 `skill_dirs`，内部会自动构造 `SkillConfig`
- 如果 `config is None` 且 `skill_dirs is None`，会抛出 `ValueError`
- runtime 初始化时会完成：
  - metadata discovery
  - metadata parsing
  - registry build
  - hybrid retriever 初始化

## 3. route()

### 3.1 方法签名

```python
selection = runtime.route(query: str, debug: bool | None = None)
```

### 3.2 参数说明

- `query: str`
  - 当前用户查询
  - retrieval/routing 的唯一输入

- `debug: Optional[bool]`
  - 当前版本下主要用于控制调用意图
  - route 会始终返回完整 `trace`
  - 传 `debug=True` 是推荐调用方式，便于排障和观察路由结果

### 3.3 返回值

返回 `SkillSelection`。

结构定义见 [src/skill_adapter/models.py](/Users/yirz/PyCharmProject/SKILL-adapter/src/skill_adapter/models.py)：

```python
@dataclass
class SkillSelection:
    selected_skills: List[Dict[str, Any]]
    candidates: List[Dict[str, Any]]
    reason: Optional[str]
    fallback: bool
    trace: Dict[str, Any]
```

### 3.4 返回字段说明

- `selected_skills`
  - 最终选中的 skill 列表
  - 当前通常受 `max_active_skills` 限制
  - 元素示例：

```python
{"skill": "paper-summary", "score": 2.015}
```

- `candidates`
  - 融合排序后的候选 skill
  - 元素示例：

```python
{
  "skill": "paper-summary",
  "score": 2.015,
  "bm25_score": 3.12,
  "semantic_score": 0.91,
  "reason": "hybrid fusion raw_bm25=3.12 raw_semantic=0.91"
}
```

- `reason`
  - 路由结果说明
  - 例如：
    - `paper-summary has the highest fused score`
    - `no candidate passed activation threshold`

- `fallback`
  - 是否进入 fallback
  - `True` 表示没有选中 skill，主流程应继续使用原始 payload

- `trace`
  - 详细调试信息
  - 见后文 trace 章节

### 3.5 route() 示例

```python
selection = runtime.route(query="请总结这篇论文的贡献和局限", debug=True)

print(selection.selected_skills)
print(selection.candidates)
print(selection.reason)
print(selection.fallback)
print(selection.trace)
```

## 4. prepare()

### 4.1 方法签名

```python
prepared = runtime.prepare(
    query: str,
    payload: Dict[str, Any],
    mode: str,
    debug: bool | None = None,
)
```

### 4.2 参数说明

- `query: str`
  - 用于 routing 的查询文本

- `payload: Dict[str, Any]`
  - 原始模型请求载荷
  - SDK 会在其副本上做 augmentation
  - 不会原地修改传入对象

- `mode: str`
  - 当前支持：
    - `"messages"`
    - `"input"`

- `debug: Optional[bool]`
  - 含义与 `route()` 一致

### 4.3 返回值

返回 `PreparedPayload`。

结构定义见 [src/skill_adapter/models.py](/Users/yirz/PyCharmProject/SKILL-adapter/src/skill_adapter/models.py)：

```python
@dataclass
class PreparedPayload:
    payload: Dict[str, Any]
    trace: Dict[str, Any]
```

### 4.4 返回字段说明

- `payload`
  - 增强后的请求载荷
  - 如果 fallback，则等于原始 payload 的拷贝

- `trace`
  - route 阶段 trace + prepare 阶段状态
  - 会额外带上：
    - `loaded`
    - `mode`

### 4.5 prepare() 示例

`messages` 模式：

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

`input` 模式：

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

## 5. SkillConfig

实现位置：
- [src/skill_adapter/config.py](/Users/yirz/PyCharmProject/SKILL-adapter/src/skill_adapter/config.py)

### 5.1 定义

```python
@dataclass
class SkillConfig:
    skill_dirs: List[str]
    top_k: int = 3
    bm25_top_k: int = 5
    semantic_top_k: int = 5
    max_active_skills: int = 1
    activation_threshold: float = 0.35
    bm25_weight: float = 0.5
    semantic_weight: float = 0.5
    embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    enable_semantic_retrieval: bool = True
    enable_bm25_retrieval: bool = True
    debug: bool = False
```

### 5.2 参数详解

#### 基础参数

- `skill_dirs: List[str]`
  - skill 根目录列表
  - 必填
  - 不能为空

- `debug: bool = False`
  - 默认 debug 标志
  - 当前不会改变 public return shape，但建议调试期设为 `True`

#### 候选召回参数

- `top_k: int = 3`
  - 最终融合排序后保留多少候选
  - 影响 `route().candidates` 和后续激活候选池大小

- `bm25_top_k: int = 5`
  - BM25 召回的候选数

- `semantic_top_k: int = 5`
  - 语义召回的候选数

建议：
- skill 很少时，`bm25_top_k` 和 `semantic_top_k` 可以略大于 `top_k`
- 如果技能数量增加，先调大这两个参数，再观察 fused candidates

#### 激活参数

- `max_active_skills: int = 1`
  - 最多激活多少个 skill
  - 当前默认只激活 1 个

- `activation_threshold: float = 0.35`
  - 最终 `final_score` 的激活阈值
  - 小于该值则 fallback

说明：
- 当前 `final_score` 使用原始分数加权：

```python
final_score = bm25_weight * bm25_score + semantic_weight * semantic_score
```

- 因为 BM25 分值通常大于 semantic cosine 分值，`activation_threshold` 需要结合你的语料观察后调整

#### 融合参数

- `bm25_weight: float = 0.5`
  - BM25 原始分数权重

- `semantic_weight: float = 0.5`
  - semantic 原始分数权重

说明：
- 两个权重都必须 `>= 0`
- 不能同时为 `0`
- 当前不是归一化融合，而是 raw score 融合

建议：
- 如果你更相信关键词精确命中，可提高 `bm25_weight`
- 如果你更希望放大语义泛化能力，可提高 `semantic_weight`
- 但需要注意两路分数的量纲不同，调参时应结合 trace 观察

#### 检索开关

- `enable_semantic_retrieval: bool = True`
  - 是否启用语义召回

- `enable_bm25_retrieval: bool = True`
  - 是否启用 BM25 召回

说明：
- 两者可以单独开关
- 至少应开启一路，否则路由没有意义

#### Embedding 参数

- `embedding_model_name: str`
  - 默认值：

```python
"sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
```

用途：
- 指定本地 sentence embedding 模型名称
- 仅在 `enable_semantic_retrieval=True` 时生效

### 5.3 校验规则

`SkillConfig` 当前有这些校验：

- `skill_dirs` 不能为空
- `top_k > 0`
- `bm25_top_k > 0`
- `semantic_top_k > 0`
- `max_active_skills > 0`
- `activation_threshold` 必须在 `[0, 1]`
- `bm25_weight >= 0`
- `semantic_weight >= 0`
- `bm25_weight` 和 `semantic_weight` 不能同时为 `0`

### 5.4 SkillConfig 示例

```python
from skill_adapter import SkillConfig

config = SkillConfig(
    skill_dirs=["./skills"],
    top_k=5,
    bm25_top_k=8,
    semantic_top_k=8,
    max_active_skills=1,
    activation_threshold=0.6,
    bm25_weight=0.7,
    semantic_weight=0.3,
    embedding_model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    enable_semantic_retrieval=True,
    enable_bm25_retrieval=True,
    debug=True,
)
```

## 6. trace 字段说明

当前 `route()` / `prepare()` 返回的 trace 重点字段如下：

```python
{
  "query": "请总结这篇论文",
  "bm25_candidates": [
    {"skill": "paper-summary", "score": 3.12, "reason": "..."}
  ],
  "semantic_candidates": [
    {"skill": "paper-summary", "score": 0.91, "reason": "..."}
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
  "selected_skills": [
    {"skill": "paper-summary", "score": 2.015}
  ],
  "activation_threshold": 0.35,
  "fallback": False,
  "loaded": True,
  "mode": "messages",
  "reason": "paper-summary has the highest fused score",
  "registry_errors": [],
  "retrieval_errors": []
}
```

字段说明：

- `query`
  - 当前路由 query

- `bm25_candidates`
  - BM25 路召回候选

- `semantic_candidates`
  - 语义路召回候选

- `fused_candidates`
  - 融合后的排序候选
  - `final_score` 为当前真实激活依据

- `selected_skills`
  - 最终选中的 skill

- `activation_threshold`
  - 当前激活阈值

- `fallback`
  - 是否 fallback

- `loaded`
  - 是否发生 lazy load
  - 仅 `prepare()` trace 中有意义

- `mode`
  - 当前 prepare 模式
  - 仅 `prepare()` trace 中有意义

- `reason`
  - 最终决策原因

- `registry_errors`
  - skill parse/build 阶段失败信息

- `retrieval_errors`
  - retrieval 阶段错误信息
  - 例如 semantic model 不可用

## 7. 推荐使用方式

### 最简接入

```python
from skill_adapter import SkillRuntime

runtime = SkillRuntime(skill_dirs=["./skills"])
prepared = runtime.prepare(
    query="请总结这篇论文",
    payload={"messages": [{"role": "user", "content": "请总结这篇论文"}]},
    mode="messages",
    debug=True,
)
```

### 需要调参时

```python
from skill_adapter import SkillRuntime, SkillConfig

config = SkillConfig(
    skill_dirs=["./skills"],
    bm25_weight=0.7,
    semantic_weight=0.3,
    activation_threshold=0.5,
    bm25_top_k=8,
    semantic_top_k=8,
)
runtime = SkillRuntime(config=config)
```

### 先看路由，再决定是否 prepare

```python
selection = runtime.route(query="解释这个仓库架构", debug=True)
if not selection.fallback:
    prepared = runtime.prepare(
        query="解释这个仓库架构",
        payload={"messages": [{"role": "user", "content": "解释这个仓库架构"}]},
        mode="messages",
        debug=True,
    )
```

## 8. 当前 public API 边界

建议用户稳定依赖：
- `SkillRuntime`
- `SkillConfig`
- `SkillSelection`
- `PreparedPayload`

不建议把这些内部模块当成稳定 public API：
- `skill_adapter.retrieval.*`
- `skill_adapter.tokenizer`
- `skill_adapter.registry`
- `skill_adapter.parser`
- `skill_adapter.routing`

原因：
- 这些模块当前更适合作为内部实现层
- 后续可能继续演进，而不保证兼容性承诺

## 9. 当前已知注意点

- 当前 hybrid fusion 使用 raw score 加权，不是归一化加权
- BM25 和 semantic 分数的量纲不同，阈值和权重需要结合 trace 调参
- metadata routing 当前仍坚持两阶段设计：
  - routing 阶段只基于 metadata
  - 只有 selected skill 才会 lazy load 完整 `SKILL.md`
- 推荐 skill metadata 至少具备：
  - `name`
  - `description`

