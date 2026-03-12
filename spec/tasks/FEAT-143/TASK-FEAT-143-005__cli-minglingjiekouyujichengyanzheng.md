---
id: TASK-FEAT-143-005
ssot_type: task
title: CLI 命令接口与集成验证
status: active
version: v1
parent_id: FEAT-143
derived_from_ids: []
source_refs:
- FEAT-143#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_143_005
  identity_kind: ssot
---

# Objective

实现 lee qa execute CLI 命令接口，集成所有核心组件，完成端到端验证

# Description

基于冻结的 UI 原型，实现 lee qa execute CLI 命令：支持 --task-ref/--plan-ref/--release-ref 参数、实现 5 阶段反馈模型的 CLI 输出、实现错误代码体系（ERR-ENTRY/CHAIN/BYPASS）、支持 --validate-only 和 --json 模式、集成 Entry Router/Chain Validator/Audit Logger 完成完整执行流程。编写端到端测试覆盖所有 AC。

## Acceptance Mapping
- FEAT-143 / AC-003-001: CLI 实现入口唯一性验证：仅当 task_ref 有效且归属 testplan 时才接受执行请求
- FEAT-143 / AC-003-002: CLI 实现链路完整性校验：验证 release_ref->testplan_ref->task_ref 链路完整且有效
- FEAT-143 / AC-003-003: CLI 实现旁路阻断：拒绝绕过 TESTPLAN/TASK 的请求并返回 ERR-BYPASS-001
- FEAT-143 / AC-003-004: CLI 实现审计查询：支持查询执行入口审计日志

## Prerequisites
- TASK-FEAT-143-002
- TASK-FEAT-143-003
- TASK-FEAT-143-004

## Dependencies
- {'task_id': 'TASK-FEAT-143-002', 'relationship': 'integrates'}
- {'task_id': 'TASK-FEAT-143-003', 'relationship': 'integrates'}
- {'task_id': 'TASK-FEAT-143-004', 'relationship': 'integrates'}

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- e2e_test_results
- cli_output_samples
```

## Evidence Requirements
```yaml
required_refs:
- TASK-FEAT-143-002
- TASK-FEAT-143-003
- TASK-FEAT-143-004
review_required: true
e2e_test_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/lee/cli/qa/
- src/lee/qa/execute.py
```

## Definition Of Done
- lee qa execute 命令实现完成
- CLI 5 阶段反馈模型输出实现完成
- 错误代码体系（ERR-ENTRY/CHAIN/BYPASS）正确返回
- --validate-only 和 --json 模式支持完成
- 端到端测试覆盖全部 4 个 AC
- 与 FEAT-QA-SSOT-001 的 Repository 集成完成
- CLI 帮助文档和示例更新完成
- 所有 exit codes (0-5) 正确实现
