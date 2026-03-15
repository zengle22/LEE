---
id: FEAT-SRC-009-004
ssot_type: feat
title: Evidence Pack 收口机制
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
  contract_key: FEAT-SRC-009-004
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
    - Feature Delivery L2 输出
    - Bugfix Delivery L2 输出
    - 各阶段交付物
    required_fields:
    - formal_ssot_id
    - source_refs
    - governing_adrs
    - delivery_outputs
    - verification_results
    consumption_rules:
    - Evidence Pack 必须在工作流完成后生成
    - 所有必需证据必须齐全
    - 证据格式必须符合规范
---

# Goal

设计 Evidence Pack 作为证据轴正式收口对象，确保所有交付可审计、可追踪
# User Value

作为证据轴正式收口对象，确保所有交付可审计、可追踪，满足三轴 SSOT 体系的证据完整性要求
# Inputs

- {'formal_ssot_id': '工作流实例 ID'}
- {'source_refs': '来源引用'}
- {'governing_adrs': '相关 ADR 引用'}
- {'delivery_outputs': '阶段交付物列表'}
- {'verification_results': '验证结果'}
# Input Contract

required_artifacts:
- Feature Delivery L2 输出
- Bugfix Delivery L2 输出
- 各阶段交付物
required_fields:
- formal_ssot_id
- source_refs
- governing_adrs
- delivery_outputs
- verification_results
consumption_rules:
- Evidence Pack 必须在工作流完成后生成
- 所有必需证据必须齐全
- 证据格式必须符合规范
# Processing

- 设计 Evidence Pack Schema 定义
- 定义必需证据清单（代码、测试报告、评审记录、部署记录）
- 设计与 L2 工作流的集成接口
- 定义审计追溯规则
- 创建示例 Evidence Pack 模板
# Outputs

- Evidence Pack Schema 定义文档
- 必需证据清单文档
- L2 工作流集成接口规范
- 审计追溯规则文档
- 示例 Evidence Pack 模板
# Acceptance

- Evidence Pack Schema 文档已冻结
- Schema 包含完整的证据类型定义
- 必需证据清单覆盖代码、测试报告、评审记录、部署记录
- L2 工作流集成接口规范完整
- 审计追溯规则文档化
- 示例 Evidence Pack 模板提供
- 不干预 Evidence Pack 审计逻辑
# Acceptance Checks

- id: AC-004-001
  scenario: Evidence Pack Schema 冻结
  given: Evidence Pack 机制设计完成
  when: 提交评审并通过
  then: Schema 文档标记为 frozen 状态
  trace_hints:
  - TASK
  - TECH
- id: AC-004-002
  scenario: 必需证据清单完整性
  given: Evidence Pack 机制文档已冻结
  when: 检查证据清单
  then: 包含代码、测试报告、评审记录、部署记录四类证据
  trace_hints:
  - TECH
  - TESTSET
- id: AC-004-003
  scenario: L2 工作流集成接口
  given: Evidence Pack 机制设计完成
  when: 检查集成接口规范
  then: 明确定义与 Feature/Bugfix Delivery L2 的集成方式
  trace_hints:
  - TECH
- id: AC-004-004
  scenario: 审计追溯规则定义
  given: Evidence Pack 机制设计完成
  when: 检查审计追溯章节
  then: 定义从 Evidence Pack 到上游 FEAT/BUG 的追溯路径
  trace_hints:
  - TECH
  - TESTSET
# Dependencies

- EPIC-SRC-009
- FEAT-SRC-009-001
- FEAT-SRC-009-002
# Non Goals

- 实现审计逻辑
- 修改 Evidence Pack 审计规则
- 实现证据收集自动化
