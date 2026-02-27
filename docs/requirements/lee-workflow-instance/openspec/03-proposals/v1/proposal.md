# 技术提案 - LEE Workflow Instance

## 实现方案

### 架构设计

```
lee run <workflow_key>
       │
       ▼
┌─────────────────────────────────────┐
│ 1. Load + Render Template          │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ 2. LLM Plan                        │
│    - agent.core.planner             │
│    - 输出: Instance + Summary        │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ 3. Plan Review Gate (Human)        │
│    - simple/suggest/force          │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ 4. Generate Instance                │
│    - instances/l2/l3/              │
│    - 版本号管理                      │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ 5. Orchestrator Execute            │
│    - 从 Instance 加载              │
│    - 状态持久化                    │
└─────────────────────────────────────┘
```

## 模块设计

### M1: Plan Agent

```python
# src/lee/orchestrator/execution/plan_agent.py
class PlanAgent:
    def __init__(self, llm_executor):
        self.llm = llm_executor

    async def plan(self, template: dict, params: dict) -> PlanResult:
        # 1. 分析模板
        # 2. 生成拆分决策
        # 3. 评估复杂度
        # 4. 返回 Instance + Summary
```

### M2: Instance Generator

```python
# src/lee/orchestrator/core/instance_generator.py
class InstanceGenerator:
    def generate(self, plan_result: PlanResult, version: int) -> Path:
        # 1. 构建 Instance YAML
        # 2. 保存到文件
        # 3. 返回路径
```

### M3: Orchestrator 改造

```python
# 改动点：
# 1. create_workflow - 改为从 Instance 加载
# 2. run_step - 从 Instance 读取步骤
# 3. 状态持久化 - 更新 Instance 文件
```

## 文件变更

| 文件 | 操作 |
|------|------|
| `src/lee/orchestrator/execution/plan_agent.py` | 新增 |
| `src/lee/orchestrator/core/instance_generator.py` | 新增 |
| `src/lee/orchestrator/execution/orchestrator.py` | 改造 |
| `src/lee/cli/commands/run.py` | 改造 |
| `config/instance_schema.yaml` | 新增 |

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| Plan 失败率高 | 换 LLM 重试机制 |
| Instance 版本混乱 | 自动版本管理 |
| 性能影响 | Plan 可选跳过 |
