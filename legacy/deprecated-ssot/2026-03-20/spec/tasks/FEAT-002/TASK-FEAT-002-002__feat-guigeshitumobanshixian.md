---
id: TASK-FEAT-002-002
ssot_type: task
title: FEAT 规格视图模板实现
status: frozen
version: v1
parent_id: FEAT-002
derived_from_ids: []
source_refs:
- FEAT-002#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_002_002
  identity_kind: ssot
frozen_at: '2026-03-13T00:29:17.529251'
---

# Objective

实现 FEAT 规格视图的 YAML 模板和生成器

# Description

基于结构定义，实现 FEAT 规格视图的可执行模板：
- 创建 FEAT 规格视图的 checked-in workflow template
- 实现模板变量替换和上下文注入逻辑
- 支持从 EPIC/SRC 派生 FEAT 规格视图

## Acceptance Mapping
- FEAT-002 / AC-002-001: FEAT 规格视图模板可执行并生成有效输出
- FEAT-002 / AC-002-002: 模板输出包含完整的 frontmatter 和正文结构

## Prerequisites
- TASK-FEAT-002-001

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- template_version
```

## Evidence Requirements
```yaml
required_refs:
- TASK-FEAT-002-001
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- spec-global/departments/dev/workflows/templates/feat-spec-view-template.yaml
```

## Definition Of Done
- TASK 文件已冻结
- 模板通过 dry-run 验证
- 生成样例 FEAT 规格视图并通过 schema 校验
