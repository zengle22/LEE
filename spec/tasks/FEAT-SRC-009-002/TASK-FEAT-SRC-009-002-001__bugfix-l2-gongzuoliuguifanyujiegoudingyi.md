---
id: TASK-FEAT-SRC-009-002-001
ssot_type: task
title: Bugfix L2 工作流规范与结构定义
status: frozen
version: v1
parent_id: FEAT-SRC-009-002
derived_from_ids: []
source_refs:
- FEAT-SRC-009-002#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_src_009_002_001
  identity_kind: ssot
frozen_at: '2026-03-13T00:38:12.841361'
---

# Objective

定义 Bugfix Delivery L2 工作流的正式规范，包括输入契约、L3 阶段编排、状态机和契约接口

# Description

基于 FEAT-SRC-009-002 和 ADR-008，建立 Bugfix Delivery L2 工作流的正式规范文档，明确：(1) 输入规范五字段定义 (bug_ssot_id, severity, reproduction_evidence, batch_mode, batch_approval_record)；(2)L3 阶段编排顺序 Triage→Root Cause→Fix Design→Fix Implementation→Verification→Evidence Pack；(3) 状态机定义；(4) 粒度控制规则 (默认单 bug，五同原则 batch 例外)；(5) 与上游 BUG 源和下游 Evidence Pack 的契约接口定义。输出为冻结状态的 L2 工作流定义文档。

## Acceptance Mapping
- FEAT-SRC-009-002 / AC-002-001: Bugfix L2 工作流定义文档已冻结并通过评审
- FEAT-SRC-009-002 / AC-002-002: 输入规范包含 bug_ssot_id, severity, reproduction_evidence, batch_mode, batch_approval_record 完整定义
- FEAT-SRC-009-002 / AC-002-003: L3 阶段编排顺序明确定义为 Triage → Root Cause → Fix Design → Fix Implementation → Verification → Evidence Pack
- FEAT-SRC-009-002 / AC-002-004: 粒度控制规则已集成默认规则和五同原则 batch 例外机制

## Prerequisites
- FEAT-SRC-009-002 已冻结
- ADR-008 已冻结
- TECH-FEAT-SRC-009-002-001 已创建

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- evidence_refs
- review_approval
```

## Evidence Requirements
```yaml
required_refs:
- FEAT-SRC-009-002
- ADR-008
- TECH-FEAT-SRC-009-002-001
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- spec/workflow/definitions/bugfix-delivery-l2-definition.md
- spec/workflow/schemas/bugfix-input-contract.yaml
preconditions:
- 文档未正式引用前可回滚
```

## Definition Of Done
- Bugfix L2 工作流定义文档已创建并标记为 frozen 状态
- 输入规范五字段定义完整并通过评审
- L3 阶段编排顺序明确定义并通过评审
- 状态机定义完整并通过评审
- 粒度控制规则文档化 (默认单 bug + 五同 batch 例外)
- 与上游 BUG 源和下游 Evidence Pack 的契约接口文档化
- 所有规范文档已存档至 spec/workflow/definitions/
