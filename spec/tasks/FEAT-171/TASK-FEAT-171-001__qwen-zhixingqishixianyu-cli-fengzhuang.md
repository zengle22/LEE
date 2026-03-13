---
id: TASK-FEAT-171-001
ssot_type: task
title: Qwen 执行器实现与 CLI 封装
status: active
version: v1
parent_id: FEAT-171
derived_from_ids: []
source_refs:
- FEAT-171#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_171_001
  identity_kind: ssot
---

# Objective

实现 Qwen 执行器适配层，封装 qwen CLI 无头调用并兼容现有执行器接口

# Description

基于 TECH-FEAT-171-001 技术方案，实现 `qwen` 执行器适配层。封装 `qwen -p/--prompt` 无头调用和 `--output-format json|stream-json` 输出模式，兼容现有执行器接口，处理超时控制、流式输出捕获、错误码映射与会话恢复语义。

## Acceptance Mapping
- FEAT-171 / AC-001: Runner 能接收 qwen 实例并执行，任务被执行并返回结果

## Prerequisites
- TECH-FEAT-171-001 技术方案已冻结

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- test_coverage
- evidence_refs
```

## Evidence Requirements
```yaml
required_refs:
- TECH-FEAT-171-001
review_required: true
test_coverage_threshold: 80
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/lee/orchestrator/execution/executors.py
- src/lee/orchestrator/execution/llm_executor.py
- src/lee/runtime/executor/profiles/loader.py
```

## Definition Of Done
- Qwen 执行器适配层实现完成并通过单元测试
- 无头调用封装层通过契约测试
- 超时控制与取消机制验证通过
- `json` 与 `stream-json` 两种输出模式行为已验证
- TASK 文件已冻结
- 代码评审通过
