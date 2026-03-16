---
id: FEAT-SRC-041-002
ssot_type: feat
title: human_gate_context 人工决策前置上下文强制化
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
  contract_key: feat_002
  identity_kind: ssot
  src_root_id: SRC-041
frozen_at: '2026-03-15T05:28:24.280301'
---

# Goal

把 human_gate_context 固定为所有 human_required 决策与自动升级到人工决策场景的强制前置物，确保人工审批前已有完整、可消费的上下文对象。
# User Value

人类审批者在进入任何人工决策前都能获得统一、可消费的审批上下文，避免在缺少决策对象、证据和后续动作线索时被迫做判断。
# Inputs

- 已冻结的 gate 双轴语义：purpose 与 decision_mode
- decision_mode=human_required 的 gate 定义集合
- 自动检查升级为人工决策的触发条件与升级原因
- 审批者最小判断信息：subject、why_now、evidence、risk、next_action
# Processing

- 定义 human_gate_context 的最小信息边界，覆盖 subject、why_now、evidence、risk 与 next_action。
- 区分原生人工决策与自动升级到人工决策两类入口，并统一前置物要求。
- 建立 gate 可审批前的校验规则，阻断缺少 human_gate_context 的人工决策流转。
- 把 human_gate_context 作为 CLI、runtime 与审计的共享消费对象，而不是局部展示字段集合。
# Outputs

- 正式 FEAT 规格：human_gate_context 强制化规则与最小上下文边界
- 人工决策前置校验规则
- 升级到人工决策场景的上下文补齐约束
# Acceptance

- 所有 decision_mode=human_required 的 gate 在进入可审批状态前必须具备 human_gate_context。
- 所有由自动检查升级到人工决策的场景必须补齐 human_gate_context，且能表达升级原因与当前审批理由。
- human_gate_context 必须至少支撑 subject、why_now、evidence、risk 与 next_action 五类判断信息。
# Acceptance Checks

## AC-FEAT-SRC-041-016-002-01

- Scenario: 人工 gate 在审批前具备统一上下文
- Given: 一个 gate 已被定义为 decision_mode=human_required
- When: 该 gate 进入待审批状态
- Then: 审批者可直接消费包含 subject、why_now、evidence、risk 与 next_action 的 human_gate_context
- Trace Hints: TASK, TESTSET, TECH

## AC-FEAT-SRC-041-016-002-02

- Scenario: 自动检查升级到人工决策时补齐上下文
- Given: 一个自动检查因风险或异常被升级到人工决策
- When: 系统生成待审批 gate
- Then: 对应 human_gate_context 包含 escalation_reason，并可连接到 subject_refs 与 evidence_refs
- Trace Hints: TASK, TESTSET, TECH
# Dependencies

- FEAT-SRC-041-016-001
# Non Goals

- 正式放行语义约束
- CLI 命令交互样式
- 历史数据一次性迁移
