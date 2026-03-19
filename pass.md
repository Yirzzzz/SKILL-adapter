# skill-adapter 项目交接说明（pass.md）

## 1. 项目初心与边界

这个项目是 **Skill Adapter SDK**，不是 Agent 框架。

核心初心：
- 给已有 chat/agent/llm 系统做“低侵入技能适配”
- 用户只需在原有模型调用前加一层 `prepare()`
- 不接管业务编排，不做工具执行，不做 workflow 平台

明确不做（MVP 范围外）：
- tool execution / MCP / orchestration
- remote registry / marketplace
- vector DB / embedding 服务依赖
- 重型框架接入（LangChain / LlamaIndex）

---

## 2. 当前版本能力（已完成）

当前版本已经完成：
1. 本地 skill 发现
2. metadata 解析
3. metadata 索引
4. query-first 检索与激活
5. selected skill lazy load
6. payload augmentation（`messages` / `input`）
7. trace/debug 输出
8. fallback（失败不阻断主流程）

当前版本核心对外 API 只有两个：
- `SkillRuntime.route(query, debug=False)`
- `SkillRuntime.prepare(query, payload, mode, debug=False)`

---

## 3. 目录约定（当前生效规则）

当前 skill 发现规则是：
- 只扫描 `skills/<sub_dir>/**/*.md`
- **不会**把 `skills/*.md` 视作 skill
- 文件名可任意（`policy.md` / `rule.md` / `x.md` 均可）
- `skill_id` 默认取 `sub_dir` 名称

示例：

```text
skills/
  anti-math/
    policy.md
  paper-summary/
    skill.zh.md
```

---

## 4. metadata 解析规则（当前实现）

### 4.1 当前可用的最小 metadata

目前已支持仅靠这两个字段：
- `name`
- `discrition`（兼容拼写错误）

也兼容标准拼写：
- `description`

可写在 YAML front matter 或正文 key-value 行。

最小示例：

```md
name: no-math
discrition: 拒绝回答数学计算、比较大小、方程求解
```

front matter 示例：

```md
---
name: no-math
discrition: 拒绝回答数学计算、比较大小、方程求解
---
```

### 4.2 parser 行为

文件：`src/skill_adapter/parser.py`
- `parse_skill_metadata_from_file()` 是主入口
- 优先读 front matter
- front matter 没有时，尝试从正文行匹配：
  - `name: ...`
  - `description: ...`
  - `discrition: ...`
- `skill_id` 默认使用 md 文件所在子目录名

---

## 5. 检索与激活（当前实现）

文件：`src/skill_adapter/retrieval/keyword.py`

当前检索实现是轻量 keyword overlap（MVP）：
- token 化 query 和 metadata 文本
- 只使用 `name + description` 两个字段参与召回评分
- 分数是归一化加权分（description 权重更高）

激活逻辑文件：`src/skill_adapter/routing.py`
- 检索得到 `top_k` candidates
- 根据 `activation_threshold` 过滤
- 取 `max_active_skills` 作为 selected
- 若无命中 => fallback

默认配置文件：`src/skill_adapter/config.py`
- `top_k=3`
- `max_active_skills=1`
- `activation_threshold=0.2`

注意：中文 query 较长时，若 metadata 太短，分数可能偏低。实践上经常需要把 `activation_threshold` 调到 `0.1~0.15`。

---

## 6. 两阶段数据流（必须遵守）

### 阶段 A：Metadata Routing

1. 发现 skill 文件（`discover_skill_files`）
2. 解析 metadata（`parse_skill_metadata_from_file`）
3. 注册到内存索引（`SkillRegistry`）
4. 用 query 做 metadata 检索+激活（`SkillRouter.route`）

这一阶段只使用 metadata，不注入全文 skill 内容。

### 阶段 B：Lazy Activation

1. 对 selected skill 才做全文读取（`SkillLoader.load_skill_markdown`）
2. 构建 augmentation context（`build_augmentation_context`）
3. 注入原 payload（`augment_payload`）
4. 输出 `PreparedPayload(payload, trace)`

失败或不适合时自动 fallback 到原始 payload。

---

## 7. 核心代码地图

### 对外入口
- `src/skill_adapter/runtime.py`
  - `SkillRuntime.route()`
  - `SkillRuntime.prepare()`

### 配置与模型
- `src/skill_adapter/config.py`（`SkillConfig`）
- `src/skill_adapter/models.py`
  - `SkillMetadata`
  - `SkillCandidate`
  - `SkillSelection`
  - `PreparedPayload`

### skill 发现/解析/索引
- `src/skill_adapter/discovery.py`
- `src/skill_adapter/parser.py`
- `src/skill_adapter/registry.py`

