---
id: TASK-FEAT-081-001
ssot_type: task
title: SSOT Workflow-First CLI 命令骨架实现
status: frozen
version: v1
parent_id: FEAT-081
derived_from_ids: []
source_refs:
- FEAT-081#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_081_001
  identity_kind: ssot
frozen_at: '2026-03-12T14:56:38.487902'
---

# Objective

实现 lee adr/epic/feat new 三条 CLI 命令骨架，完成命令注册、参数解析和帮助体系

# Description

基于 Click 框架创建 ssot_create.py 模块，实现 lee adr new、lee epic new、lee feat new 三条命令的基础结构。包含参数定义（title 为必需，其他为可选）、--dry-run 支持、帮助文案（强制包含'治理流程'字样），并注册到 lee.cli.main 的 Workflow Commands 分组。

## Acceptance Mapping
- FEAT-081 / AC-002-001: workflow-first 命令出现在主帮助 - 命令注册到 CLI，帮助分组为 'Workflow Commands'
- FEAT-081 / AC-002-003: 帮助文案说明治理流程 - click help 参数包含治理流程说明

## Definition Of Done
- src/lee/cli/commands/ssot_create.py 模块创建完成
- 三条命令（lee adr new、lee epic new、lee feat new）注册到 CLI
- --dry-run 参数支持实现
- 帮助文案通过 lee --help 和 lee adr new --help 验证包含'治理流程'字样
- 单元测试覆盖参数解析逻辑
- TASK 文件已冻结
