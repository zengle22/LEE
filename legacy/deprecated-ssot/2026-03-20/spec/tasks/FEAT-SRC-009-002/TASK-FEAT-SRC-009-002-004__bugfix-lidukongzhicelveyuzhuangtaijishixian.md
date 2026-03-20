---
id: TASK-FEAT-SRC-009-002-004
ssot_type: task
title: Bugfix 粒度控制策略与状态机实现
status: frozen
version: v1
parent_id: FEAT-SRC-009-002
derived_from_ids: []
source_refs:
- FEAT-SRC-009-002#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_src_009_002_004
  identity_kind: ssot
frozen_at: '2026-03-13T00:38:12.876963'
---

# Objective

实现 Bugfix 粒度控制策略引擎和状态机 runtime

# Description

基于 FEAT-SRC-009-002 和 ADR-008 的粒度控制要求，实现 Bugfix 粒度控制策略引擎，包括：(1) 默认单 bug 规则 (1 bug -> 1 bugfix workflow instance)；(2) 五同原则 batch 判断逻辑 (同模块、同根因类别、同修复策略、同验证面、同发布窗口)；(3) 五同失败后的审批例外路径 (`batch_approval_record`)；(4) batch_mode 输入参数验证；(5) 状态机实现 (INIT→TRIAGE→ROOT_CAUSE→FIX_DESIGN→FIX_IMPL→VERIFICATION→EVIDENCE_PACK→MERGE_DECISION→COMPLETED/FAILED)；(6) 状态转换条件和回滚路径定义。

## Acceptance Mapping
- FEAT-SRC-009-002 / AC-002-004: Bugfix 粒度控制规则已集成并可通过 runtime 验证
- FEAT-SRC-009-002 / AC-002-003: 状态机定义完整并可执行

## Prerequisites
- TASK-FEAT-SRC-009-002-001 完成

## Dependencies
- TASK-FEAT-SRC-009-002-001
- TASK-FEAT-SRC-009-002-002

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- policy_evaluation_results
- state_transitions
- batch_mode_decisions
```

## Evidence Requirements
```yaml
required_refs:
- src/lee/policy/granularity_evaluator.py
- src/lee/state/bugfix_state_machine.py
- tests/policy/test_granularity_evaluator.py
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/lee/policy/granularity_evaluator.py
- src/lee/state/bugfix_state_machine.py
preconditions:
- 策略引擎未正式使用前可回滚
```

## Definition Of Done
- Bugfix 粒度控制策略引擎已实现 (GranularityPolicyEvaluator)
- 默认单 bug 规则已编码为硬约束
- 五同原则 batch 判断逻辑已实现 (同模块、同根因、同策略、同验证面、同发布窗口)
- 五同失败后的审批例外路径已实现 (`batch_approval_record`)
- batch_mode 输入参数验证已实现
- 状态机 runtime 已实现并支持完整状态流转
- 状态转换条件和回滚路径已定义
- 策略引擎通过单元测试
