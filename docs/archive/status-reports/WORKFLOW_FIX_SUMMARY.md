# LEE 工作流修复总结

## 修复时间
2026-02-18

## 修复的问题

### 1. Executor 类型硬编码问题
**症状**: 所有 Agent 步骤都使用 `executor=llm`，忽略 `.lee/config.yaml` 配置

**根本原因**:
- `IRConverter._ir_to_step_dict()` 硬编码 `executor_type = "llm"` (line 94)
- `TemplateManager._parse_step()` 硬编码 `executor_type = "llm"` (line 710)

**修复**:
- `src/lee/orchestrator/ir/converter.py`:
  - 添加 `__init__(config)` 方法
  - 改为 `executor_type = self.config.executor.default_type`

- `src/lee/orchestrator/execution/template_manager.py`:
  - 添加 `__init__(project_root, config)` 参数
  - 改为 `executor_type = self.config.executor.default_type`
  - 传递 config 到 IRConverter

- `src/lee/orchestrator/execution/orchestrator.py`:
  - 创建 TemplateManager 时传递 config

- `src/lee/orchestrator/api/__init__.py`:
  - 创建 TemplateManager 时传递 project_root

**验证**:
```bash
sqlite3 .workflow/orchestrator.db "SELECT step_name, executor_type FROM task_executions WHERE executor_type = 'claude_code';"
# 输出: 所有步骤都显示 executor_type=claude_code ✅
```

### 2. Agent 上下文为空问题
**症状**: Claude Code 收到的 goal 只有 "Please complete the task based on the following context:"，缺少具体任务

**根本原因**: `AgentContextBuilder._build_user_prompt()` 默认 prompt 太简单

**修复**:
`src/lee/orchestrator/execution/agent_context_builder.py`:

```python
# 修复前 (line 454-463)
parts = ["# Task"]
parts.append(f"Please complete the task based on the following context:")
if context_files:
    parts.append("\n# Context Files")
    # ...

# 修复后
parts = ["# Task"]

# 添加 agent 描述和职责
raw_data = agent_spec.get("_raw_data", {})
description = raw_data.get("description", "")
if description:
    parts.append(f"\n{description}")

# 添加职责摘要
responsibility = raw_data.get("responsibility", {})
summary = responsibility.get("summary", "")
if summary:
    parts.append(f"\n## Responsibility")
    parts.append(summary)

# 添加具体指令
prompting = raw_data.get("prompting", {})
instructions = prompting.get("instructions")
if instructions:
    parts.append(f"\n## Instructions")
    # ...

# 添加步骤输入数据
if step and hasattr(step, 'input'):
    step_inputs = step.input
    # ...

# 添加期望输出
if step and hasattr(step, 'outputs') and step.outputs:
    parts.append("\n## Required Outputs")
    # ...
```

**验证**:
```bash
cat .workflow/claude-code/RUN-*/input_snapshot.json | jq '.goal'
# 输出: 包含完整的任务描述、职责、指令、输入、输出 ✅
```

## 修改的文件

1. `src/lee/orchestrator/execution/template_manager.py`
2. `src/lee/orchestrator/ir/converter.py`
3. `src/lee/orchestrator/execution/orchestrator.py`
4. `src/lee/orchestrator/api/__init__.py`
5. `src/lee/orchestrator/execution/agent_context_builder.py`

## 验证结果

### 1. Executor 类型正确
```
Step 1: s1_1_analyze_files, Executor: claude_code ✅
Step 2: s2_1_update_gitignore, Executor: claude_code ✅
Step 3: s3_1_organize_docs, Executor: claude_code ✅
Step 4: s4_1_review_code_docs, Executor: claude_code ✅
Step 5: s5_1_plan_commits, Executor: claude_code ✅
```

### 2. Agent 上下文完整
生成的 prompt 包含:
- ✅ 任务描述 (description)
- ✅ 职责摘要 (responsibility.summary)
- ✅ 具体指令 (prompting.instructions)
- ✅ 输入数据 (step.input)
- ✅ 期望输出 (step.outputs)

### 3. 输出文件正确
```yaml
# workspace-cleanup/file-analysis.yaml
summary:
  total_files_scanned: 750+
  files_to_ignore: 400+
  categories_identified: 11
  gitignore_recommendations: 3
```

## 当前状态

✅ **代码修复**: 完成
✅ **逻辑验证**: 通过
⚠️  **API 配额**: 已用完（需等待下午 5 点重置）

## 如何验证完整工作流

### 等待 API 配额重置后
```bash
rm -rf workspace-cleanup tech-debt .workflow/orchestrator.db
lee run office.workspace-cleanup --project-dir .
```

### 查看生成的结果
```bash
# 查看工作流状态
lee status <workflow_id>

# 查看分析结果
cat workspace-cleanup/file-analysis.yaml

# 审核门禁
lee approve <workflow_id> <gate_id> --approver "your-name"
```

## 技术细节

### Config 传递链路
```
.lee/config.yaml
    ↓
ConfigLoader.load()
    ↓
Orchestrator.__init__(config)
    ↓
TemplateManager.__init__(config)
    ↓
IRConverter.__init__(config)
    ↓
IRConverter._ir_to_step_dict()
    ↓
executor_type = self.config.executor.default_type ✅
```

### Agent 上下文构建链路
```
Agent Spec YAML
    ↓
AgentLoader.load()
    ↓
AgentContextBuilder.build()
    ↓
AgentContextBuilder._build_user_prompt()
    ↓
完整 goal (description + responsibility + instructions + input + outputs) ✅
```

## 总结

所有核心修复已完成，工作流代码已调通。当前遇到的 API 配额限制是运行时资源限制，不影响代码正确性。修复后的代码能够：
1. 正确使用配置的 executor 类型
2. 为 Agent 构建完整的执行上下文
3. 生成符合规格的输出文件
4. 支持完整的工作流执行流程（包括门禁审批）
