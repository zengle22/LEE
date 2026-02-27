# Openspec Workflow - LEE Workflow Instance 实现

## 流程状态

| 阶段 | 状态 | 说明 |
|------|------|------|
| P1: 需求冻结 | ✅ 完成 | 需求文档 |
| P2: 测试契约 | ✅ 完成 | 测试用例 |
| P3: 架构设计 | ✅ 完成 | 技术提案 |
| P4: 实现方案 | ✅ 完成 | 方案评审 |
| P5: 迭代开发 | 🔄 进行中 | 核心模块实现 |
| P6: 测试验证 | ⏳ 待开始 | 单元/集成测试 |
| P7: 发布 | ⏳ 待开始 | 版本发布 |

## P5 实现清单

### 已完成

- [x] M1: Plan Agent (`src/lee/orchestrator/execution/plan_agent.py`)
  - `PlanAgent` 类
  - `PlanConfig` 配置
  - `PlanResult` 结果
  - `create_plan()` 便捷函数

- [x] M2: Instance Generator (`src/lee/orchestrator/core/instance_generator.py`)
  - `InstanceGenerator` 类
  - `InstanceMetadata` 元数据
  - 版本管理
  - 状态更新

- [x] M3: Workflow Runner (`src/lee/orchestrator/execution/workflow_runner.py`)
  - `WorkflowRunner` 控制器
  - `WorkflowRunConfig` 配置
  - `WorkflowRunResult` 结果
  - Plan → Instance → Execute 流程

- [x] M4: CLI 集成 (`src/lee/cli/commands/run.py`)
  - ✅ 添加 `--plan-only` 选项
  - ✅ 添加 `--skip-plan` 选项
  - ✅ 添加 `--plan-mode` 选项
  - ✅ 添加 `--instance` 选项

- [x] M5: 测试 (`tests/test_workflow_instance.py`)
  - ✅ 18 个测试用例全部通过

- [x] M6: Orchestrator 改造
  - ✅ `InstanceLoaderMixin` 添加到 Orchestrator
  - ✅ `get_ready_steps` 支持从 Instance 加载
  - ✅ `_check_workflow_completion` 支持 Instance

- [x] M7: Review Gate 交互
  - ✅ `ReviewGate` 模块实现
  - ✅ simple 模式自动跳过
  - ✅ suggest 模式 LLM 判断
  - ✅ force 模式强制审批（交互式）

### 核心文件清单

```
src/lee/orchestrator/
├── core/
│   ├── instance_generator.py    # ✅ 已实现
│   └── __init__.py              # ✅ 已更新
└── execution/
    ├── plan_agent.py            # ✅ 已实现
    ├── workflow_runner.py       # ✅ 已实现
    ├── instance_loader.py       # ✅ 已实现 (新)
    ├── review_gate.py           # ✅ 已实现 (新)
    └── __init__.py              # ✅ 已更新

src/lee/cli/commands/
└── run.py                       # ✅ 已更新

tests/
└── test_workflow_instance.py   # ✅ 18 tests
```

## 代码结构

```
src/lee/orchestrator/
├── core/
│   ├── instance_generator.py    # ✅ 已实现
│   └── __init__.py              # ✅ 已更新
└── execution/
    ├── plan_agent.py            # ✅ 已实现
    ├── workflow_runner.py       # ✅ 已实现
    └── __init__.py              # ✅ 已更新
```

## 使用方式

### 1. Plan Agent 单独使用

```python
from lee.orchestrator.execution.plan_agent import create_plan

# 分析模板，生成 Plan
plan_result = await create_plan(
    template=template_dict,
    params={"phase_id": "xxx"},
    config=PlanConfig(mode="suggest")
)

print(plan_result.summary)  # Plan Summary Markdown
print(plan_result.instance) # Instance YAML
```

### 2. Instance Generator 使用

```python
from lee.orchestrator.core.instance_generator import InstanceGenerator

generator = InstanceGenerator(project_root)

# 生成 Instance 文件
metadata = generator.generate(plan_result, phase_id="xxx", tier="l2")

# 加载最新版本
instance = generator.load_latest(workflow_id)

# 更新状态
generator.update_status(workflow_id, "running")
```

### 3. Workflow Runner 完整流程

```python
from lee.orchestrator.execution.workflow_runner import run_workflow

result = await run_workflow(
    workflow_key="my-workflow",
    template_path=Path("templates/my-workflow.yaml"),
    params={"phase_id": "xxx"},
    project_root=Path("."),
    plan_mode="suggest"
)

print(result.workflow_id)
print(result.plan_summary)
```

## 下一步

1. 集成到 CLI (`lee run` 命令)
2. 添加 `--plan-only` 选项
3. 实现 Review Gate 交互
4. 测试验证
