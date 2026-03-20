---
id: TASK-FEAT-162-001
ssot_type: task
title: Semantic测试器-语义一致性验证
status: frozen
version: v1
parent_id: FEAT-162
derived_from_ids: []
source_refs:
- FEAT-162#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_162_001
  identity_kind: ssot
frozen_at: '2026-03-12T21:40:15.391172'
---

# Objective

实现相邻层间语义相似度计算与关键词覆盖验证

# Description

集成预训练语言模型(sentence-transformers)提取语义向量，计算余弦相似度，提取核心关键词并验证子节点覆盖，支持分层级阈值配置

## Acceptance Mapping
- FEAT-162 / AC-004-001: 语义相似度计算
- FEAT-162 / AC-004-002: 语义漂移检测
- FEAT-162 / AC-004-003: 关键词覆盖验证
- FEAT-162 / AC-004-004: 分层级阈值配置

## Dependencies
- TASK-FEAT-159-001
- TASK-FEAT-161-001

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
- FEAT-162
review_required: true
```

## Rollback Strategy
```yaml
mode: revert
restore_targets:
- src/chain_testing/testers/semantic_tester
```

## Definition Of Done
- 语义向量提取集成完成
- 相似度计算与评分映射实现
- 关键词提取与覆盖验证实现
- API降级方案就绪
- TASK文件已冻结
