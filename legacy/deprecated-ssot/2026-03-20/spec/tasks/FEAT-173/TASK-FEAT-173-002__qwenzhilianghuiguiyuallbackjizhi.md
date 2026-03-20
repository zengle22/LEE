---
id: TASK-FEAT-173-002
ssot_type: task
title: Qwen 质量回归与回退机制实现
status: active
version: v1
parent_id: FEAT-173
derived_from_ids: []
source_refs:
- FEAT-173#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_173_002
  identity_kind: ssot
---

# Objective

实现 qwen 质量回归检测与备用执行器回退机制

# Description

基于 TECH-FEAT-173-001，在线路中加入 schema 校验失败、关键字段对齐率不达标时的回退逻辑，并记录原执行器、回退目标、失败原因和原始输出引用。

## Acceptance Mapping
- FEAT-173 / AC-002: 输出质量验证
- FEAT-173 / AC-004: 回退机制生效

## Prerequisites
- TECH-FEAT-173-001 技术方案已冻结
- TASK-FEAT-173-001 完成或基线数据已可用

## Dependencies
- TASK-FEAT-173-001

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- executor_type
- fallback_target
- evidence_refs
```

## Evidence Requirements
```yaml
required_refs:
- TECH-FEAT-173-001
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/lee/orchestrator/execution/runners/llm_runner.py
- src/lee/runtime/executor/profiles/loader.py
```

## Definition Of Done
- 中文质量回归检测可触发
- 失败样本能切换到备用执行器
- 回退链路有完整审计字段
- TASK 文件已冻结

