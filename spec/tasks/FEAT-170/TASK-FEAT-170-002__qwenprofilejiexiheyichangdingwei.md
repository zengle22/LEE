---
id: TASK-FEAT-170-002
ssot_type: task
title: Qwen Profile 解析与异常定位
status: active
version: v1
parent_id: FEAT-170
derived_from_ids: []
source_refs:
- FEAT-170#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_170_002
  identity_kind: ssot
---

# Objective

补齐 qwen profile 解析、缺失配置报错和工厂回归测试

# Description

基于 TECH-FEAT-170-001，完善 `qwen` profile 的解析优先级、缺失 profile 时的错误提示，以及工厂层的回归测试，确保实例化失败时能快速定位到配置问题，而不是在 workflow 深处报错。

## Acceptance Mapping
- FEAT-170 / AC-001: 工厂创建 qwen 实例
- FEAT-170 / AC-002: 实例化失败时返回可定位错误

## Prerequisites
- TECH-FEAT-170-001 技术方案已冻结
- TASK-FEAT-170-001 完成或接口已定义

## Dependencies
- TASK-FEAT-170-001

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- evidence_refs
```

## Evidence Requirements
```yaml
required_refs:
- TECH-FEAT-170-001
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/lee/runtime/executor/profiles/loader.py
- src/lee/orchestrator/execution/tests/
```

## Definition Of Done
- `qwen` profile 缺失时返回包含候选 profile 的错误信息
- profile 解析优先级有测试覆盖
- 工厂实例化异常可在日志中定位
- TASK 文件已冻结

