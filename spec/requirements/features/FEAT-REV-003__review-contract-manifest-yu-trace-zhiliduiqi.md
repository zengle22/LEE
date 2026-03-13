---
id: FEAT-REV-003
ssot_type: feat
title: Review Contract、Manifest 与 Trace 治理对齐
status: active
version: v1
parent_id: EPIC-113
derived_from_ids: []
source_refs:
- EPIC-113#scope
owner: null
tags: []
properties:
  contract_key: feat_003
  identity_kind: ssot
---

# Goal

补齐 reverse workflow 的 review contract、manifest 和 traceability 约束，使整条 SSOT 链可审查、可追溯、可验证。
# User Value

治理审查员可以按完整 SSOT 链检查 reverse 结果，避免只审 EPIC/FEAT 导致链路失真。
# Inputs

- EPIC-113#scope
- reverse pack outputs
- review and manifest contracts
# Processing

- 扩展 review contract 到 SRC / EPIC / FEAT / seeds / views / handoff
- 生成覆盖 reverse scope 的 manifest 与 trace index
- 校验 formal / seed / view 边界与 evidence 追踪闭环
# Outputs

- full-chain review contract
- reverse scope manifest
- trace index / evidence map
- governance validation summary
# Acceptance

- review contract 能覆盖整条 reverse SSOT 链
- manifest 清晰声明 formal / seed / view / handoff 边界
- trace index 能把 repo evidence、SRC、EPIC、FEAT 与下游 seeds/views 关联起来
# Acceptance Checks

## AC-GOV-01

- Scenario: review contract 覆盖校验
- Given: reverse workflow 产出了 formal object、seeds、views 和 handoff
- When: 执行 review contract 校验
- Then: review subject_refs 覆盖 SRC / EPIC / FEAT 及其对应 seeds/views/handoff
- Trace Hints: TASK, TECH, TESTSET

## AC-GOV-02

- Scenario: manifest 与 trace index 一致性校验
- Given: manifest 和 trace index 已生成
- When: 审查 formal / seed / view / handoff 边界
- Then: manifest 分类与 trace 链接一致，且 repo evidence 可追溯到下游 seeds/views
- Trace Hints: TASK, TECH, TESTSET
# Dependencies

- FEAT-REV-002
# Non Goals

- 不引入新的治理层级或平行目录
- 不把 ADR 当成 SRC / EPIC / FEAT 的业务源对象
