# PM Agent 处理流程说明

> **作者**: LEE Team
> **日期**: 2026-02-21
> **版本**: v1.0.0
> **分类**: 流程文档

## 🎯 你的理解是正确的！

**PM Agent 的处理流程是**:

1. **用户输入** → `lee chat`
2. **Intent Classifier** → 识别意图（使用规则 + LLM fallback）
3. **Param Mapper** → 提取参数（**两层机制**）
4. **API Wrapper** → 调用对应的 Orchestrator API
5. **返回结果** → 显示给用户

---

## 📊 详细处理流程

### 步骤 1: 意图分类 (Intent Classifier)

**文件**: `src/lee/orchestrator/execution/pm_agent/intent_classifier.py`

```python
async def classify(self, user_input: str) -> Intent:
    # 1. 先尝试规则匹配 (快速路径)
    rule_match = self._try_rule_based_classification(user_input)
    if rule_match:
        return rule_match

    # 2. 规则不匹配，调用 LLM fallback
    llm_intent = await self._classify_with_llm(user_input)
    return llm_intent
```

**匹配规则**:
- "运行|run|执行" + 模板ID → `RUN_WORKFLOW`
- "继续|continue" + 工作流ID → `EXECUTE_STEP` (next_step)
- "批准|approve" + 网关ID → `APPROVE_GATE`
- "状态|status" → `GET_STATE`
- 等等...

---

### 步骤 2: 参数提取 (Param Mapper) - **两层机制**

**文件**: `src/lee/orchestrator/execution/pm_agent/param_mapper.py`

#### 第一层: 规则提取 (快速路径，~1ms)

```python
async def map_params(self, user_input: str, intent: Intent, context):
    # 1. 先尝试规则提取
    rule_based_params = self._try_rule_based_extraction(user_input, intent.type)
    if rule_based_params:
        logger.info("Rule-based parameter extraction successful")
        return rule_based_params  # ✅ 直接返回，不调用 LLM

    # 2. 规则不匹配，调用 LLM
    # ...
```

**规则提取模式**:
- **Workflow ID**: `r'(?:继续|continue)(?:工作流|workflow)?\s*(wf_[a-z0-9_]+)'`
- **Template ID**: `r'(?:运行|run)(?:工作流|workflow)?\s*([a-z][a-z0-9_.-]+\.[a-z]+)'`
- **Gate ID**: `r'(?:批准|approve)\s*(gate_[a-z0-9_]+)'`
- 等等...

**覆盖的常见模式**:
- "继续工作流wf_task_123" → workflow_id = "wf_task_123"
- "运行 step_generate_code" → step_id = "step_generate_code"
- "批准 gate_review" → gate_id = "gate_review"
- "在当前目录运行office.workspace-cleanup" → template_id = "office.workspace-cleanup"

#### 第二层: LLM 提取 (语义理解，~600ms)

如果规则提取失败，调用 LLM:

```python
# 1. 发现可用的工作流
workflows = await self._discover_workflows()

# 2. 构建提示词
system_prompt = self._build_extraction_system_prompt(intent.type, workflow_summary)

# 3. 调用 LLM
result = await self._extract_with_llm(
    user_input,
    system_prompt,
    context_info,
    intent
)

# 4. 验证和归一化参数
params = self._validate_and_normalize_params(result, workflows, intent.type)

return params
```

**LLM 提取的提示词包含**:
- 可用的工作流列表
- 工作流的步骤信息
- 当前的对话上下文
- 提取参数的格式要求

---

### 步骤 3: API 调用

**文件**: `src/lee/orchestrator/execution/pm_agent/api_wrapper.py`

根据决策结果调用对应的 Orchestrator API:

```python
async def execute(self, decision: Decision, context):
    action = decision.action

    if action == "run_workflow":
        return await self._handle_run_workflow(decision, context)
    elif action == "next_step":
        return await self._handle_next_step(decision, context)
    elif action == "approve_gate":
        return await self._handle_approve_gate(decision, context)
    # ... 等等

    # 每个 handler 都调用对应的 Orchestrator API
```

---

## 🎯 总结：两层机制

### 意图分类 (Intent Classifier)

1. **规则匹配** (快速)
   - 正则表达式匹配常见模式
   - 覆盖 ~80% 的常见输入

2. **LLM Fallback** (慢速但智能)
   - 处理复杂或不常见的输入
   - 理解语义和上下文

### 参数提取 (Param Mapper)

1. **规则提取** (快速，~1ms)
   - 正则表达式提取常见参数
   - 覆盖 ~80% 的常见场景
   - 例如: "继续工作流wf_task_123"

2. **LLM 提取** (慢速但智能，~600ms)
   - 处理复杂或不常见的输入
   - 理解模糊的描述
   - 例如: "我想运行那个清理工作空间的任务"

---

## ✅ 你的理解完全正确！

**PM Agent 的处理流程**:

```
用户输入: "在当前目录运行office.workspace-cleanup"
    ↓
Intent Classifier (规则匹配)
    ↓
识别意图: RUN_WORKFLOW ✅
    ↓
Param Mapper (规则提取)
    ↓
提取参数: template_id = "office.workspace-cleanup" ✅
    ↓
API Wrapper
    ↓
调用: api_create_workflow() + api_run_until_blocked()
    ↓
返回结果
```

**如果用户说**: "我想运行清理工作空间的任务"

```
用户输入: "我想运行清理工作空间的任务"
    ↓
Intent Classifier (规则不匹配)
    ↓
LLM Fallback
    ↓
识别意图: RUN_WORKFLOW ✅ (理解语义)
    ↓
Param Mapper (规则提取失败)
    ↓
LLM 提取
    ↓
提取参数: template_id = "office.workspace-cleanup" ✅ (理解模糊描述)
    ↓
API Wrapper
    ↓
调用: api_create_workflow() + api_run_until_blocked()
    ↓
返回结果
```

---

## 📊 性能优化

**规则匹配的优势**:
- ⚡ 快速: ~1ms vs ~600ms
- 🎯 准确: 对于常见模式，100% 准确
- 💰 便宜: 无需调用 LLM API

**LLM Fallback 的优势**:
- 🧠 智能: 理解语义和上下文
- 🔄 灵活: 处理各种复杂场景
- 📈 可学习: 可以通过改进提示词提升效果

**两层机制结合**:
- ✅ 80% 的请求使用快速路径 (规则)
- ✅ 20% 的请求使用智能路径 (LLM)
- ✅ 整体性能优秀
- ✅ 用户体验良好

---

**结论**: 你的理解是正确的！PM Agent 使用两层机制：规则匹配（快速）+ LLM fallback（智能），而不是单纯依赖正则表达式。
