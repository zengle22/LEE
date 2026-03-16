---
id: FEAT-SRC-046-004
ssot_type: feat
title: 缺陷回流路径与 bugfix 交付轴闭环
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
  priority: P1
  delivery_slice: mvp
---

# 缺陷回流路径与 bugfix 交付轴闭环

## Goal
建立缺陷回流路径并确保 100% 的 bugfix 可归属到对应交付版本并重新进入交付轴闭环

## User Value
100% 的 bugfix 可明确归属到对应交付版本并重新进入交付轴治理闭环

## Inputs
- EPIC-SRC-046-001 冻结规格
- 交付主链建立规则文档
- 现有缺陷管理流程定义
- 现有 bugfix 流程定义

## Input Contract
required_artifacts:
  - EPIC-SRC-046-001 frozen spec
  - baseline delivery-chain-baseline.md
  - draft bugfix-evidence-ownership-spec
  - draft bugfix-route-to-delivery-axis-spec
required_fields:
  - formal_ssot_id
  - source_refs
  - governing_adrs
  - repo_context
  - bugfix_evidence_ref
  - bugfix_execution_commitment_ref
  - delivery_version_ref
consumption_rules:
  - 直接复用 EPIC 冻结规格作为需求基线
  - 交付主链规则以 baseline 版本引用
  - 缺陷回流路径以 draft 规格输出供下游消费

## Processing
- 定义缺陷回流路径
- 区分 bugfix 证据归属与执行承诺位置
- 建立 bugfix 到交付版本的归属规则
- 制定 bugfix 重新纳入交付轴闭环的规则

## Outputs
- 缺陷回流路径规格 (bugfix-route-spec.md)
- bugfix 证据归属与执行承诺区分指南 (bugfix-evidence-commitment-guide.md)
- bugfix 交付版本归属规则 (bugfix-version-ownership-rules.md)
- bugfix 交付轴闭环规则 (bugfix-delivery-axis-close-rules.md)

## Acceptance Criteria
- 100% bugfix 可明确归属到对应交付版本
- bugfix 可重新进入交付轴闭环
- 缺陷回流路径清晰可执行
- 证据归属与执行承诺位置区分明确

## Acceptance Checks
- id: AC-001
  scenario: 缺陷回流路径定义验证
  given: 存在交付主链规则和现有缺陷管理流程
  when: 执行缺陷回流路径定义流程
  then: 产出缺陷回流路径规格
  trace_hints: [TASK, TESTSET, TECH]

- id: AC-002
  scenario: bugfix 交付版本归属
  given: 缺陷回流路径已定义
  when: 对 bugfix 执行交付版本归属检查
  then: 100% bugfix 可明确归属到对应交付版本
  trace_hints: [TASK, TESTSET]

- id: AC-003
  scenario: bugfix 重新纳入交付轴闭环
  given: bugfix 已归属到交付版本
  when: 执行 bugfix 交付轴闭环流程
  then: bugfix 重新进入交付轴治理闭环
  trace_hints: [TASK, TESTSET, TECH]

- id: AC-004
  scenario: 证据归属与执行承诺区分
  given: bugfix 流程已定义
  when: 检查 bugfix 证据归属与执行承诺位置
  then: 两者区分明确且可追溯
  trace_hints: [TASK, TESTSET]

## Dependencies
- EPIC-SRC-046-001
- FEAT-SRC-046-001

## Non Goals
- bugfix 流程重构
- 缺陷管理系统改造
- bugfix 代码实现修改
