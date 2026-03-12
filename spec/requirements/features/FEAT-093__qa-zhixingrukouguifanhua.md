---
id: FEAT-093
ssot_type: feat
title: QA 执行入口规范化
status: frozen
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: feat_003
  identity_kind: ssot
frozen_at: '2026-03-12T00:13:22.020380'
---

# Goal

收敛 QA 执行入口到 TESTPLAN 下的 TASK，实现 RELEASE -> PLAN -> TASK 的唯一执行路径
# User Value

QA 部门有唯一的规范化执行入口，防止执行路径混乱，确保执行可追踪
# Inputs

- TASK 定义
- FEAT-QA-SSOT-001 完成的 TESTPLAN release 化结构
# Processing

- TASK 模型强制 parent_testplan_id 必填
- 阻塞非 TESTPLAN 路径的 QA 执行入口
- 实现执行前链路完整性校验机制
- 运行时拦截绕过 TESTPLAN 的直接执行尝试
# Outputs

- 规范化 TASK 模型
- 执行入口拦截机制
- 执行路径校验规则
# Acceptance

- QA 执行入口必须收敛到 TESTPLAN 下的 TASK（入口唯一性验证）
- 正式交付只能通过 RELEASE -> PLAN -> TASK 进入执行
# Acceptance Checks

## AC-003-001

- Scenario: TASK 必须属于 TESTPLAN
- Given: 系统已部署执行入口规范化
- When: 创建 TASK 时提供有效的 parent_testplan_id
- Then: TASK 创建成功且 parent_testplan_id 不可为空
- Trace Hints: TECH, TASK, TESTSET

## AC-003-002

- Scenario: 阻塞直接执行入口
- Given: 系统已部署执行入口规范化
- When: 尝试绕过 TESTPLAN 直接执行 TASK
- Then: 执行被拦截并返回路径错误
- Trace Hints: TECH, TASK, TESTSET

## AC-003-003

- Scenario: 执行前链路完整性校验
- Given: 准备执行一个 TASK
- When: 系统校验 TESTPLAN -> RELEASE 链路
- Then: 链路完整才允许执行，否则拒绝
- Trace Hints: TECH, TASK, TESTSET

## AC-003-004

- Scenario: FEAT-001 前置依赖完成
- Given: FEAT-QA-SSOT-001 已交付
- When: 验证 TESTPLAN 挂在 RELEASE 下的状态
- Then: 基础结构已就绪
- Trace Hints: TASK, TESTSET
# Dependencies

- EPIC-QA-SSOT-UPGRADE
- FEAT-QA-SSOT-001
# Non Goals

- TESTSET/TESTPLAN 的基础 release 化改造（由 FEAT-001 负责）
- 追溯链路的完整性验证（由 FEAT-002 负责）
- BUG/REPORT/EVI 的反查能力（由 FEAT-002 负责）
- 具体拦截机制的技术实现细节
