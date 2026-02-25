# QA L2/L3 Orchestrator 集成指南

## 概述

本文档描述 QA 部门 L2/L3 工作流与 Orchestrator 的集成方式。

## 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         L2 Workflow                              │
│  (template.qa.test_plan_l2)                                     │
│                                                                  │
│  Phase 1-3: 直接执行                                             │
│  ├─ test_run_init   → agent.qa.test_run_initializer             │
│  ├─ env_provision    → agent.qa.env_provisioner                  │
│  └─ env_check       → skill.env.check_tools                     │
│                                                                  │
│  Phase 4: L3 调度 (orchestrator 执行)                           │
│  └─ test_set_execution                                           │
│      ├─ p4_s1: 加载 Test Set 定义                               │
│      ├─ p4_s2: 创建 L3 实例 (spawn_workflow)                    │
│      └─ p4_s3: 执行 L3 实例 (run_until_blocked)                 │
│                                                                  │
│  Phase 5-8: L2 汇总                                             │
│  ├─ bug_summary     → agent.qa.bug_summarizer                   │
│  ├─ test_report     → agent.qa.report_generator                 │
│  ├─ exit_evaluation → agent.qa.exit_evaluator                   │
│  └─ retrospective   → agent.qa.retrospective_generator           │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ spawns
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         L3 Workflow                              │
│  (template.qa.test_set_l3)                                      │
│                                                                  │
│  Step 1: case_generation     → agent.qa.case_generator           │
│  Step 2: script_translation  → agent.qa.script_translator        │
│  Step 3: script_execution    → skill.runner.test_e2e             │
│  Step 4: behavior_compliance → skill.qa.behavior_compliance      │
│  Step 5: result_judgment     → agent.qa.result_judge             │
│  Step 6: tse_assembly        → agent.qa.tse_assembler            │
│  Step 7: bug_drafting        → agent.qa.bug_drafter              │
└─────────────────────────────────────────────────────────────────┘
```

## L3 创建逻辑

### 触发时机

L2 Phase 4 (`test_set_execution`) 执行时，Orchestrator 检测到：
- `spawns_l3: true`
- `l3_template_id: template.qa.test_set_l3`

### 创建参数

```yaml
parent_id: "<l2_workflow_id>"
level: WorkflowLevel.TASK
template_id: "template.qa.test_set_l3"
data:
  test_run_id: "<test_run_id>"
  test_set_id: "<test_set_id>"
  test_set_definition: {...}
  build_version: "<build_version>"
  build_commit: "<build_commit>"
  environment: "<environment>"
  env_check_result: {...}
  dependency_results: {...}
```

### Test Set 依赖关系

```python
# Test Set 依赖关系示例
test_sets = [
    {"id": "ts_auth", "depends_on": []},
    {"id": "ts_payment", "depends_on": ["ts_auth"]},
    {"id": "ts_checkout", "depends_on": ["ts_payment"]},
]

# 拓扑排序后的执行顺序
execution_order = ["ts_auth", "ts_payment", "ts_checkout"]

# 如果 ts_auth 失败
# → ts_payment 被标记为 skipped
# → ts_checkout 被标记为 skipped
```

## L3 输出契约

```yaml
# L3 完成后的输出数据
status: "completed"  # or failed, skipped, invalid_run
output:
  test_set_id: "ts_auth"
  tse_path: "qa/test-runs/TR-xxx/tse-ts_auth/tse.yaml"
  results_summary:
    total_cases: 30
    passed_cases: 28
    failed_cases: 2
    pass_rate: 93.3
  bug_drafts:
    - "qa/bugs/bug_ts_auth_001.yaml"
    - "qa/bugs/bug_ts_auth_002.yaml"
```

## Orchestrator 实现

### 关键方法

```python
# 在 SubworkflowMixin 中实现
async def _create_l3_for_test_set(
    self,
    l2_workflow_id: str,
    test_set_config: dict,
    context: dict,
) -> str:
    """
    为单个 Test Set 创建 L3 实例

    Returns:
        child_workflow_id: L3 实例 ID
    """
    child = await self.spawn_workflow(
        parent_id=l2_workflow_id,
        level=WorkflowLevel.TASK,
        template_id="template.qa.test_set_l3",
        data={
            "test_run_id": context["test_run_id"],
            "test_set_id": test_set_config["id"],
            "test_set_definition": test_set_config,
            "build_version": context["build_version"],
            "build_commit": context["build_commit"],
            "environment": context["environment"],
            "env_check_result": context["env_check_result"],
            "dependency_results": context.get("dependency_results", {}),
        },
    )
    return child.id


async def _execute_l3s_serial_with_dependencies(
    self,
    l2_workflow_id: str,
    test_sets: list[dict],
    context: dict,
) -> dict[str, Any]:
    """
    串行执行 L3 实例，按依赖关系排序

    Returns:
        l3_results: {test_set_id: result}
    """
    # 1. 拓扑排序
    execution_order = topological_sort(test_sets)

    # 2. 串行执行
    results = {}
    for test_set_id in execution_order:
        # 检查依赖是否失败
        if _should_skip_due_to_dependency(test_set_id, results):
            results[test_set_id] = {"status": "skipped", "skip_reason": "dependency_failed"}
            continue

        # 创建并执行 L3
        l3_id = await self._create_l3_for_test_set(l2_workflow_id, test_sets[test_set_id], context)
        await self.run_until_blocked(l3_id, max_steps=50)

        # 获取结果
        l3 = await self.store.get_workflow(l3_id)
        results[test_set_id] = l3.data.get("output", {})

    return results
```

## 待实现功能

### 1. Test Set 依赖关系定义

在 Test Set schema 中增加 `depends_on` 字段：

```yaml
# test-set schema
fields:
  - id: test_set_id
  - name
  - description
  - depends_on  # 新增：Test Set ID 列表
    type: array
    items:
      type: string
```

### 2. 拓扑排序算法

```python
def topological_sort(test_sets: list[dict]) -> list[str]:
    """根据 depends_on 进行拓扑排序"""
    # 实现拓扑排序
    # 返回可执行的顺序
    pass
```

### 3. 依赖失败跳过逻辑

```python
def should_skip_due_to_dependency(
    test_set: dict,
    results: dict[str, dict],
) -> bool:
    """检查是否因依赖失败而跳过"""
    for dep_id in test_set.get("depends_on", []):
        dep_result = results.get(dep_id, {})
        if dep_result.get("status") in ["failed", "invalid_run"]:
            return True
    return False
```

### 4. L3 输出验证

```python
def validate_l3_output(l3_output: dict) -> bool:
    """验证 L3 输出符合契约"""
    required_fields = [
        "test_set_id",
        "status",
        "tse_path",
        "results_summary",
        "bug_drafts",
    ]
    return all(field in l3_output for field in required_fields)
```

## 未来扩展：并行执行

```python
async def _execute_l3s_parallel(
    self,
    l2_workflow_id: str,
    test_sets: list[dict],
    context: dict,
) -> dict[str, Any]:
    """
    并行执行无依赖关系的 L3 实例

    使用 asyncio.gather 并行执行
    """
    # 1. 按依赖关系分组
    groups = group_by_independence(test_sets)

    # 2. 组内并行，组间串行
    results = {}
    for group in groups:
        # 并行执行组内 L3
        tasks = [
            self._create_and_run_l3(l2_workflow_id, ts, context)
            for ts in group
        ]
        group_results = await asyncio.gather(*tasks)
        results.update(group_results)

    return results
```
