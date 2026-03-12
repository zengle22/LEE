---
id: FEAT-172
ssot_type: feat
title: Workflow 实例支持携带执行器类型并在多执行器间隔离运行
status: frozen
version: v1
parent_id: EPIC-022
derived_from_ids: []
source_refs:
- EPIC-022#scope
owner: null
tags: []
properties:
  contract_key: feat_004
  identity_kind: ssot
frozen_at: '2026-03-12T22:26:15.259213'
---

# Goal

Workflow 实例能够携带执行器类型并隔离运行
# User Value

用户可在同一工作流中切换执行器
# Inputs

- workflow_instance_state
- executor_binding
# Processing

- 携带执行器类型上下文
- 隔离多执行器实例
- 保持 workflow 状态连续性
- 验证执行器切换兼容性
# Outputs

- isolated_workflow_state
# Acceptance

- workflow 实例可携带执行器类型
- 执行器切换不破坏状态连续性
- 多执行器实例可隔离运行
# Acceptance Checks

## AC-001

- Scenario: 携带执行器上下文
- Given: Workflow 实例初始化
- When: 绑定执行器类型
- Then: 实例携带执行器上下文
- Trace Hints: TECH, TESTSET

## AC-002

- Scenario: 多执行器隔离
- Given: 多个执行器实例存在
- When: 并行执行任务
- Then: 实例间状态互不干扰
- Trace Hints: TECH, TASK
# Dependencies

- EPIC-022
- FEAT-022-003
# Non Goals

- 不替换现有执行器
- 不新增平行 workflow
