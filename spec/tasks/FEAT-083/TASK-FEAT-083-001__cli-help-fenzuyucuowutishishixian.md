---
id: TASK-FEAT-083-001
ssot_type: task
title: CLI Help 分组与错误提示实现
status: frozen
version: v1
parent_id: FEAT-083
derived_from_ids: []
source_refs:
- FEAT-083#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_083_001
  identity_kind: ssot
frozen_at: '2026-03-12T19:26:45.189400'
---

# Objective

实现 CLI Help 的 Workflow/Internal 分组展示，统一错误提示文案以引导用户使用 workflow-first 治理入口

# Description

实现自定义 WorkflowFirstGroup 类支持命令分组显示，更新 main.py 以使用新的 Group 类，扩展 error_hints.py 添加 workflow-first 引导提示，并添加单元测试

## Acceptance Mapping
- FEAT-083 / AC-004-001: CLI help 明确区分 Workflow Commands 和 Internal/Maintenance Commands 分组
- FEAT-083 / AC-004-004: 错误提示文案引导用户使用正确的治理入口

## Definition Of Done
- WorkflowFirstGroup 类实现并通过单元测试
- lee --help 输出显示两个明确分组的命令列表
- error_hints.py 扩展 workflow-first 引导提示
- 相关单元测试覆盖率 >=80%
- 代码审查通过
- TASK 文件已冻结
