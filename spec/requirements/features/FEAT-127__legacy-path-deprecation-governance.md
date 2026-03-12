---
id: FEAT-127
ssot_type: feat
title: Legacy Path Deprecation Governance
status: active
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
---

# Goal

治理旧工作流路径的有序退出，确保新主入口成为唯一活跃通道，消除入口混乱和治理盲区
# User Value

旧工作流路径有序退出，新主入口成为唯一活跃通道，消除入口混乱和治理盲区
# Inputs

- Inputs defined by EPIC scope
# Processing

- 识别 phase-openspec-flow 等旧路径
- 在代码层标记 deprecated
- 在文档层标记 deprecated
- 在配置层标记 deprecated
- 更新 README 指向新主入口
# Outputs

- 代码层 deprecated 标记
- 文档层 deprecated 标记
- 配置层 deprecated 标记
- 更新的 README 文档
- 更新的 WORKFLOWS 文档
# Acceptance

- 旧路径标记完成
- phase-openspec-flow 等旧路径标记 deprecated（代码/文档/配置三重标记）
- README 更新指向新主入口
- WORKFLOWS 文档更新
- 旧路径任务迁移指南发布
# Acceptance Checks

## AC-SRC-009-009-01

- Scenario: 三重 deprecated 标记完成
- Given: EPIC-SRC-009-009 进入验收阶段
- When: 检查旧路径标记
- Then: 代码、文档、配置三层均标记 deprecated
- Trace Hints: TASK, TECH

## AC-SRC-009-009-02

- Scenario: 入口文档更新
- Given: 新主入口已定义
- When: 检查 README 和 WORKFLOWS 文档
- Then: 文档指向 Feature/Bugfix Delivery L2 新主入口
- Trace Hints: TASK, UI

## AC-SRC-009-009-03

- Scenario: 迁移指南发布
- Given: 旧路径已标记 deprecated
- When: 检查文档
- Then: 存在完整的旧路径任务迁移指南
- Trace Hints: TASK

## AC-SRC-009-009-04

- Scenario: 旧路径活跃度归零验证
- Given: 治理措施已实施
- When: 统计一段时间内的 workflow 创建
- Then: 无新任务通过旧路径创建
- Trace Hints: TASK, TESTSET
# Dependencies

- EPIC-SRC-009
- FEAT-SRC-009-001
- FEAT-SRC-009-002
# Non Goals

- 不强制迁移历史任务
- 不删除旧路径代码
- 不修改已完成的任务
