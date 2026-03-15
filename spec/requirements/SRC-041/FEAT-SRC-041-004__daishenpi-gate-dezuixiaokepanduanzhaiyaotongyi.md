---
id: FEAT-SRC-041-004
ssot_type: feat
title: 待审批 gate 的最小可判断摘要统一
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
  contract_key: feat_004
  identity_kind: ssot
  src_root_id: SRC-041
frozen_at: '2026-03-15T05:28:24.304552'
---

# Goal

统一待审批 gate 在 list、show、decide 链路中的最小可判断摘要，确保审批者在同一语义模型下快速判断当前 gate 的职责、参与方式、决策对象与触发原因。
# User Value

人工审批者在 list、show、decide 链路中无需额外追问即可快速识别当前 gate 的职责、参与方式、决策对象与触发原因，提升待办处理效率。
# Inputs

- 已冻结的 gate 双轴语义定义
- 已强制化的 human_gate_context 最小字段集合
- CLI 待审批链路：list、show、decide
- 审批者最小判断摘要字段：purpose、decision_mode、subject、why_now
# Processing

- 定义待审批 gate 的最小可判断摘要模型，覆盖 purpose、decision_mode、subject 与 why_now。
- 约束 list、show、decide 三个链路复用同一判断语义与字段来源。
- 把摘要字段绑定到 human_gate_context 与 gate 双轴语义，避免 CLI 侧重新发明字段解释。
- 建立审批者无需额外追问即可做首轮判断的验收边界。
# Outputs

- 正式 FEAT 规格：待审批 gate 最小可判断摘要模型
- CLI list/show/decide 共享的判断字段边界
- 摘要字段与 human_gate_context 的映射规则
# Acceptance

- 待审批 gate 在 list 阶段至少可见 purpose、decision_mode、subject 与 why_now 摘要。
- show 与 decide 链路必须延续同一套判断字段语义，不得重新命名同类治理信息。
- 审批者在最小摘要层即可识别 gate 职责、参与方式、决策对象与触发原因。
# Acceptance Checks

## AC-FEAT-SRC-041-016-004-01

- Scenario: list 阶段展示最小可判断摘要
- Given: 存在一个待审批 gate
- When: 审批者查看待办列表
- Then: 列表项中可直接读取 purpose、decision_mode、subject 与 why_now 摘要
- Trace Hints: UI, TASK, TESTSET, TECH

## AC-FEAT-SRC-041-016-004-02

- Scenario: show 与 decide 延续同一语义
- Given: 审批者从 list 进入 show 或 decide
- When: 系统展示该 gate 的详情或接收决策
- Then: 同一 gate 的职责、参与方式、对象与原因字段保持同名同义，不出现平行语义
- Trace Hints: UI, TASK, TESTSET, TECH
# Dependencies

- FEAT-SRC-041-016-001
- FEAT-SRC-041-016-002
# Non Goals

- 终端 UI 美化
- 审批结果模型统一
- 底层命令实现方案
