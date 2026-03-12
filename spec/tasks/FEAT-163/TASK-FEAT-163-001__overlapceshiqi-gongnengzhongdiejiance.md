---
id: TASK-FEAT-163-001
ssot_type: task
title: Overlap测试器-功能重叠检测
status: frozen
version: v1
parent_id: FEAT-163
derived_from_ids: []
source_refs:
- FEAT-163#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_163_001
  identity_kind: ssot
frozen_at: '2026-03-12T21:40:15.400854'
---

# Objective

实现FEAT层与TASK层功能重叠检测与聚类分析

# Description

计算同层节点间功能相似度矩阵，识别超过阈值的相似节点对，使用HDBSCAN进行聚类分析，生成重叠关系图和合并建议

## Acceptance Mapping
- FEAT-163 / AC-005-001: 功能重叠检测
- FEAT-163 / AC-005-002: 重叠率计算
- FEAT-163 / AC-005-003: 聚类分析
- FEAT-163 / AC-005-004: 增量重叠检测

## Dependencies
- TASK-FEAT-159-001
- TASK-FEAT-162-001

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
- FEAT-163
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/chain_testing/testers/overlap_tester
```

## Definition Of Done
- 相似度矩阵计算实现
- HDBSCAN聚类集成
- 重叠关系图生成
- 增量检测优化实现
- TASK文件已冻结