### 检索与激活
- `src/skill_adapter/retrieval/base.py`
- `src/skill_adapter/retrieval/keyword.py`
- `src/skill_adapter/routing.py`

### lazy load 与注入
- `src/skill_adapter/loading.py`
- `src/skill_adapter/augmentation.py`

### 示例
- `examples/route_demo.py`
- `examples/prepare_messages_demo.py`
- `examples/prepare_input_demo.py`

### 测试
- `tests/test_discovery.py`
- `tests/test_parser.py`
- `tests/test_retrieval.py`
- `tests/test_routing.py`
- `tests/test_prepare.py`

---

## 8. 常用命令

在项目根目录执行：

```bash
# 运行测试
pytest -p no:tmpdir

# 运行 route 示例
$env:PYTHONPATH='src'; python examples/route_demo.py

# 运行 prepare(messages) 示例
$env:PYTHONPATH='src'; python examples/prepare_messages_demo.py

# 运行 prepare(input) 示例
$env:PYTHONPATH='src'; python examples/prepare_input_demo.py
```

如果在 Linux/macOS：

```bash
PYTHONPATH=src python examples/route_demo.py
```

---

## 9. 已知问题与技术债

1. 当前召回是纯关键词法，语义召回能力弱
- 同义词、隐式意图、多轮上下文表现有限
- 中文 query 长句下，分数易被稀释

2. token 粒度比较粗
- 中文按单字切分（不是词级分词）
- 对短 description 可用，但可解释性和稳定性一般

3. 目前仍保留了 `discover_skill_dirs()/parse_skill_metadata(skill_dir)` 兼容函数
- 现在主流程已经走 `discover_skill_files()/parse_skill_metadata_from_file()`
- 后续可评估是否收敛并简化历史兼容入口

4. 编码风险
- parser 按 UTF-8 读取
- 若外部团队用 ANSI/GBK 保存 md，可能读出乱码

---

## 10. 下一步优化建议（按优先级）

### P0（低成本高收益）
1. 召回阈值策略优化
- 代码位置：`src/skill_adapter/routing.py`
- 建议：引入“动态阈值”或“最低候选保底策略”（例如 top1 高于极低阈值且差距明显时可激活）

2. 召回解释增强
- 代码位置：`src/skill_adapter/retrieval/keyword.py`
- 建议：在 `reason` 输出字段级命中信息（name 命中数 / description 命中数）

3. 编码兜底
- 代码位置：`src/skill_adapter/parser.py`
- 建议：UTF-8 失败时尝试 GBK，避免业务方本地保存编码导致不可用

### P1（中期）
4. 检索器可插拔升级（embedding）
- 代码位置：`src/skill_adapter/retrieval/base.py`, `runtime.py`
- 做法：新增 `EmbeddingRetriever`，保持 `BaseRetriever` 接口不变
- 目标：在不改 `route()/prepare()` API 的前提下替换检索能力

5. metadata schema 显式校验
- 代码位置：`parser.py` / `models.py`
- 建议：增加轻量验证，缺失核心字段时给出可观测 warning（而不是静默）

### P2（可选）
6. trace 标准化与事件分层
- 代码位置：`runtime.py`
- 建议：新增 `trace.events`，记录 discovery_count / parsed_count / retrieved_count / selected_count / lazy_loaded

---

## 11. 如何改“skill 召回”

如果下一任负责人要改召回策略，优先改这几个点：

1. 分词/tokenizer
- 文件：`src/skill_adapter/retrieval/keyword.py`
- 函数：`_tokenize`

2. 评分公式
- 文件：`src/skill_adapter/retrieval/keyword.py`
- 函数：`retrieve`
- 当前是 name/description 加权重；可改 BM25-like、字段归一化、短语匹配等

3. 激活门槛
- 文件：`src/skill_adapter/routing.py`
- 逻辑：`score >= activation_threshold`

4. 默认参数
- 文件：`src/skill_adapter/config.py`
- 可调整 `top_k/max_active_skills/activation_threshold`

---

## 12. 如何改“扫描规则”

当前规则是 `skills/<sub_dir>/**/*.md`。

修改位置：
- `src/skill_adapter/discovery.py` 的 `discover_skill_files()`

如果要兼容更多格式（例如单文件 `skills/*.md`），只改这一个函数即可，不影响 route/prepare API。

---

## 13. 交付稳定性状态

- 单元测试：通过（当前 14 个测试）
- 主流程：可运行
- API：`route()/prepare()` 已稳定
- 失败策略：全链路 fallback 到原始 payload

---

## 14. 最后给下一任负责人的一句话

请守住项目初心：
- 这是“适配层”，不是“新框架”
- 设计目标永远是低侵入接入、稳定 fallback、可观测
- 任何优化都应优先不破坏 `route()/prepare()` 这两个核心接口

