---
id: FEAT-070
ssot_type: feat
title: Freeze SSOT 状态语义定义
status: frozen
version: v1
parent_id: EPIC-003
derived_from_ids: []
source_refs:
- EPIC-003#scope
owner: null
tags: []
properties:
  contract_key: feat_003
  identity_kind: ssot
frozen_at: '2026-03-11T14:48:59.061105'
---

# Goal

澄清 Freeze 为 SSOT 对象的状态变化（冻结态），而非独立文档实体
# User Value

明确 Freeze 状态迁移属于 Approval Gate 范畴，确保冻结操作的合规性
# Inputs

- SSOT 对象当前状态
- Freeze 操作请求
- Approval Gate 审批结果
# Processing

- 解析 Freeze 请求，验证当前 SSOT 状态
- 检查是否已通过 Approval Gate 审批
- 执行 Freeze 状态变更
- 记录 Freeze 操作的审计日志
# Outputs

- Freeze 状态变更结果
- 触发条件说明
- 有效期信息
- 状态迁移规则说明
# Acceptance

- Freeze 明确定义为 SSOT 状态变化，不是独立文档实体
- Freeze 状态迁移必须经过 Approval Gate 审批
- Freeze 有明确的触发条件、有效期和迁移规则
# Acceptance Checks

## AC-FREEZE-001

- Scenario: Freeze 状态定义
- Given: SSOT 对象
- When: 查看对象状态定义
- Then: Freeze 是状态属性值，不是独立实体
- Trace Hints: TECH, TASK

## AC-FREEZE-002

- Scenario: Freeze 必须经过 Approval Gate
- Given: 用户发起 Freeze 请求
- When: 请求进入审批流程
- Then: 系统要求 Approval Gate 审批通过后才执行 Freeze
- Trace Hints: TASK, TESTSET

## AC-FREEZE-003

- Scenario: Freeze 触发条件和有效期
- Given: Freeze 配置
- When: 定义 Freeze 规则时
- Then: 必须指定触发条件（如时间、操作类型）和有效期
- Trace Hints: UI, TASK

## AC-FREEZE-004

- Scenario: Freeze 状态迁移规则
- Given: 已 Freeze 的 SSOT
- When: 状态发生变更时
- Then: 系统记录完整的迁移历史和变更原因
- Trace Hints: TECH, TESTSET
# Dependencies

- FEAT-GATE-MODEL
# Non Goals

- 不涉及具体的 Freeze 状态存储实现
- 不处理跨系统的 Freeze 同步机制
- 不定义历史 Freeze 数据的迁移方案
