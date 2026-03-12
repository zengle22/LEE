---
id: TASK-FEAT-SRC-009-001-004
ssot_type: task
title: 验证测试与文档治理
status: frozen
version: v1
parent_id: FEAT-SRC-009-001
derived_from_ids: []
source_refs:
- FEAT-SRC-009-001#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_src_009_001_004
  identity_kind: ssot
frozen_at: '2026-03-13T00:06:13.746310'
---

# Objective

完成L2工作流的验证测试，更新相关文档，标记旧路径deprecated

# Description

验证TASK-FEAT-SRC-009-001-003完成的运行时集成，包括：(1)L2工作流端到端测试；(2)阶段编排顺序验证；(3)状态机流转验证；(4)输入契约验证；(5)更新README/WORKFLOWS文档，明确feature_delivery_l2为新主入口；(6)标记phase-openspec-flow为deprecated；(7)验证Evidence Pack生成完整性。确保L2工作流可稳定运行并正确收口到证据轴。

## Acceptance Mapping
- FEAT-SRC-009-001 / AC-001-001: L2工作流验证测试通过，文档已更新
- FEAT-SRC-009-001 / AC-001-002: 输入规范验证测试通过
- FEAT-SRC-009-001 / AC-001-003: L3阶段编排验证测试通过
- FEAT-SRC-009-001 / AC-001-004: 状态机验证测试通过

## Prerequisites
- TASK-FEAT-SRC-009-001-003完成

## Dependencies
- TASK-FEAT-SRC-009-001-003

## Observability
```yaml
execution_unit: task
log_scope: task-execution
audit_fields:
- run_id
- test_results
- evidence_pack_refs
- doc_changes
```

## Evidence Requirements
```yaml
required_refs:
- e2e-test-report
- evidence-pack-sample
- updated-documentation
review_required: true
```

## Rollback Strategy
```yaml
mode: manual
restore_targets:
- spec-global/departments/dev/README.md
- spec-global/WORKFLOWS.md
preconditions:
- 文档备份已创建
```

## Definition Of Done
- L2工作流端到端测试通过
- 阶段编排顺序验证通过(Contract→Backend→Frontend→Integration→Evidence Pack)
- 状态机流转验证通过(Ready→In Progress→Evidence Pack Produced→Closed)
- 输入契约验证通过(formal_ssot_id, source_refs, governing_adrs, repo_context)
- README/WORKFLOWS文档已更新，明确feature_delivery_l2为新主入口
- phase-openspec-flow已标记为deprecated
- Evidence Pack生成验证通过
- 所有AC可验证
