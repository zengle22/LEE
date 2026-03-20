---
id: TASK-FEAT-SRC-009-004-001
ssot_type: task
title: Evidence Pack Schema 结构定义
status: frozen
version: v1
parent_id: FEAT-SRC-009-004
derived_from_ids: []
source_refs:
- FEAT-SRC-009-004#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_src_009_004_001
  identity_kind: ssot
frozen_at: '2026-03-13T00:47:10.122599'
---

# Objective

设计 Evidence Pack 作为证据轴正式收口对象的 Schema 定义

# Description

基于三轴 SSOT 模型，定义 Evidence Pack 的完整 Schema 结构，包含必需证据类型、字段定义、验证规则，确保所有交付可审计、可追踪

## Acceptance Mapping
- FEAT-SRC-009-004 / AC-004-001: Evidence Pack Schema 文档已冻结
- FEAT-SRC-009-004 / AC-004-002: Schema 包含完整的证据类型定义，覆盖代码、测试报告、评审记录、部署记录四类

## Prerequisites
- FEAT-SRC-009-003 TECH Schema 冻结

## Dependencies
- TASK-FEAT-SRC-009-003-001

## Observability
```yaml
execution_unit: task
log_scope: evidence-pack-schema-design
audit_fields:
- run_id
- changed_files
- schema_version
- evidence_refs
```

## Evidence Requirements
```yaml
required_refs:
- FEAT-SRC-009-004
- ADR-008
- TECH-SRC-009-004
review_required: true
review_checklist:
- Schema 字段完整性
- 证据类型覆盖度
- 与三轴模型对齐性
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- spec-global/departments/dev/contracts/evidence-pack/v1/schema.json
```

## Definition Of Done
- Evidence Pack JSON Schema 已创建并冻结于 spec-global/departments/dev/contracts/evidence-pack/v1/
- Schema 包含完整的证据类型定义（代码 diff、测试报告、评审记录、部署记录、集成报告）
- Schema 包含形式化字段（formal_ssot_id、source_refs、governing_adrs、delivery_outputs、verification_results）
- Schema 通过 JSON Schema 验证器校验
- Schema 评审通过并标记 frozen 状态
