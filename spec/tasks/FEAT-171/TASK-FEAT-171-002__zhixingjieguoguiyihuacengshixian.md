---
id: TASK-FEAT-171-002
ssot_type: task
title: 执行结果归一化层实现
status: active
version: v1
parent_id: FEAT-171
derived_from_ids: []
source_refs:
- FEAT-171#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_171_002
  identity_kind: ssot
---

# Objective

实现结果归一化层，确保 Qwen Chat 执行结果与其他执行器格式一致

# Description

基于 TECH-FEAT-171-001 技术方案，实现结果归一化层。统一吸收 `qwen_chat` 的 `json` / `stream-json` 输出事件，归并为与其他执行器一致的执行状态、输出内容、元数据与追溯信息，并补齐日志记录功能。

## Acceptance Mapping
- FEAT-171 / AC-002: 执行结果格式与其他执行器一致，符合统一规范

## Prerequisites
- TECH-FEAT-171-001 技术方案已冻结
- TASK-FEAT-171-001 完成或接口已定义

## Dependencies
- TASK-FEAT-171-001

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
- src/lee/orchestrator/execution/runners/llm_runner.py
- src/lee/orchestrator/execution/trace.py
```

## Definition Of Done
- NormalizedExecutionResult 模型定义完成
- Qwen Chat 结果归一化适配器实现并通过测试
- 归一化结果包含完整追溯信息
- 结构化日志输出验证通过
- TASK 文件已冻结
- 代码评审通过
