---
id: FEAT-SRC-009-011
ssot_type: feat
title: 共享输入规范落地
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
  contract_key: FEAT-SRC-009-011
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
    - Feature Delivery L2 定义文档
    - Bugfix Delivery L2 定义文档
    - Dev workflow 清单
    required_fields:
    - formal_ssot_id
    - source_refs
    - governing_adrs
    - workflow_catalog
    consumption_rules:
    - 共享规范必须在 L2 定义冻结后进行
    - workflow_catalog 必须覆盖所有 Dev workflow
    - 规范必须可验证
---

# Goal

统一所有 Dev workflow 的输入规范，确保跨工作流的一致性和可集成性
# User Value

所有 Dev workflow 统一遵守输入规范，确保跨工作流的一致性和可集成性，降低上下文切换成本
# Inputs

- {'formal_ssot_id': 'L2 工作流定义文档 ID'}
- {'source_refs': '规范来源引用'}
- {'governing_adrs': '规范决策 ADR'}
- {'workflow_catalog': 'Dev workflow 清单'}
# Input Contract

required_artifacts:
- Feature Delivery L2 定义文档
- Bugfix Delivery L2 定义文档
- Dev workflow 清单
required_fields:
- formal_ssot_id
- source_refs
- governing_adrs
- workflow_catalog
consumption_rules:
- 共享规范必须在 L2 定义冻结后进行
- workflow_catalog 必须覆盖所有 Dev workflow
- 规范必须可验证
# Processing

- 定义 formal_ssot_id 规范（格式、校验规则）
- 定义 source_refs 规范（引用格式、必填性）
- 定义 governing_adrs 规范（ADR 引用格式、影响范围声明）
- 定义 repo_context 规范（代码库路径、分支规则）
- 创建输入验证 checklist
# Outputs

- 共享输入规范文档
- formal_ssot_id 规范定义
- source_refs 规范定义
- governing_adrs 规范定义
- repo_context 规范定义
- 输入验证 checklist
# Acceptance

- 共享输入规范文档已冻结
- formal_ssot_id 规范包含格式和校验规则
- source_refs 规范包含引用格式和必填性
- governing_adrs 规范包含 ADR 引用格式和影响范围声明
- repo_context 规范包含代码库路径和分支规则
- 输入验证 checklist 可用
- 不实现验证工具
# Acceptance Checks

- id: AC-011-001
  scenario: 共享输入规范文档冻结
  given: 共享输入规范设计完成
  when: 提交评审并通过
  then: 文档标记为 frozen 状态
  trace_hints:
  - TASK
  - TECH
- id: AC-011-002
  scenario: formal_ssot_id 规范完整性
  given: 共享输入规范文档已冻结
  when: 检查 formal_ssot_id 规范
  then: 包含格式定义和校验规则
  trace_hints:
  - TECH
  - TESTSET
- id: AC-011-003
  scenario: source_refs 规范完整性
  given: 共享输入规范设计完成
  when: 检查 source_refs 规范
  then: 包含引用格式和必填性定义
  trace_hints:
  - TECH
- id: AC-011-004
  scenario: 输入验证 checklist 可用性
  given: 共享输入规范设计完成
  when: 使用 checklist 验证示例输入
  then: checklist 覆盖所有必需字段且可执行
  trace_hints:
  - TECH
  - TESTSET
# Dependencies

- EPIC-SRC-009
- FEAT-SRC-009-001
- FEAT-SRC-009-002
# Non Goals

- 实现输入验证工具
- 修改 workflow 引擎
- 强制历史任务合规
