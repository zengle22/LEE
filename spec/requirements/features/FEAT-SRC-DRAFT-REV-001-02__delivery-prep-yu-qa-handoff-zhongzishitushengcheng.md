---
id: FEAT-SRC-DRAFT-REV-001-02
ssot_type: feat
title: Delivery Prep 与 QA Handoff 种子视图生成
status: active
version: v1
parent_id: EPIC-078
derived_from_ids: []
source_refs:
- EPIC-078#scope
owner: null
tags: []
properties:
  contract_key: feat_002
  identity_kind: ssot
---

# Goal

在 FEAT 之后补齐 UI / TECH / TASK / TESTSET seed，以及 TC / REPORT / BUG / EVI 的 trace / evidence views 与 handoff index。
# User Value

研发与 QA 可以基于 reverse pack 获得下游准备材料，但不会越权生成新的 formal freeze 对象。
# Inputs

- EPIC-078#scope
- formal FEAT bundle
- canonical SSOT directory rules
# Processing

- 基于 FEAT 派生 delivery prep seeds
- 生成 QA handoff seeds 与 evidence / trace views
- 输出 handoff / index 而不是直接物化下游 formal object
# Outputs

- UI / TECH / TASK seeds
- TESTSET seed
- TC / REPORT / BUG / EVI evidence views
- delivery / QA handoff indexes
# Acceptance

- UI / TECH / TASK / TESTSET 仅生成 seed 级输出
- TC / REPORT / BUG / EVI 仅生成 evidence / trace view 或 handoff/index
- 下游输出路径与现行 canonical SSOT 目录保持一致
# Acceptance Checks

## AC-02-01

- Scenario: 状态变更触发快照
- Given: 工作流状态发生变更
- When: 事件发布到总线
- Then: 系统自动创建 SSOT 快照并关联版本
- Trace Hints: TASK, TESTSET, TECH

## AC-02-02

- Scenario: 快照可检索
- Given: 快照已创建
- When: 查询特定版本快照
- Then: 系统返回正确的快照内容
- Trace Hints: TASK, TESTSET, TECH

## AC-02-03

- Scenario: 回滚一致性
- Given: 状态发生回滚
- When: 恢复至前一版本
- Then: 快照版本链保持连续且一致
- Trace Hints: TASK, TESTSET, TECH
# Dependencies

- FEAT-SRC-DRAFT-REV-001-01
# Non Goals

- 不直接 freeze UI / TECH / TASK / TESTSET / TC / REPORT / BUG / EVI
- 不替代 feat-to-delivery-prep 与 qa.test-set-production 的正式职责
