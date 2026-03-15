---
id: FEAT-SRC-009-008
ssot_type: feat
title: L3 Integration 阶段定义
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
  contract_key: FEAT-SRC-009-008
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
    - Backend Development 阶段输出
    - Frontend Development 阶段输出
    - 集成测试环境配置
    required_fields:
    - formal_ssot_id
    - source_refs
    - governing_adrs
    - backend_outputs
    - frontend_outputs
    consumption_rules:
    - Integration 必须在 Backend 和 Frontend 阶段完成后进行
    - 后端和前端的契约必须一致
    - 集成测试环境必须可用
---

# Goal

定义 Integration 阶段的标准化流程，确保前后端、内外部依赖正确集成
# User Value

Dev 团队获得标准化的集成验证阶段指导，确保前后端、内外部依赖正确集成，产出集成测试证据
# Inputs

- {'formal_ssot_id': '上游阶段 ID'}
- {'source_refs': '需求来源引用'}
- {'governing_adrs': '技术决策 ADR'}
- {'backend_outputs': 'Backend Development 输出'}
- {'frontend_outputs': 'Frontend Development 输出'}
# Input Contract

required_artifacts:
- Backend Development 阶段输出
- Frontend Development 阶段输出
- 集成测试环境配置
required_fields:
- formal_ssot_id
- source_refs
- governing_adrs
- backend_outputs
- frontend_outputs
consumption_rules:
- Integration 必须在 Backend 和 Frontend 阶段完成后进行
- 后端和前端的契约必须一致
- 集成测试环境必须可用
# Processing

- 定义阶段输入规范（Backend/Frontend 阶段输出）
- 定义阶段内任务清单（环境准备、集成测试执行、问题修复）
- 定义输出物规范（集成测试报告、问题修复记录）
- 定义完成标准（集成测试通过率阈值）
- 定义与 Evidence Pack 阶段的交接规则
# Outputs

- L3 Integration 阶段定义文档
- 输入规范文档
- 阶段任务清单
- 输出物规范
- 完成标准定义（含通过率阈值）
- 阶段交接规则文档
# Acceptance

- L3 Integration 阶段文档已冻结
- 输入规范明确定义 Backend/Frontend 阶段输出为输入
- 阶段任务清单覆盖环境准备、集成测试执行、问题修复
- 输出物规范定义集成测试报告和问题修复记录格式
- 完成标准包含集成测试通过率阈值
- 与 Evidence Pack 阶段的交接规则文档化
- 不包含具体集成测试框架
# Acceptance Checks

- id: AC-008-001
  scenario: Integration 阶段文档冻结
  given: L3 Integration 阶段设计完成
  when: 提交评审并通过
  then: 文档标记为 frozen 状态
  trace_hints:
  - TASK
  - TECH
- id: AC-008-002
  scenario: 阶段任务清单完整性
  given: Integration 阶段文档已冻结
  when: 检查任务清单
  then: 覆盖环境准备、集成测试执行、问题修复三类任务
  trace_hints:
  - TECH
  - TESTSET
- id: AC-008-003
  scenario: 完成标准可量化
  given: Integration 阶段设计完成
  when: 检查完成标准
  then: 包含具体的集成测试通过率阈值（如 100% 关键路径）
  trace_hints:
  - TECH
- id: AC-008-004
  scenario: 交接规则完整性
  given: Integration 阶段设计完成
  when: 检查交接规则章节
  then: 明确定义与 Evidence Pack 阶段的交接条件
  trace_hints:
  - TECH
  - TESTSET
# Dependencies

- EPIC-SRC-009
- FEAT-SRC-009-001
- FEAT-SRC-009-006
- FEAT-SRC-009-007
# Non Goals

- 实现集成测试框架
- 定义具体测试工具
- 实现自动化部署
