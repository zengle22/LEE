---
id: FEAT-082
ssot_type: feat
title: Formal Object 元数据自动继承机制
status: frozen
version: v1
parent_id: EPIC-003
derived_from_ids: []
source_refs:
- EPIC-003#scope
owner: null
tags: []
properties:
  contract_key: feat_003
  identity_kind: ssot
frozen_at: '2026-03-11T15:17:41.927838'
---

# Goal

使 formal object 的 source_refs、parent_id、derived_from_ids 在 workflow 执行过程中自动继承和绑定
# User Value

用户创建 ADR/EPIC/FEAT 时，系统自动维护来源追溯信息，无需手动维护
# Inputs

- Source Object (SRC) 定义
- Workflow 执行上下文
- 对象层级关系配置
# Processing

- 通过 workflow 创建对象时自动注入正确的 source_refs
- 自动维护 parent_id 层级关系（FEAT->EPIC->ADR）
- 自动维护 derived_from_ids 追溯链
- 在 workflow runtime 中实现元数据继承逻辑
# Outputs

- 元数据自动继承逻辑
- 来源追溯信息展示
# Acceptance

- 通过 workflow 创建 ADR/EPIC/FEAT 时系统自动注入正确的 source_refs
- 自动维护 parent_id 层级关系
- 自动维护 derived_from_ids 追溯链
- 对象详情查询时能展示完整的来源追溯信息
# Acceptance Checks

## AC-003-001

- Scenario: source_refs 自动绑定
- Given: 用户通过 workflow 创建 EPIC
- When: workflow 执行完成
- Then: EPIC 对象的 source_refs 自动包含关联的 SRC
- Trace Hints: TECH, TESTSET

## AC-003-002

- Scenario: parent_id 层级关系自动维护
- Given: 用户通过 workflow 创建 FEAT
- When: workflow 执行完成
- Then: FEAT 对象的 parent_id 自动设置为对应的 EPIC
- Trace Hints: TECH, TESTSET

## AC-003-003

- Scenario: 来源追溯信息展示
- Given: FEAT 对象已创建并绑定元数据
- When: 查询 FEAT 详情
- Then: 响应中包含完整的 source_refs、parent_id、derived_from_ids 信息
- Trace Hints: UI, TESTSET
# Dependencies

- FEAT-003-002
# Non Goals

- 不修改现有 SSOT 数据模型 schema
- 不处理跨 workspace 的 source refs 引用
