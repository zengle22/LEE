---
id: FEAT-SRC-046-001
ssot_type: feat
title: 交付主链建立与 RELEASE 起点治理
status: frozen
version: v1
workflow_instance_id: wf_task_296dfcdf
parent_id: EPIC-SRC-046-001
derived_from_ids:
- id: EPIC-SRC-046-001
  version: v1
  required: true
source_refs:
- EPIC-SRC-046-001#scope
owner: null
tags: []
properties:
  src_root_id: SRC-046
  priority: P0
  delivery_slice: mvp
---

# 交付主链建立与 RELEASE 起点治理

## Goal
建立以 RELEASE 为起点的正式交付主链，确保交付对象绑定关系可追溯可验证

## User Value
确保所有正式发布版本通过统一交付主链运行，交付对象绑定关系可追溯可验证

## Inputs
- EPIC-SRC-046-001 冻结规格
- 现有 RELEASE 对象定义
- 现有 DEVPLAN/TESTPLAN/TASK 对象定义
- 交付对象绑定关系规则

## Input Contract
required_artifacts:
  - EPIC-SRC-046-001 frozen spec
  - draft RELEASE schema
  - draft DEVPLAN schema
  - draft TESTPLAN schema
  - draft TASK schema
required_fields:
  - formal_ssot_id
  - source_refs
  - governing_adrs
  - repo_context
  - release_id
  - devplan_id
  - testplan_id
  - task_ids
consumption_rules:
  - 直接复用 EPIC 冻结规格作为需求基线
  - schema 对象以 draft 版本引用，本 FEAT 不负责冻结
  - 绑定关系字段必须存在于交付主链各对象中

## Processing
- 定义交付主链起点为 RELEASE 对象的规则
- 建立 RELEASE 到 DEVPLAN 的派生关系
- 建立 DEVPLAN 到 TESTPLAN 的绑定关系
- 建立 TESTPLAN 到 TASK 的执行关系
- 定义交付对象绑定一致性验证规则
- 定义 scope 完整性检查规则

## Outputs
- 交付主链建立规则文档 (delivery-chain-baseline.md)
- RELEASE 起点治理校验清单 (release-start-checklist.md)
- 交付对象绑定关系验证规则 (binding-validation-rules.md)
- scope 完整性检查清单 (scope-completeness-checklist.md)

## Acceptance Criteria
- 100% 正式发布版本通过交付主链完成交付
- 交付链上各对象 (RELEASE/DEVPLAN/TESTPLAN/TASK) 的绑定关系可查询可验证
- 交付主链起点明确为 RELEASE 对象
- scope 完整性检查可通过清单执行

## Acceptance Checks
- id: AC-001
  scenario: 交付主链建立规则验证
  given: 存在 EPIC 冻结规格和现有对象定义
  when: 执行交付主链建立流程
  then: 产出交付主链建立规则文档和校验清单
  trace_hints: [TASK, TESTSET, TECH]

- id: AC-002
  scenario: 交付对象绑定关系可追溯
  given: 交付主链已建立
  when: 查询任意 RELEASE 的交付链
  then: 可追溯其关联的 DEVPLAN/TESTPLAN/TASK 对象
  trace_hints: [TASK, TESTSET, TECH]

- id: AC-003
  scenario: scope 完整性检查执行
  given: 交付主链规则已定义
  when: 对 RELEASE 执行 scope 完整性检查
  then: 检查清单可识别缺失的交付对象绑定
  trace_hints: [TASK, TESTSET]

## Dependencies
- EPIC-SRC-046-001

## Non Goals
- 技术架构重构
- 重新发明三轴模型
- 对象 schema 冻结
