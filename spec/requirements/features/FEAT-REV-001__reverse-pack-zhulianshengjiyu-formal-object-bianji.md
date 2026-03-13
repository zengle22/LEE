---
id: FEAT-REV-001
ssot_type: feat
title: Reverse Pack 主链升级与 formal object 边界固化
status: active
version: v1
parent_id: EPIC-113
derived_from_ids: []
source_refs:
- EPIC-113#scope
owner: null
tags: []
properties:
  contract_key: feat_001
  identity_kind: ssot
---

# Goal

升级 core.reverse-epic-feat，使其从 repo evidence 逆向产出 SRC/EPIC/FEAT，并明确 formal object 只直物化这三类对象。
# User Value

产品和治理侧可以得到与现行 SSOT 主链一致的 reverse pack，而不是停留在 EPIC/FEAT-only 输出。
# Inputs

- EPIC-113#scope
- ADR-016 decision constraints
- repo evidence manifest
# Processing

- 解析 reverse workflow 的 repo evidence 与 ADR 约束
- 生成并串联 SRC reverse pack、EPIC、FEAT 三类 formal object
- 校验 formal object 物化边界仅覆盖 SRC / EPIC / FEAT
# Outputs

- SRC reverse pack
- EPIC formal object
- FEAT formal object bundle
- formal object boundary report
# Acceptance

- reverse workflow 能完整产出 SRC / EPIC / FEAT 三段 formal object
- 不直接 freeze UI / TECH / TASK / TESTSET / TC / REPORT / BUG / EVI
- 所有 formal object 都保留对上游 evidence 与 ADR 约束的追溯
# Acceptance Checks

## AC-REV-01

- Scenario: formal object 边界校验
- Given: core.reverse-epic-feat 基于同一 repo evidence 运行
- When: 执行 reverse pack 物化
- Then: 仅生成 SRC / EPIC / FEAT 正式对象，不生成 UI / TECH / TASK / TESTSET formal freeze
- Trace Hints: TASK, TECH

## AC-REV-02

- Scenario: 主链追溯校验
- Given: reverse pack 已生成
- When: 检查 source_refs 与 derived_from 关系
- Then: SRC、EPIC、FEAT 都能追溯到同一条 reverse evidence 与 ADR 约束
- Trace Hints: TASK, TECH
# Dependencies

- None
# Non Goals

- 不替代现有正向 product / qa 正式治理流程
- 不新增平行 workflow key
