---
id: FEAT-SRC-009-005
ssot_type: feat
title: L3 Contract Design 阶段定义
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
  contract_key: FEAT-SRC-009-005
  identity_kind: ssot
  materialized_from_workflow: wf_task_de4f2645
  priority: P1
  delivery_slice: stage-l3
  lifecycle_status: draft
  derived_object_expectations:
    qa_seed_required: true
    testset_required: true
    task_required: true
  input_contract:
    required_artifacts:
    - TECH 对象冻结文档
    - 技术决策 ADR
    required_fields:
    - formal_ssot_id
    - source_refs
    - governing_adrs
    - tech_design_spec
    consumption_rules:
    - Contract Design 必须在 TECH 冻结后进行
    - tech_design_spec 必须包含完整的技术边界
    - ADR 必须明确接口技术选型
---

# Goal

定义 Contract Design 阶段的标准化流程，确保技术契约在实现前被充分定义和评审
# User Value

Dev 团队获得标准化的契约设计阶段指导，确保技术契约在实现前被充分定义和评审，减少后期返工
# Inputs

- {'formal_ssot_id': '上游 TECH 对象 ID'}
- {'source_refs': '需求来源引用'}
- {'governing_adrs': '技术决策 ADR'}
- {'tech_design_spec': 'TECH 设计规格'}
# Input Contract

required_artifacts:
- TECH 对象冻结文档
- 技术决策 ADR
required_fields:
- formal_ssot_id
- source_refs
- governing_adrs
- tech_design_spec
consumption_rules:
- Contract Design 必须在 TECH 冻结后进行
- tech_design_spec 必须包含完整的技术边界
- ADR 必须明确接口技术选型
# Processing

- 定义阶段输入规范（TECH 对象）
- 定义阶段内任务清单（API 契约、数据契约、事件契约设计）
- 定义输出物规范（契约文档、评审记录）
- 定义完成标准
- 定义与 Backend/Frontend 阶段的交接规则
# Outputs

- L3 Contract Design 阶段定义文档
- 输入规范文档
- 阶段任务清单
- 输出物规范
- 完成标准定义
- 阶段交接规则文档
# Acceptance

- L3 Contract Design 阶段文档已冻结
- 输入规范明确定义 TECH 对象为输入
- 阶段任务清单覆盖 API 契约、数据契约、事件契约设计
- 输出物规范定义契约文档和评审记录格式
- 完成标准明确定义
- 与 Backend/Frontend 阶段的交接规则文档化
- 不包含具体契约模板
# Acceptance Checks

- id: AC-005-001
  scenario: Contract Design 阶段文档冻结
  given: L3 Contract Design 阶段设计完成
  when: 提交评审并通过
  then: 文档标记为 frozen 状态
  trace_hints:
  - TASK
  - TECH
- id: AC-005-002
  scenario: 阶段任务清单完整性
  given: Contract Design 阶段文档已冻结
  when: 检查任务清单
  then: 覆盖 API 契约、数据契约、事件契约三类设计任务
  trace_hints:
  - TECH
  - TESTSET
- id: AC-005-003
  scenario: 交接规则定义
  given: Contract Design 阶段设计完成
  when: 检查交接规则章节
  then: 明确定义与 Backend 和 Frontend 阶段的交接条件
  trace_hints:
  - TECH
- id: AC-005-004
  scenario: 完成标准可验收性
  given: Contract Design 阶段设计完成
  when: 检查完成标准
  then: 标准可量化、可验证
  trace_hints:
  - TECH
  - TESTSET
# Dependencies

- EPIC-SRC-009
- FEAT-SRC-009-001
- FEAT-SRC-009-003
# Non Goals

- 实现契约生成工具
- 定义具体 API 规范
- 实现代码生成
