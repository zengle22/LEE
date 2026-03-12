---
id: TASK-FEAT-SRC-009-001-002
ssot_type: task
title: L2工作流模板实现
status: frozen
version: v1
parent_id: FEAT-SRC-009-001
derived_from_ids: []
source_refs:
- FEAT-SRC-009-001#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_src_009_001_002
  identity_kind: ssot
frozen_at: '2026-03-13T00:06:13.724684'
---

# Objective

将L2工作流规范实现为可执行的workflow模板

# Description

基于TASK-FEAT-SRC-009-001-001定义的规范，实现template.dev.feature_delivery_l2工作流模板，包括：(1)模板YAML结构定义；(2)阶段编排逻辑实现；(3)输入参数绑定；(4)阶段间数据传递机制；(5)状态转换钩子定义。模板必须支持TECH→Contract→FE/BE→Integration→Evidence顺序编排，并阻止绕过TECH或证据收口的路径。

## Acceptance Mapping
- FEAT-SRC-009-001 / AC-001-001: L2工作流模板实现并通过验证
- FEAT-SRC-009-001 / AC-001-003: 模板正确实现Contract→Backend→Frontend→Integration→Evidence Pack阶段编排

## Prerequisites
- TASK-FEAT-SRC-009-001-001完成

## Dependencies
- TASK-FEAT-SRC-009-001-001

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- validation_results
- template_version
```

## Evidence Requirements
```yaml
required_refs:
- spec/workflow/definitions/feature-delivery-l2-definition.md
- feature-delivery-l2-template.yaml
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- spec-global/departments/dev/workflows/templates/
preconditions:
- 模板未正式发布前可回滚
```

## Definition Of Done
- feature-delivery-l2-template.yaml模板文件已创建
- 模板包含完整的阶段编排定义(tech_design→contract_design→frontend_dev→backend_dev→integration→evidence_pack→smoke_gate)
- 输入参数绑定完整(formal_ssot_id, source_refs, governing_adrs, repo_context)
- 阶段间数据传递机制已定义
- 状态转换钩子已配置
- 模板通过语法和结构验证
