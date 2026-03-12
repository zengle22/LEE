---
id: FEAT-092
ssot_type: feat
title: 测试追溯链路贯通
status: frozen
version: v1
parent_id: EPIC-QA-SSOT-UPGRADE
derived_from_ids: []
source_refs:
- EPIC-QA-SSOT-UPGRADE#scope
owner: null
tags: []
properties:
  contract_key: feat_002
  identity_kind: ssot
frozen_at: '2026-03-12T00:13:22.010850'
---

# Goal

实现 BUG/REPORT/EVI 到 RELEASE/TESTPLAN/TASK/TESTSET/FEAT 的完整追溯能力
# User Value

Release Gate 评审者能够基于完整追溯链路进行 go/no-go 决策，问题可定位到具体 FEAT
# Inputs

- BUG/REPORT/EVI 定义
- FEAT-QA-SSOT-001 完成的 release 化结构
# Processing

- REPORT 模型增加追溯字段（release_id, testplan_id, task_id, testset_id, feat_id）
- BUG 模型增加追溯字段（release_id, testplan_id, task_id, testset_id, feat_id）
- EVI 模型增加追溯字段（release_id, testplan_id, task_id, testset_id, feat_id）
- 实现从 REPORT/BUG/EVI 反查完整链路的查询能力
- 验证追溯链路完整性约束
# Outputs

- 具备完整追溯字段的 REPORT/BUG/EVI 模型
- 反查链路 API/查询接口
- 追溯链路验证报告
# Acceptance

- BUG、REPORT、EVI 必须反查到 RELEASE、TESTPLAN、TASK、TESTSET、FEAT
- 给定一个 BUG，能追溯到它所属的 RELEASE/TESTPLAN/TASK/TESTSET/FEAT
# Acceptance Checks

## AC-002-001

- Scenario: REPORT 追溯字段完整性
- Given: 系统已实现 REPORT 模型扩展
- When: 创建 REPORT 时
- Then: release_id, testplan_id, task_id, testset_id, feat_id 全部非空
- Trace Hints: TECH, TESTSET

## AC-002-002

- Scenario: BUG 追溯字段完整性
- Given: 系统已实现 BUG 模型扩展
- When: 创建 BUG 时
- Then: release_id, testplan_id, task_id, testset_id, feat_id 全部非空
- Trace Hints: TECH, TESTSET

## AC-002-003

- Scenario: EVI 追溯字段完整性
- Given: 系统已实现 EVI 模型扩展
- When: 创建 EVI 时
- Then: release_id, testplan_id, task_id, testset_id, feat_id 全部非空
- Trace Hints: TECH, TESTSET

## AC-002-004

- Scenario: 从 BUG 反查完整链路
- Given: 存在一个已创建的 BUG
- When: 查询该 BUG 的完整追溯链路
- Then: 返回 RELEASE/TESTPLAN/TASK/TESTSET/FEAT 完整路径
- Trace Hints: UI, TECH, TESTSET

## AC-002-005

- Scenario: 从 REPORT 反查完整链路
- Given: 存在一个已创建的 REPORT
- When: 查询该 REPORT 的完整追溯链路
- Then: 返回 RELEASE/TESTPLAN/TASK/TESTSET/FEAT 完整路径
- Trace Hints: UI, TECH, TESTSET
# Dependencies

- EPIC-QA-SSOT-UPGRADE
- FEAT-QA-SSOT-001
# Non Goals

- TESTSET/TESTPLAN 的基础 release 化改造（由 FEAT-001 负责）
- QA 执行入口的收敛（由 FEAT-003 负责）
- 三轴模型的分层存储（由 FEAT-001 负责）
- 具体查询接口的技术实现细节
