---
id: TASK-FEAT-085-002
ssot_type: task
title: 流式输出 CLI 格式化组件
status: frozen
version: v1
parent_id: FEAT-085
derived_from_ids: []
source_refs:
- FEAT-085#delivery
owner: null
tags: []
properties:
  contract_key: task_streaming_cli_formatter
  identity_kind: ssot
frozen_at: '2026-03-11T16:23:57.943950'
---

# Objective

实现 Rich 库集成的终端美化组件，优化用户可见输出格式。

# Description

使用 Rich 库实现跨平台终端美化，支持进度条、颜色和表格展示，并与 StreamExecutor 解耦。

## Acceptance Mapping

- FEAT-085 / AC-00401-001: 流式输出延迟验证，输出延迟 <= 500ms
- FEAT-085 / AC-00401-002: 输出完整性验证，所有输出内容完整

## Prerequisites

- TASK-FEAT-085-001

## Inputs

- 流式输出原始数据
- 展示配置参数

## Outputs

- 美化后的终端输出
- Rich 格式化组件

## Dependencies

- TASK-FEAT-085-001

## Definition Of Done

- CLIFormatter 组件实现完成
- Rich 库集成测试通过
- 与 StreamExecutor 集成测试通过

## Observability

- Log Scope: cli-formatting
- Audit Fields: run_id, changed_files

## Evidence Requirements

- Required Refs: TECH-FEAT-085
- Review Required: false

## Rollback Strategy

- Mode: revert
- Restore Targets: .workflow/workspace/wf_task_*/src/lee/executor/rendering
