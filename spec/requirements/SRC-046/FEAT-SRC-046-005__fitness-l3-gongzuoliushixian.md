---
id: FEAT-SRC-046-005
ssot_type: feat
title: Fitness L3 工作流实现与多嵌入点集成
status: draft
version: v1
workflow_instance_id: wf_task_296dfcdf
parent_id: EPIC-SRC-046-001
derived_from_ids:
- id: EPIC-SRC-046-001
  version: v1
  required: true
- id: ADR-024
  version: v2
  required: true
source_refs:
- EPIC-SRC-046-001#scope
- ADR-024
owner: null
tags: [governance, fitness, l3-workflow, completion]
properties:
  src_root_id: SRC-046
  priority: P0
  delivery_slice: mvp
---

# Fitness L3 工作流实现与多嵌入点集成

## Goal

实现 Fitness L3 工作流模板 (`template.governance.fitness`)，并嵌入 Product/Dev/QA L2 工作流的关键决策点前，提供统一的完成条件验证能力。

## User Value

- **防止完成误判**：agent 无法仅凭"局部测试通过"就宣布可完成
- **统一验证入口**：所有完成条件验证通过 Fitness L3 统一执行
- **可追溯证据**：fitness_result 结构化输出，可被 gate/supervisor 直接消费
- **灵活嵌入**：单一 L3 模板支持多嵌入点，按需加载适用规则

## Inputs

- ADR-024 frozen 规格
- Fitness Rule Schema 定义
- Product L2 / Dev L2 / QA L2 工作流模板
- 现有 Gate 消费接口

## Input Contract

required_artifacts:
  - ADR-024 frozen spec
  - Fitness Rule Schema draft
  - Product L2 workflow template
  - Dev L2 workflow template
  - QA L2 workflow template
required_fields:
  - formal_ssot_id
  - source_refs
  - governing_adrs
  - l3_workflow_template
  - fitness_rule_schema
  - embedding_points
consumption_rules:
  - ADR-024 必须为 frozen 状态
  - Fitness Rule Schema 必须包含 5 个 P0 Dimension
  - L3 模板必须支持 Product/Dev/QA 3 个嵌入点

## Processing

- 实现 Fitness L3 工作流模板 (`spec-global/departments/governance/workflows/templates/fitness-l3-template.yaml`)
- 实现 Fitness Runner 执行器 (`src/lee/governance/fitness_runner.py`)
- 创建最小 Fitness Rule 库 (`spec/fitness/rules/`)
- 嵌入 Dev L2 (Smoke Test 前) - **P0 切片**
- 嵌入 Product L2 (FEAT 冻结后) - **P1**
- 嵌入 QA L2 (Test Report 前) - **P1**
- 实现 fitness_result 输出结构化
- 集成 Gate 消费接口

## Outputs

- Fitness L3 工作流模板 YAML
- Fitness Runner 执行器代码
- Fitness Rule Schema 文件 (5 个 P0 Dimension)
- Dev L2 嵌入点集成代码
- Product L2 嵌入点集成代码 - **P1**
- QA L2 嵌入点集成代码 - **P1**
- fitness_result 输出对象定义

## Acceptance Criteria

- Fitness L3 模板可独立运行
- Dev L2 Smoke 前置验证已启用且可阻断
- fitness_result 输出结构符合 ADR-024 定义
- hard_gate 失败可正确阻塞下游步骤
- ADR-024 状态提升为 frozen

## Acceptance Checks

- id: AC-001
  scenario: Fitness L3 模板创建验证
  given: ADR-024 frozen 规格和 Fitness Rule Schema
  when: 执行 Fitness L3 工作流
  then: 产出 fitness_result 对象且结构完整
  trace_hints: [TASK, TESTSET, TECH]

- id: AC-002
  scenario: Dev L2 嵌入点验证
  given: Dev L2 工作流运行中
  when: integration 完成后进入 smoke_test 前
  then: Fitness L3 被正确调用且结果可阻断 smoke_test
  trace_hints: [TASK, TESTSET, TECH]

- id: AC-003
  scenario: hard_gate 阻断验证
  given: Fitness Rule 包含 hard_gate 规则
  when: 执行 Fitness L3 且规则失败
  then: fitness_result=fail 且下游步骤被阻断
  trace_hints: [TASK, TESTSET]

- id: AC-004
  scenario: fitness_result 消费验证
  given: fitness_result 已产出
  when: Gate/Supervisor 审查
  then: 可直接消费 fitness_result 无需手工拼接
  trace_hints: [TASK, TESTSET]

## Dependencies

- EPIC-SRC-046-001
- ADR-024 (must be frozen)

## Non Goals

- 替代现有 Gate/Approval/Supervisor 体系
- 一次性实现全部 Dimensions 和 Rules
- 独立 RELEASE L1 工作流实现 (未来 Phase C)
