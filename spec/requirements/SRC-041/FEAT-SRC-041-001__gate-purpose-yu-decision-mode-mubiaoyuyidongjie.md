---
id: FEAT-SRC-041-001
ssot_type: feat
title: Gate purpose 与 decision_mode 目标语义冻结
status: frozen
version: v1
workflow_instance_id: feat-specs-epic-src-041-016-v1
parent_id: EPIC-SRC-041-016
derived_from_ids:
- id: EPIC-SRC-041-016
  version: v1
  required: true
source_refs:
- EPIC-SRC-041-016#scope
owner: null
tags: []
properties:
  contract_key: feat_001
  identity_kind: ssot
  src_root_id: SRC-041
frozen_at: '2026-03-15T05:28:24.267600'
---

# Goal

将 gate 的职责语义与参与方式冻结为 purpose 与 decision_mode 双轴模型，并把历史分类明确降级为收敛映射入口，避免后续规格、workflow 与 runtime 继续扩散混合语义。
# User Value

治理负责人和 workflow 设计者可用统一双轴语义定义任一 gate，避免 Auto/Review/Approval 与 auto_check/human_review/human_approval/human_gate 混用导致的职责歧义。
# Inputs

- 冻结 EPIC 的目标、范围、非目标与成功标准
- 现行 gate 分类样本：Auto Gate、Review Gate、Approval Gate、auto_check、human_review、human_approval、human_gate
- 治理约束来源：PGC-ADR-017-V1 对 gate 语义归一化的正式约束
# Processing

- 定义 purpose 作为职责语义轴，覆盖 approval、review、check 等可审计职责边界。
- 定义 decision_mode 作为参与方式轴，区分 auto、human_required 等决策参与模式。
- 建立旧分类到双轴模型的收敛映射规则，并声明其用途仅限兼容入口与迁移识别。
- 输出禁止继续扩散旧分类语义的规则，作为下游 workflow、runtime、CLI 与审计消费前置约束。
# Outputs

- 正式 FEAT 规格：gate 双轴目标语义、允许组合与旧分类收敛约束
- 历史分类到 purpose / decision_mode 的兼容映射清单
- 下游规格消费必须引用的统一术语边界
# Acceptance

- 新增或收敛后的 gate 定义必须显式声明 purpose 与 decision_mode，且这两个字段足以表达职责与参与方式。
- Auto Gate、Review Gate、Approval Gate、auto_check、human_review、human_approval、human_gate 必须被定义为输入兼容映射，而不是正式输出语义。
- 下游 FEAT 不得重新引入第三条分类轴来表达 gate 职责或参与方式。
# Acceptance Checks

## AC-FEAT-SRC-041-016-001-01

- Scenario: 新增 gate 定义按双轴模型冻结
- Given: 存在一个新增或待收敛的 gate 定义
- When: 规格作者为该 gate 编写正式定义
- Then: 定义中可直接读取 purpose 与 decision_mode，且无需依赖旧分类字段解释职责
- Trace Hints: TASK, TESTSET, TECH

## AC-FEAT-SRC-041-016-001-02

- Scenario: 历史分类被限制为兼容映射入口
- Given: 存在来自旧模型的 gate 分类值
- When: 系统或规格消费这些旧值
- Then: 消费结果只能映射到 purpose 与 decision_mode，不能把旧值继续发布为正式治理语义
- Trace Hints: TASK, TESTSET, TECH
# Dependencies

- None
# Non Goals

- 数据库列名或存储方案
- 运行时执行逻辑改造
- CLI 展示细节
