---
id: FEAT-SRC-046-005
ssot_type: feat
title: workflow 命令整合 - 现有 RELEASE/DEVPLAN/TESTPLAN/TASK 对象与命令能力整合
status: frozen
version: v1
workflow_instance_id: wf_task_65036fdd
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
  contract_key: feat_005
  identity_kind: ssot
  src_root_id: SRC-046
frozen_at: '2026-03-19T02:47:17.101568'
---

# Goal

基于现有 RELEASE、DEVPLAN、TESTPLAN、TASK 对象基础进行 workflow 化治理，整合现有 release-cut、plan-derive、plan-check、release-check、release-close 等命令能力
# User Value

基于现有 RELEASE、DEVPLAN、TESTPLAN、TASK 对象基础进行 workflow 化治理，利用现有 release-cut、plan-derive、plan-check、release-check、release-close 等命令能力进行整合
# User Stories

- 作为**发布工程师**，我希望 RELEASE 对象完成 workflow 化治理，以便确保版本管理遵循统一规范
- 作为**计划经理**，我希望 DEVPLAN/TESTPLAN 对象完成 workflow 化治理，以便确保计划制定和测试计划的一致性
- 作为**开发负责人**，我希望 TASK 对象完成 workflow 化治理，以便确保任务执行可追溯到交付主链
- 作为**技术负责人**，我希望整合现有命令能力到交付主链 workflow，以便消除命令碎片化、提高执行效率
# Inputs

- RELEASE 对象定义（baseline）
- DEVPLAN 对象定义（baseline）
- TESTPLAN 对象定义（baseline）
- TASK 对象定义（baseline）
- release-cut 命令能力说明
# Processing

- 对 RELEASE 对象进行 workflow 化治理
- 对 DEVPLAN 对象进行 workflow 化治理
- 对 TESTPLAN 对象进行 workflow 化治理
- 对 TASK 对象进行 workflow 化治理
- 整合 release-cut 命令到交付主链 workflow
# Outputs

- RELEASE 对象 workflow 化规范
- DEVPLAN 对象 workflow 化规范
- TESTPLAN 对象 workflow 化规范
- TASK 对象 workflow 化规范
- release-cut 命令整合方案
# Acceptance

- RELEASE/DEVPLAN/TESTPLAN/TASK 对象均完成 workflow 化治理
- release-cut 命令整合到交付主链 workflow，可追溯 RELEASE 起点
- plan-derive 命令整合到交付主链 workflow，支持计划追溯
- plan-check 命令整合到交付主链 workflow，支持计划校验
- release-check 命令整合到交付主链 workflow，支持版本检查
- 当 workflow 执行失败时，提供回滚机制恢复到执行前的状态
# Acceptance Checks

## AC-001

- Scenario: RELEASE 对象 workflow 化验证
- Given: 存在 RELEASE 对象实例
- When: 检查 RELEASE 对象是否遵循 workflow 化规范
- Then: 返回遵循状态或违规项列表
- Trace Hints: TECH, TASK, TESTSET

## AC-002

- Scenario: plan-derive 命令整合验证
- Given: 存在计划派生需求
- When: 执行 plan-derive 命令
- Then: 命令通过交付主链 workflow 执行并返回可追溯结果
- Trace Hints: TECH, TASK, TESTSET

## AC-003

- Scenario: release-check 命令整合验证
- Given: 存在 RELEASE 版本
- When: 执行 release-check 命令
- Then: 命令通过交付主链 workflow 执行并返回版本检查报告
- Trace Hints: TECH, TASK, TESTSET

## AC-004

- Scenario: release-close 命令整合验证
- Given: 存在待关闭的 RELEASE 版本
- When: 执行 release-close 命令
- Then: 命令通过交付主链 workflow 执行并完成发布关闭
- Trace Hints: TECH, TASK, TESTSET

## AC-005

- Scenario: 命令能力与交付主链映射查询
- Given: 存在多个命令与交付主链的映射数据
- When: 查询命令与交付主链的映射关系
- Then: 返回清晰的映射关系表
- Trace Hints: TECH, TASK, TESTSET
# Dependencies

- FEAT-SRC-046-001
# Non Goals

- 新命令开发
- 现有命令功能重构
