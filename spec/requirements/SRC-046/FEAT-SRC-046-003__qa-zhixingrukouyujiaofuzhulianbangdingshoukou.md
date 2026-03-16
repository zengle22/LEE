---
id: FEAT-SRC-046-003
ssot_type: feat
title: QA 执行入口与交付主链绑定收口
status: draft
version: v1
workflow_instance_id: manual-ssot-create
parent_id: EPIC-SRC-046-001
derived_from_ids:
- id: EPIC-SRC-046-001
  version: v1
source_refs:
- EPIC-SRC-046-001#scope
owner: null
tags: []
properties:
  src_root_id: SRC-046
  priority: P1
  delivery_slice: qa-entry-binding
---

# QA 执行入口与交付主链绑定收口

## Goal
明确 QA 与研发执行入口对正式交付主链的绑定关系，完成入口治理收口

## User Value
QA 执行入口与正式交付主链建立明确绑定关系，消除对分散命令和兼容入口拼接的依赖

## Inputs
- 已冻结的 RELEASE 对象
- 已生成的 TESTPLAN 对象
- QA 执行入口现状说明

## Input Contract
required_artifacts:
  - RELEASE (scope_frozen)
  - TESTPLAN (draft|committed)
required_fields:
  - TESTPLAN.parent_id
  - TESTPLAN.derived_from_ids
consumption_rules:
  - TESTPLAN 的 parent_id 必须指向 RELEASE
  - TESTPLAN 的 derived_from_ids 必须包含 FEAT 和 TESTSET

## Processing
- 校验 QA 入口与交付主链的绑定关系
- 清理独立于交付主链之外的 QA 执行路径
- 建立 QA 活动追溯机制

## Outputs
- TESTPLAN 对象 (committed 状态)
- QA 入口绑定关系说明

## Acceptance Criteria
- QA 入口收口完成
- 执行入口与交付主链绑定关系清晰可查
- 无独立于交付主链之外的 QA 执行路径

## Acceptance Checks
- id: AC-001
  scenario: 校验 TESTPLAN 绑定关系
  given: 存在 TESTPLAN 对象
  when: 执行 plan-check 校验
  then: TESTPLAN.parent_id 必须指向有效的 RELEASE 对象
  trace_hints: [TASK, TESTSET]

- id: AC-002
  scenario: 校验 TESTPLAN 覆盖范围
  given: RELEASE 包含多个 FEAT@version
  when: 执行 plan-check --commit
  then: 每个 FEAT 都被 TESTPLAN 的 derived_from_ids 或 slices 覆盖
  trace_hints: [TASK, TESTSET]

## Dependencies
- FEAT-SRC-046-001

## Non Goals
- 不涉及技术架构重构
- 不包含研发排期管理
- 不涉及入口实现重构
