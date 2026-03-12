---
id: FEAT-116
ssot_type: feat
title: Legacy Path Deprecation Governance
status: frozen
version: v1
parent_id: EPIC-SRC-009
derived_from_ids: []
source_refs:
- EPIC-SRC-009#scope
owner: null
tags: []
properties:
  contract_key: feat_009
  identity_kind: ssot
frozen_at: '2026-03-12T17:47:40.533563'
---

# Goal

治理旧工作流路径有序退出，确保新主入口成为唯一活跃通道
# User Value

旧工作流路径有序退出，新主入口成为唯一活跃通道，消除入口混乱和治理盲区
# Inputs

- 旧路径清单（phase-openspec-flow 等）
- 新主入口定义（Feature/Bugfix Delivery L2）
- 文档清单（README, WORKFLOWS）
# Processing

- 识别所有旧路径
- 在代码中标记 deprecated
- 在文档中标记 deprecated
- 在配置中标记 deprecated
- 更新 README 指向新主入口
# Outputs

- 标记 deprecated 的旧路径代码
- 更新的 README 文档
- 更新的 WORKFLOWS 文档
- 旧路径任务迁移指南
- 旧路径活跃度报告
# Acceptance

- 旧路径标记完成
- phase-openspec-flow 等旧路径标记 deprecated（代码/文档/配置三重标记）
- README 更新指向新主入口
- WORKFLOWS 文档更新
- 旧路径任务迁移指南完成
# Acceptance Checks

## AC-SRC-009-009-01

- Scenario: 旧路径三重标记完成
- Given: 旧路径识别完成
- When: 执行标记 deprecated 操作
- Then: 代码、文档、配置均已标记 deprecated
- Trace Hints: TASK, TECH

## AC-SRC-009-009-02

- Scenario: README 更新验证
- Given: README 文档更新完成
- When: 检查 README 内容
- Then: README 指向新主入口 Feature/Bugfix Delivery L2
- Trace Hints: TASK, UI

## AC-SRC-009-009-03

- Scenario: WORKFLOWS 文档更新验证
- Given: WORKFLOWS 文档更新完成
- When: 检查 WORKFLOWS 内容
- Then: 文档指向新主入口
- Trace Hints: TASK

## AC-SRC-009-009-04

- Scenario: 旧路径活跃度为零
- Given: 治理实施完成
- When: 统计一段时间内的任务创建
- Then: 旧路径活跃度 = 0
- Trace Hints: TASK, TESTSET

## AC-SRC-009-009-05

- Scenario: 新入口唯一性验证
- Given: 新任务创建工作流
- When: 创建新工作流任务
- Then: 只能通过 Feature/Bugfix Delivery L2 入口发起
- Trace Hints: TASK, TESTSET
# Dependencies

- EPIC-SRC-009
- FEAT-SRC-009-001
- FEAT-SRC-009-002
# Non Goals

- 不强制迁移历史任务
- 不删除旧路径代码
- 不修改已完成的任务
