---
id: TASK-FEAT-084-003
ssot_type: task
title: Workflow CLI命令与输出格式化实现
status: frozen
version: v1
parent_id: FEAT-084
derived_from_ids: []
source_refs:
- FEAT-084#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_084_003
  identity_kind: ssot
frozen_at: '2026-03-12T19:44:04.751270'
---

# Objective

实现lee workflow命令组，包括template list、instance list和OutputFormatter

# Description

实现CLI命令层：
1. lee workflow template list: 显示模板列表(table/json/yaml格式)，列包含NAME/VERSION/DESCRIPTION/UPDATED
2. lee workflow instance list: 显示实例列表，列包含ID/TEMPLATE/STATUS/STARTED/DURATION/AGE，支持status_filter和watch_mode
3. OutputFormatter: 支持table/json/yaml输出格式；状态颜色编码(success=绿色/running=蓝色/pending=黄色/error=红色)
4. 退出码规范: 0=成功, 1=一般错误, 2=配置错误, 3=权限错误, 4=未找到, 10=未知错误
5. 8种关键状态处理: template_list_normal/empty, instance_list_normal/empty/filtered, comparison_view, error_config, error_permission

## Acceptance Mapping
- FEAT-084 / AC-005-002: lee workflow template list命令 - 返回模板列表，包含name/version/description
- FEAT-084 / AC-005-003: lee workflow instance list命令 - 返回实例列表，包含id/template/status/started/duration

## Dependencies
- TASK-FEAT-084-001
- TASK-FEAT-084-002

## Definition Of Done
- lee workflow template list命令实现并通过测试
- lee workflow instance list命令实现并通过测试
- OutputFormatter支持3种输出格式
- 状态颜色编码符合UI规范
- 退出码规范实现完整
- 8种关键状态UI行为验证通过
- 代码审查通过并合入主干
