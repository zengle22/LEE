---
id: TASK-FEAT-012-003-002
ssot_type: task
title: Kimi 执行器运行时集成验证
status: frozen
version: v1
parent_id: FEAT-012-003
derived_from_ids: []
source_refs:
- FEAT-012-003#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_012_003_002
  identity_kind: ssot
frozen_at: '2026-03-12T22:50:57.198832'
---

# Objective

验证 Kimi CLI 执行器走 code runner 接线、复用 workflow wiring，并完成日志追踪集成

# Description

验证 Kimi CLI 执行器通过统一工厂创建后，参考 `ClaudeCodeRunner` 所在执行链路接入 code step 调度，复用 workflow wiring 进行流程编排，执行输出被正确捕获并记录到日志和追踪系统中，确保执行链路一致性，且不走 LangGraph/LLM profile 路径

## Acceptance Mapping
- FEAT-012-003 / AC-012-003-03: Kimi 进入与 `claude_code` 同类的 code runner/executor 轨道，而不是 LangGraph/LLM profile 轨道
- FEAT-012-003 / AC-012-003-04: 复用相同 workflow wiring，步骤模板无需修改
- FEAT-012-003 / AC-012-003-05: 执行器输出被正确捕获并记录到日志和追踪系统

## Prerequisites
- TASK-FEAT-012-003-001

## Dependencies
- TASK-FEAT-012-003-001

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- test_results
- evidence_refs
```

## Evidence Requirements
```yaml
required_refs:
- FEAT-012-003
- TECH-FEAT-012-003
- TESTSET-FEAT-012-003
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/lee/orchestrator/execution/runners/llm_runner.py
- tests/integration/test_kimi_executor_runtime.py
```

## Definition Of Done
- Code runner 接线验证测试通过，确认不走 LangGraph/LLM profile 路径
- Workflow wiring 复用验证测试通过，确认步骤模板无需修改
- 日志与追踪集成测试通过，确认输出正确捕获
- 端到端集成测试通过
- TASK 文件已冻结
