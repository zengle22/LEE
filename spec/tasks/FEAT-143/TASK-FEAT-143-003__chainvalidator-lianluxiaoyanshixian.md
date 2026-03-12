---
id: TASK-FEAT-143-003
ssot_type: task
title: ChainValidator 链路校验实现
status: active
version: v1
parent_id: FEAT-143
derived_from_ids: []
source_refs:
- FEAT-143#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_143_003
  identity_kind: ssot
---

# Objective

实现 RELEASE→PLAN→TASK 执行路径的完整性校验，确保正式交付必须通过完整链路

# Description

基于 TASK-FEAT-143-001 定义的链路校验规范，实现 ChainValidator 核心组件：验证 TASK 存在性和有效性、验证 TASK 归属的 TESTPLAN、验证 TESTPLAN 归属的 RELEASE、执行渐进式校验并生成校验报告。支持自动补全模式下推导缺失的 plan_ref/release_ref。

## Acceptance Mapping
- FEAT-143 / AC-003-002: 实现 RELEASE→PLAN→TASK 链路完整性校验逻辑

## Prerequisites
- TASK-FEAT-143-001

## Dependencies
- {'task_id': 'TASK-FEAT-143-001', 'relationship': 'implements'}
- {'task_id': 'TASK-FEAT-143-002', 'relationship': 'uses'}

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- test_results
- performance_metrics
```

## Evidence Requirements
```yaml
required_refs:
- TASK-FEAT-143-001
- FTA-FEAT-143-001
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/lee/orchestrator/execution/entry/chain_validator.py
preconditions:
- 确保有回滚前的代码版本
```

## Definition Of Done
- ChainValidator 核心逻辑实现完成
- 三级引用完整性校验通过单元测试
- 链路断裂场景（缺失 PLAN/RELEASE/不匹配）正确检测
- 错误代码 ERR-CHAIN-001/002/003 正确返回
- 自动补全逻辑实现完成
- 参数冲突检测实现完成
- 代码通过静态分析和类型检查
