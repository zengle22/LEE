---
id: TASK-FEAT-SRC-009-002-005
ssot_type: task
title: 验证测试与文档治理
status: frozen
version: v1
parent_id: FEAT-SRC-009-002
derived_from_ids: []
source_refs:
- FEAT-SRC-009-002#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_src_009_002_005
  identity_kind: ssot
frozen_at: '2026-03-13T00:38:12.888299'
---

# Objective

为 Bugfix L2 工作流创建验证测试用例集，并更新相关文档以封禁旧入口

# Description

为 Bugfix Delivery L2 工作流创建完整的验证测试和文档治理：(1) 创建测试用例验证 L2 模板结构和阶段编排；(2) 创建测试用例验证粒度控制策略 (单 bug 模式和 batch 模式)；(3) 创建测试用例验证状态机流转；(4) 创建测试用例验证与上游 BUG 源和下游 Evidence Pack 的契约接口；(5) 更新 README.md 封禁旧的 bug-fix-l3-template 入口；(6) 更新 WORKFLOWS.md 将 Bugfix Delivery L2 列为唯一推荐入口；(7) 将旧的 bug-fix-l3-template 标记为 deprecated。

## Acceptance Mapping
- FEAT-SRC-009-002 / AC-002-001: Bugfix L2 工作流通过验证测试
- FEAT-SRC-009-002 / AC-002-002: 输入规范通过测试验证
- FEAT-SRC-009-002 / AC-002-003: 阶段编排和状态机通过测试验证
- FEAT-SRC-009-002 / AC-002-004: 粒度控制规则通过测试验证

## Prerequisites
- TASK-FEAT-SRC-009-002-002 完成
- TASK-FEAT-SRC-009-002-003 完成
- TASK-FEAT-SRC-009-002-004 完成

## Dependencies
- TASK-FEAT-SRC-009-002-002
- TASK-FEAT-SRC-009-002-003
- TASK-FEAT-SRC-009-002-004

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- changed_files
- test_results
- test_coverage
- documentation_updates
```

## Evidence Requirements
```yaml
required_refs:
- tests/workflow/test_bugfix_delivery_l2.py
- spec-global/departments/dev/README.md
- spec-global/WORKFLOWS.md
- spec-global/departments/dev/workflows/templates/bug-fix-l3-template.yaml
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- tests/workflow/test_bugfix_delivery_l2.py
- spec-global/departments/dev/README.md
- spec-global/WORKFLOWS.md
preconditions:
- 文档更新未正式发布前可回滚
```

## Definition Of Done
- 测试用例集已创建 (test_bugfix_delivery_l2.py)
- L2 模板结构验证测试通过
- 阶段编排验证测试通过
- 粒度控制策略测试通过 (单 bug 模式、五同 batch 模式、以及审批例外 batch 模式)
- 状态机流转测试通过
- 契约接口验证测试通过
- README.md 已更新封禁旧的 bug-fix-l3-template 入口
- WORKFLOWS.md 已更新将 Bugfix Delivery L2 列为唯一推荐入口
- 旧的 bug-fix-l3-template.yaml 已标记为 deprecated
