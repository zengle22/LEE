---
id: TASK-FEAT-084-002
ssot_type: task
title: CLI 命令与输出格式化实现
status: active
version: v1
parent_id: FEAT-084
derived_from_ids: []
source_refs:
- FEAT-084#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_084_002
  identity_kind: ssot
---

# Objective

实现 lee workflow 命令组、OutputFormatter、FilterEngine 和 WatchModeController

# Description

实现 CLI 层和格式化层：
- lee workflow template list 命令支持 --format (table/json/yaml) 和 --filter 通配符过滤，列包含 NAME/VERSION/DESCRIPTION/UPDATED
- lee workflow instance list 命令支持 --status 过滤、--template 过滤、--watch 实时监控模式，列包含 ID/TEMPLATE/STATUS/STARTED/DURATION/AGE
- OutputFormatter 实现 L1_Sparse(JSON)、L2_Standard(表格)、L3_Verbose 三层输出格式
- 状态颜色编码（🟢success 🔵running 🟡pending 🔴failed ⚪cancelled）
- 退出码规范（0成功 2参数错误 3未找到 4权限错误 10配置错误）
- FilterEngine 实现通配符和状态组合过滤
- WatchModeController 实现定时刷新和优雅退出

## Acceptance Mapping
- FEAT-084 / AC-005-002: lee workflow template list 命令可查看可用模板，支持 table/json/yaml 格式和过滤
- FEAT-084 / AC-005-003: lee workflow instance list 命令可查看运行实例，支持状态过滤和 watch 模式

## Dependencies
- TASK-FEAT-084-001

## Definition Of Done
- lee workflow template list 命令实现并通过集成测试，支持 3 种输出格式
- lee workflow instance list 命令实现并通过集成测试，支持状态过滤和 --watch 模式
- OutputFormatter 支持 table/json/yaml 格式，状态颜色编码符合 UI 规范
- FilterEngine 实现通配符匹配和状态组合过滤
- WatchModeController 实现定时刷新和终端兼容性处理
- 8 种关键状态 UI 行为验证通过（template_list_normal/empty, instance_list_normal/empty/filtered, comparison_view, error_config, error_permission）
- 退出码规范实现完整（0/2/3/4/10）
- 代码审查通过并合入主干
- TASK 文件已冻结
