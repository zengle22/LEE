---
id: TASK-FEAT-SRC-009-008-004
ssot_type: task
title: IntegrationReporter 与 Evidence Pack 交接规范
status: frozen
version: v1
parent_id: FEAT-SRC-009-008
derived_from_ids: []
source_refs:
- FEAT-SRC-009-008#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_src_009_008_004
  identity_kind: ssot
frozen_at: '2026-03-13T00:53:51.852867'
---

# Objective

定义集成报告发布器和与 Evidence Pack 的交接规范

# Description

基于 Frozen 技术架构，定义 IntegrationReporter 的报告内容（执行摘要、失败用例详情、结构性问题标识、环境信息、追溯链接）、输出格式、与 Evidence Pack 的交接条件（报告评审通过、structural issue 已解决、覆盖率阈值满足）、交接物清单

## Acceptance Mapping
- FEAT-SRC-009-008 / AC-008-003: 完成标准可量化 - 报告包含覆盖率摘要
- FEAT-SRC-009-008 / AC-008-004: 交接规则完整性 - 明确定义与 Evidence Pack 的交接条件

## Prerequisites
- TASK-FEAT-SRC-009-008-001
- TASK-FEAT-SRC-009-008-003

## Dependencies
- FROZEN-ARCH-FEAT-SRC-009-008
- ADR-008

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- evidence_refs
- handoff_refs
```

## Evidence Requirements
```yaml
required_refs:
- FROZEN-ARCH-FEAT-SRC-009-008
- ADR-008
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- spec/tasks/FEAT-SRC-009-008/TASK-FEAT-SRC-009-008-004.md
```

## Definition Of Done
- IntegrationReporter 规范已冻结
- 报告内容模板定义完成
- 与 Evidence Pack 交接条件清晰
- 交接物清单文档化（4 项）
