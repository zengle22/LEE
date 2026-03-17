---
id: FEAT-SRC-058-001
ssot_type: feat
title: Smoke Gate Merge 门禁集成
status: frozen
version: v1
workflow_instance_id: wf_task_fdb19191
parent_id: EPIC-SRC-058-001
derived_from_ids:
- id: EPIC-SRC-058-001
  version: v1
  required: true
source_refs:
- EPIC-SRC-058-001#scope
owner: null
tags: []
properties:
  contract_key: feat_001
  identity_kind: ssot
frozen_at: '2026-03-17T10:13:48.257344'
---

# Goal

将 Smoke Gate 作为 blocker 门禁集成到 merge 流程，实现 100% merge 请求覆盖，自动拦截 blocker 问题

# User Value

Dev 在 merge 前自动执行 Smoke 测试，快速拦截 blocker 问题，避免有缺陷代码进入主干

# Inputs

- smoke_test_result
- merge_request_context
- gate_config

# Processing

- 在 merge 流程中集成 Smoke Gate 作为前置条件
- 实现 100% merge 请求覆盖
- 自动拦截 blocker 问题
- 可视化门禁状态

# Outputs

- merge_gate_status
- blocker_issue_report
- gate_visualization

# Acceptance

- Smoke Gate 作为 blocker 门禁集成到 merge 流程
- 实现 100% merge 请求覆盖
- 自动拦截 blocker 问题
- 门禁状态可视化

# Acceptance Checks

## AC-001
Smoke Gate 作为 merge 前置条件，未通过时阻止 merge 操作

## AC-002
所有 merge 请求 100% 经过 Smoke Gate 检查

## AC-003
Blocker 问题自动拦截并生成报告

## AC-004
门禁状态在 merge 界面可视化展示

# Non Goals

- QA Test Run 不直接阻塞 merge
- 非 blocker 的测试执行

# Dependencies

[]
