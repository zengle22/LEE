---
id: TASK-FEAT-SRC-009-004-002
ssot_type: task
title: Evidence Pack 模板与目录结构实现
status: frozen
version: v1
parent_id: FEAT-SRC-009-004
derived_from_ids: []
source_refs:
- FEAT-SRC-009-004#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_src_009_004_002
  identity_kind: ssot
frozen_at: '2026-03-13T00:47:10.137310'
---

# Objective

创建 Evidence Pack 的标准化模板和目录结构

# Description

基于 Schema 定义，实现 Evidence Pack 的物理目录结构模板、示例文件、打包规范，确保所有交付物可正确组织和归档

## Acceptance Mapping
- FEAT-SRC-009-004 / AC-004-002: 必需证据清单覆盖代码、测试报告、评审记录、部署记录四类证据
- FEAT-SRC-009-004 / AC-004-005: 示例 Evidence Pack 模板提供

## Prerequisites
- TASK-FEAT-SRC-009-004-001 Schema 冻结

## Observability
```yaml
execution_unit: task
log_scope: evidence-pack-template
audit_fields:
- run_id
- changed_files
- template_path
- evidence_refs
```

## Evidence Requirements
```yaml
required_refs:
- FEAT-SRC-009-004
- TASK-FEAT-SRC-009-004-001
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- spec-global/departments/dev/templates/evidence-pack/
```

## Definition Of Done
- Evidence Pack 目录结构模板已创建于 spec-global/departments/dev/templates/evidence-pack/
- 模板包含子目录：code-diff/、test-reports/、review-records/、deployment-records/、integration-report/
- 每个子目录包含 README 说明和占位示例
- Evidence Pack 元数据文件（evidence-manifest.yaml）模板已创建
- 打包脚本或规范文档已提供
