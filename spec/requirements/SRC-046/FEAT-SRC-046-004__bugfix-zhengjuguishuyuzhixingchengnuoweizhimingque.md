---
id: FEAT-SRC-046-004
ssot_type: feat
title: Bugfix 证据归属与执行承诺位置明确化
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
  delivery_slice: bugfix-governance
---

# Bugfix 证据归属与执行承诺位置明确化

## Goal
区分 bugfix 的证据归属与执行承诺位置，将 bugfix 重新纳入交付轴治理闭环

## User Value
100% 的 bugfix 可明确归属到对应交付版本并重新进入交付轴治理闭环

## Inputs
- BUG 对象 (found_in_release 指向 RELEASE)
- REPORT 对象 (测试报告)
- TASK 对象 (修复任务)

## Input Contract
required_artifacts:
  - BUG (active)
  - REPORT (test_execution)
  - TASK (doing|done)
required_fields:
  - BUG.found_in_release
  - BUG.severity
  - BUG.source_report_id
  - TASK.implements
consumption_rules:
  - BUG 必须通过 found_in_release 关联到 RELEASE
  - BUG 必须通过 source_report_id 追溯到测试报告
  - TASK 修复完成后必须更新 BUG 状态

## Processing
- 明确 bugfix 的证据归属位置 (REPORT/EVI)
- 明确 bugfix 的执行承诺位置 (TASK)
- 将 bugfix 重新纳入交付轴闭环

## Outputs
- BUG 对象 (closed|waived 状态)
- BUGFIX_REPORT (修复报告)
- 证据关联关系

## Acceptance Criteria
- bugfix 的证据归属与执行承诺位置明确区分
- 所有 bugfix 可明确归属到对应交付版本
- bugfix 重新进入交付轴闭环

## Acceptance Checks
- id: AC-001
  scenario: 创建 BUG 对象
  given: 测试执行发现缺陷
  when: 创建 BUG 对象并设置 found_in_release 和 source_report_id
  then: BUG 可追溯到 RELEASE 和测试报告
  trace_hints: [TASK, TESTSET]

- id: AC-002
  scenario: Bugfix 任务执行
  given: BUG 状态为 open/triaged
  when: 创建 TASK 执行修复并设置 TASK.implements 指向 BUG
  then: TASK 完成后 BUG 状态可更新为 in_fix/in_verify
  trace_hints: [TASK, TECH]

- id: AC-003
  scenario: Bugfix 闭环校验
  given: BUG 修复完成
  when: 执行 release-check
  then: BUG.bug_state 必须为 closed 或 waived，否则阻断发布
  trace_hints: [TASK, TESTSET]

## Dependencies
- FEAT-SRC-046-002

## Non Goals
- 不涉及技术架构重构
- 不涉及缺陷管理系统改造
- 不改变 bugfix 本质属性
