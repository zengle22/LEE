---
id: FEAT-SRC-009-002
ssot_type: feat
title: Bugfix Delivery L2 工作流定义
status: frozen
version: v1
parent_id: EPIC-SRC-009
derived_from_ids:
- id: EPIC-SRC-009
  version: v1
source_refs:
- EPIC-SRC-009#scope
owner: null
tags: []
properties:
  contract_key: FEAT-SRC-009-002
  identity_kind: ssot
  materialized_from_workflow: wf_task_de4f2645
  priority: P0
  delivery_slice: foundation
  lifecycle_status: draft
  derived_object_expectations:
    qa_seed_required: true
    testset_required: true
    task_required: true
  input_contract:
    required_artifacts:
    - BUG 报告（bug_ssot_id 标识）
    - 复现证据（日志、截图、步骤）
    required_fields:
    - bug_ssot_id
    - severity
    - reproduction_evidence
    consumption_rules:
    - BUG 报告必须包含完整的复现步骤
    - severity 必须符合 P0/P1/P2 分级标准
    - reproduction_evidence 必须可验证
---

# Goal

定义 Dev 部门从 BUG 到 Evidence Pack 的完整 Bugfix 交付主链，建立 Bug 修复的标准化流程
# User Value

Dev 部门获得从 BUG 到 Evidence Pack 的完整 Bugfix 交付主链，实现 Bug 修复流程的标准化和可追溯，团队可通过统一的 L2 入口执行 Bug 修复任务
# Inputs

- {'bug_ssot_id': 'BUG 的正式 SSOT ID'}
- {'severity': 'BUG 严重程度分级'}
- {'reproduction_evidence': '复现证据'}
# Input Contract

required_artifacts:
- BUG 报告（bug_ssot_id 标识）
- 复现证据（日志、截图、步骤）
required_fields:
- bug_ssot_id
- severity
- reproduction_evidence
consumption_rules:
- BUG 报告必须包含完整的复现步骤
- severity 必须符合 P0/P1/P2 分级标准
- reproduction_evidence 必须可验证
# Processing

- 校验输入完整性（bug_ssot_id, severity, reproduction_evidence）
- 定义 L3 阶段编排顺序（Triage → Fix → Verification → Evidence Pack）
- 定义 Bugfix 状态机
- 集成 Bugfix 粒度控制规则
- 设计与上游 BUG 源的契约接口
- 设计与下游 Evidence Pack 的契约接口
# Outputs

- Bugfix Delivery L2 工作流定义文档（冻结状态）
- Bugfix 输入规范文档
- Bugfix L3 阶段编排顺序定义
- Bugfix 状态机定义
- 粒度控制规则集成规范
- 契约接口定义文档
# Acceptance

- Bugfix Delivery L2 工作流定义文档已冻结并通过评审
- 输入规范包含 bug_ssot_id, severity, reproduction_evidence 字段定义
- L3 阶段编排顺序明确定义为 Triage → Fix → Verification → Evidence Pack
- 状态机定义完整
- Bugfix 粒度控制规则已集成
- 与上游 BUG 源的契约接口文档化
- 与下游 Evidence Pack 的契约接口文档化
- 不包含 L3 阶段具体实现逻辑
# Acceptance Checks

- id: AC-002-001
  scenario: Bugfix L2 工作流定义文档冻结
  given: Bugfix Delivery L2 框架设计完成
  when: 提交评审并通过
  then: 文档标记为 frozen 状态并存档
  trace_hints:
  - TASK
  - TECH
- id: AC-002-002
  scenario: Bugfix 输入规范完整性
  given: Bugfix L2 工作流定义文档已冻结
  when: 检查输入规范章节
  then: 包含 bug_ssot_id, severity, reproduction_evidence 完整定义
  trace_hints:
  - TECH
  - TESTSET
- id: AC-002-003
  scenario: Bugfix L3 阶段编排定义
  given: Bugfix L2 框架包含阶段编排定义
  when: 检查阶段编排章节
  then: 明确定义 Triage → Fix → Verification → Evidence Pack 顺序
  trace_hints:
  - TECH
- id: AC-002-004
  scenario: 粒度控制规则集成
  given: Bugfix L2 框架设计完成
  when: 检查粒度控制章节
  then: 已集成默认规则和五同原则 batch 例外机制
  trace_hints:
  - TECH
  - TESTSET
# Dependencies

- EPIC-SRC-009
# Non Goals

- 实现 L3 阶段的具体逻辑
- 修改 BUG 产生机制
- 实现具体修复代码
