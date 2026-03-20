---
id: TASK-FEAT-SRC-009-001-003
ssot_type: task
title: 运行时集成与Agent/Contract绑定
status: frozen
version: v1
parent_id: FEAT-SRC-009-001
derived_from_ids: []
source_refs:
- FEAT-SRC-009-001#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_src_009_001_003
  identity_kind: ssot
frozen_at: '2026-03-13T00:06:13.735149'
---

# Objective

将L2工作流模板与运行时系统、Agent、Gate进行集成绑定

# Description

完成feature_delivery_l2模板与运行时系统的集成，包括：(1)Agent配置更新，注册feature_delivery_l2工作流；(2)Gate配置更新，确保smoke_gate和contract_freeze_gate与L2工作流正确关联；(3)运行时参数解析和传递机制实现；(4)阶段执行器绑定(tech_design_l3, feature_contract_l3等)；(5)状态持久化配置。确保L2工作流可以被运行时正确调度和执行。

## Acceptance Mapping
- FEAT-SRC-009-001 / AC-001-001: L2工作流运行时集成完成并可执行
- FEAT-SRC-009-001 / AC-001-004: 状态机运行时实现完整

## Prerequisites
- TASK-FEAT-SRC-009-001-002完成

## Dependencies
- TASK-FEAT-SRC-009-001-002

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- integration_test_results
- runtime_config_version
```

## Evidence Requirements
```yaml
required_refs:
- feature-delivery-l2-template.yaml
- integration_test_report
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/lee/orchestrator/config/
- spec-global/departments/dev/AGENTS.md
- spec-global/departments/dev/gates/
preconditions:
- 未正式启用前可回滚
```

## Definition Of Done
- Agent配置已更新，feature_delivery_l2工作流已注册
- Gate绑定配置已完成
- 运行时参数解析机制已实现
- 阶段执行器已绑定(tech_design_l3, feature_contract_l3, feature_fe_l3, feature_be_l3, feature_integration_l3, evidence_pack_l3)
- 状态持久化配置已完成
- 运行时集成测试通过
