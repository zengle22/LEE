---
id: FEAT-SSOT-REV-002
ssot_type: feat
title: Delivery Prep 与 QA Handoff 种子视图生成
status: active
version: v1
parent_id: EPIC-127
derived_from_ids: []
source_refs:
- EPIC-127#scope
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

- EPIC-127#scope
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

## AC-SEED-01

- Scenario: delivery prep seed 生成
- Given: formal FEAT bundle 已冻结
- When: 运行 reverse delivery prep step
- Then: 生成 UI / TECH / TASK seeds，且输出只落 seed 或 handoff/index
- Trace Hints: UI, TECH, TASK

## AC-SEED-02

- Scenario: QA handoff seed 与 evidence view 生成
- Given: formal FEAT bundle 已冻结
- When: 运行 reverse QA handoff generation
- Then: 生成 TESTSET seed 与 TC / REPORT / BUG / EVI trace/evidence views，不产生 formal freeze
- Trace Hints: TESTSET, TASK, TECH
# Dependencies

- FEAT-SSOT-REV-001
# Non Goals

- 不直接 freeze UI / TECH / TASK / TESTSET / TC / REPORT / BUG / EVI
- 不替代 feat-to-delivery-prep 与 qa.test-set-production 的正式职责
