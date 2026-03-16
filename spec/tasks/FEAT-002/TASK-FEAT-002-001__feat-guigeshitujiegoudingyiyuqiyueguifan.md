---
id: TASK-FEAT-002-001
ssot_type: task
title: FEAT 规格视图结构定义与契约规范
status: frozen
version: v1
parent_id: FEAT-002
derived_from_ids: []
source_refs:
- FEAT-002#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_002_001
  identity_kind: ssot
frozen_at: '2026-03-13T00:29:17.514567'
---

# Objective

定义 FEAT 规格视图的 SSOT 结构、契约边界和状态机规则

# Description

基于 ADR-008 的三轴 SSOT 模型，定义 FEAT 规格视图的正式结构：
- 明确 FEAT 规格视图在需求轴→交付轴映射中的位置
- 定义规格视图的 YAML frontmatter schema
- 定义规格视图的状态机（draft → active → frozen）
- 定义与上游 EPIC/SRC 和下游 TECH 的引用关系

## Acceptance Mapping
- FEAT-002 / AC-002-001: FEAT 规格视图结构定义文档完成并通过评审
- FEAT-002 / AC-002-003: 规格视图状态机定义完整

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
- ADR-008
- FEAT-SRC-009-002
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- spec/requirements/features/FEAT-002
```

## Definition Of Done
- TASK 文件已冻结
- SSOT schema 通过 ADR-008 合规性审查
- 状态机定义被 downstream runtime 任务引用
