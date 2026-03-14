---
id: TASK-FEAT-064-002
ssot_type: task
title: source_freeze 运行时与 gate 接线实现
status: frozen
version: v1
parent_id: FEAT-064
derived_from_ids: []
source_refs:
- FEAT-064#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_064_002
  identity_kind: ssot
workflow_instance_id: wf_task_adr016_cleanup
frozen_at: '2026-03-14T13:36:00'
---

# Objective

实现 source_freeze 与 gate 间的运行时接线，确保冻结结果可被后续阶段稳定消费

# Description

在现有 orchestrator 主线中补齐并验证源冻结的运行时接线：
- `source_freeze` 输出能够稳定传入 `frozen_inputs`
- gate 可以提取主冻结载荷并保留 `workspace_artifacts` 路径
- 并发作用域和路径 token 能从 `source_freeze` 身份中解析
- `qwen3.5-plus` 标准化能力与 product workflow 模板保持一致

## Acceptance Mapping
- FEAT-064 / AC-001: 执行器调用 source_freeze 步骤后生成包含工件列表的执行报告
- FEAT-064 / AC-002: 工件清单生成延迟小于 1 秒
- EPIC-064 / Scope-001: 实现 source_freeze 执行步骤逻辑
- EPIC-064 / Scope-004: 集成 qwen3.5-plus 模型进行标准化处理

## Prerequisites
- TASK-FEAT-064-001

## Dependencies
- src/lee/orchestrator/execution/gate_operations.py
- src/lee/orchestrator/execution/concurrency_scope.py
- src/lee/orchestrator/execution/state_machine.py
- config/llm_config.yaml
- tests/orchestrator/test_l2_l3_workflow_p1_p2.py

## Observability
```yaml
execution_unit: task
log_scope: task-runtime
audit_fields:
- run_id
- task_id
- changed_files
- test_results
- workspace_artifacts
```

## Evidence Requirements
```yaml
required_refs:
- FEAT-064
- TASK-FEAT-064-001
- src/lee/orchestrator/execution/gate_operations.py
- src/lee/orchestrator/execution/concurrency_scope.py
- tests/orchestrator/test_l2_l3_workflow_p1_p2.py
- tests/test_run_spec_governance.py
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/lee/orchestrator/execution/gate_operations.py
- src/lee/orchestrator/execution/concurrency_scope.py
- src/lee/orchestrator/execution/state_machine.py
- config/llm_config.yaml
- tests/orchestrator/test_l2_l3_workflow_p1_p2.py
```

## Definition Of Done
- TASK 文件已冻结并写入 spec/tasks/FEAT-064/
- `source_freeze -> frozen_inputs -> gate` 的主链路有实现与测试证据
- `workspace_artifacts` 路径对齐 `output/design-frozen/`
- 并发作用域可从 `source_freeze` 标识或路径稳定推导
- `qwen3.5-plus` 配置仍为标准化处理的可用模型
