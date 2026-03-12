---
id: TASK-FEAT-161-001
ssot_type: task
title: Trace测试器-链路追溯与覆盖率
status: frozen
version: v1
parent_id: FEAT-161
derived_from_ids: []
source_refs:
- FEAT-161#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_161_001
  identity_kind: ssot
frozen_at: '2026-03-12T21:40:15.381445'
---

# Objective

实现需求链纵向追溯完整性验证，检测孤儿/断链/循环引用，计算覆盖率

# Description

构建需求链图谱(DAG)，实现四层链路完整性验证、孤儿节点检测、断链检测、循环引用检测算法，计算EPIC层和FEAT层覆盖率

## Acceptance Mapping
- FEAT-161 / AC-003-001: 完整链路追溯验证
- FEAT-161 / AC-003-002: 孤儿节点检测
- FEAT-161 / AC-003-003: 循环引用检测
- FEAT-161 / AC-003-004: 覆盖率计算

## Dependencies
- TASK-FEAT-159-001
- TASK-FEAT-160-001

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
- FEAT-161
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/chain_testing/testers/trace_tester
```

## Definition Of Done
- 需求链图谱构建实现
- 四种检测算法实现并验证
- 覆盖率计算准确
- TASK文件已冻结
