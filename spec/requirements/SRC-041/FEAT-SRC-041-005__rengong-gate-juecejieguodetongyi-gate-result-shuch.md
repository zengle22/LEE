---
id: FEAT-SRC-041-005
ssot_type: feat
title: 人工 gate 决策结果的统一 gate_result 输出
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
  contract_key: feat_005
  identity_kind: ssot
  src_root_id: SRC-041
frozen_at: '2026-03-15T05:28:24.316598'
---

# Goal

统一所有人工 gate 的决策结果输出为 gate_result，并固定 subject_refs、evidence_refs 与 next_action 的最小治理信息边界，支撑 runtime、CLI 与审计稳定消费。
# User Value

runtime、CLI 维护者和审计链路可以消费统一的人工决策结果对象，稳定追踪审批对象、证据引用与后续动作，减少结果解释分叉。
# Inputs

- 已冻结的 gate 双轴语义定义
- 已强制化的 human_gate_context
- 人工 gate 决策结论样本：批准、拒绝、要求补充信息、风险接受
- 下游消费需求：subject_refs、evidence_refs、next_action
# Processing

- 定义 gate_result 作为人工决策的统一输出对象。
- 固定 subject_refs、evidence_refs 与 next_action 为所有人工决策结果的最小必备信息。
- 对批准、拒绝、补充信息、风险接受等结果分支采用统一结构而非分叉载体。
- 把 gate_result 设计为 runtime、CLI 与审计可直接消费的稳定结果边界。
# Outputs

- 正式 FEAT 规格：人工 gate 的统一 gate_result 输出规则
- 包含 subject_refs、evidence_refs、next_action 的最小结果边界
- 人工决策结果与上下文、审批对象的可追溯关联规则
# Acceptance

- 所有人工 gate 的决策结果都必须统一输出为 gate_result。
- gate_result 必须稳定包含 subject_refs、evidence_refs 与 next_action。
- 不同人工决策结论不得引入互不兼容的结果对象结构。
# Acceptance Checks

## AC-FEAT-SRC-041-016-005-01

- Scenario: 人工 gate 输出统一结果对象
- Given: 一个人工 gate 已产生审批结论
- When: 系统输出该结论供 runtime、CLI 或审计消费
- Then: 输出对象为统一 gate_result，而不是特定 gate 私有结构
- Trace Hints: TASK, TESTSET, TECH

## AC-FEAT-SRC-041-016-005-02

- Scenario: 统一结果对象包含最小治理字段
- Given: 存在一个已生成的 gate_result
- When: 下游系统消费该结果
- Then: 可直接读取 subject_refs、evidence_refs 与 next_action，并追溯到对应审批对象和证据
- Trace Hints: TASK, TESTSET, TECH
# Dependencies

- FEAT-SRC-041-016-001
- FEAT-SRC-041-016-002
# Non Goals

- 审计报表设计
- 数据库落表细节
- 历史结果回填策略
