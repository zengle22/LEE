---
id: TASK-FEAT-088-002
ssot_type: task
title: 边界可视化 UI 前缀实现
status: frozen
version: v1
parent_id: FEAT-088
derived_from_ids: []
source_refs:
- FEAT-088#delivery
owner: null
tags: []
properties:
  contract_key: task_boundary_ui
  identity_kind: ssot
frozen_at: '2026-03-11T16:23:57.980427'
---

# Objective

实现 `[LOG]/[EVD]/[EVT]/[OUT]` 四类信息前缀区分。

# Description

在 CLI 展示层添加边界标识前缀，确保用户可以清晰区分日志、证据、事件和展示输出。

## Acceptance Mapping

- FEAT-088 / AC-00404-002: 展示层解耦验证，仅通过展示层接口获取数据

## Prerequisites

- TASK-FEAT-088-001

## Inputs

- 边界分类数据
- 展示数据请求

## Outputs

- 带前缀的终端输出
- 边界可视化组件

## Dependencies

- TASK-FEAT-088-001

## Definition Of Done

- 边界前缀格式化组件实现完成
- 四类前缀 `[LOG]/[EVD]/[EVT]/[OUT]` 可用
- 与 BoundarySeparator 集成测试通过

## Observability

- Log Scope: boundary-ui
- Audit Fields: run_id

## Evidence Requirements

- Required Refs: TECH-FEAT-088
- Review Required: false

## Rollback Strategy

- Mode: revert
- Restore Targets: .workflow/workspace/wf_task_*/src/lee/executor/rendering/boundary.py
