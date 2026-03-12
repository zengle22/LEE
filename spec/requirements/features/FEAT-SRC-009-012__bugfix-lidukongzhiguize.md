---
id: FEAT-SRC-009-012
ssot_type: feat
title: Bugfix 粒度控制规则
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
  contract_key: FEAT-SRC-009-012
  identity_kind: ssot
  materialized_from_workflow: wf_task_de4f2645
  priority: P1
  delivery_slice: governance
  lifecycle_status: draft
  derived_object_expectations:
    qa_seed_required: true
    testset_required: true
    task_required: true
  input_contract:
    required_artifacts:
    - Bugfix Delivery L2 定义文档
    - BUG 分类标准
    - 历史 batch 修复案例分析
    required_fields:
    - formal_ssot_id
    - source_refs
    - governing_adrs
    - bug_classification
    consumption_rules:
    - 粒度控制规则必须在 Bugfix L2 定义冻结后进行
    - bug_classification 必须清晰可执行
    - batch 例外审批流程必须明确
---

# Goal

定义 Bugfix 的粒度控制标准，确保默认单 bug 单 workflow instance，同时为合理的 batch 场景提供审批机制
# User Value

明确 Bugfix 的粒度控制标准，确保默认单 bug 单 workflow instance，同时为合理的 batch 场景提供审批机制
# Inputs

- {'formal_ssot_id': 'Bugfix Delivery L2 定义文档 ID'}
- {'source_refs': '规则来源引用'}
- {'governing_adrs': '粒度决策 ADR'}
- {'bug_classification': 'BUG 分类标准'}
# Input Contract

required_artifacts:
- Bugfix Delivery L2 定义文档
- BUG 分类标准
- 历史 batch 修复案例分析
required_fields:
- formal_ssot_id
- source_refs
- governing_adrs
- bug_classification
consumption_rules:
- 粒度控制规则必须在 Bugfix L2 定义冻结后进行
- bug_classification 必须清晰可执行
- batch 例外审批流程必须明确
# Processing

- 定义默认规则（1 bug → 1 bugfix workflow instance）
- 定义五同原则（同模块、同根因、同修复方案、同测试范围、同风险等级）
- 设计 batch 例外审批流程
- 创建粒度合规检查 checklist
- 定义合规率统计方法
# Outputs

- Bugfix 粒度控制规则文档
- 默认规则定义
- 五同原则定义
- Batch 例外审批流程
- 粒度合规检查 checklist
- 合规率统计方法
# Acceptance

- Bugfix 粒度控制规则文档已冻结
- 默认规则明确为 1 bug → 1 bugfix workflow instance
- 五同原则完整定义（同模块、同根因、同修复方案、同测试范围、同风险等级）
- Batch 例外审批流程清晰可执行
- 粒度合规检查 checklist 可用
- 合规率统计方法定义
- 不实现自动化检查工具
# Acceptance Checks

- id: AC-012-001
  scenario: Bugfix 粒度控制规则文档冻结
  given: Bugfix 粒度控制规则设计完成
  when: 提交评审并通过
  then: 文档标记为 frozen 状态
  trace_hints:
  - TASK
  - TECH
- id: AC-012-002
  scenario: 默认规则明确性
  given: 粒度控制规则文档已冻结
  when: 检查默认规则章节
  then: 明确定义 1 bug → 1 bugfix workflow instance
  trace_hints:
  - TECH
  - TESTSET
- id: AC-012-003
  scenario: 五同原则完整性
  given: 粒度控制规则设计完成
  when: 检查五同原则定义
  then: 覆盖同模块、同根因、同修复方案、同测试范围、同风险等级
  trace_hints:
  - TECH
- id: AC-012-004
  scenario: Batch 审批流程可执行性
  given: 粒度控制规则设计完成
  when: 检查 batch 例外审批流程
  then: 流程步骤清晰、审批节点明确
  trace_hints:
  - TECH
  - TESTSET
# Dependencies

- EPIC-SRC-009
- FEAT-SRC-009-002
# Non Goals

- 实现自动化粒度检查
- 修改 BUG 报告机制
- 强制拆分历史 batch
