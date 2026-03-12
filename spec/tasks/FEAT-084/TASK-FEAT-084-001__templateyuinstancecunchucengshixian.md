---
id: TASK-FEAT-084-001
ssot_type: task
title: Template与Instance存储层实现
status: frozen
version: v1
parent_id: FEAT-084
derived_from_ids: []
source_refs:
- FEAT-084#delivery
owner: null
tags: []
properties:
  contract_key: task_feat_084_001
  identity_kind: ssot
frozen_at: '2026-03-12T19:44:04.733700'
---

# Objective

建立Template与Instance的物理存储分离机制，实现TemplateStore和InstanceStore核心组件

# Description

实现模板与实例的存储分离架构：
1. TemplateStore: 管理templates/目录的YAML文件读写，支持模板元数据解析(name, version, description)
2. InstanceStore: 实现SQLite workflow_instances表操作，支持实例CRUD和查询
3. 数据表结构设计: 包含id, template_name, template_version, status, concurrency_scope等字段
4. 存储路径策略: 遵循PathPolicy规范，协调templates/目录与.artifacts/{run_id}/的关系

## Acceptance Mapping
- FEAT-084 / AC-005-001: Template与Instance存储分离 - Template使用YAML文件系统，Instance使用SQLite+artifacts目录
- FEAT-084 / AC-005-004: 模板升级不影响实例 - Instance表存储template_version字段支持版本隔离

## Definition Of Done
- TemplateStore类实现并通过单元测试
- InstanceStore类实现并通过单元测试
- workflow_instances表结构定义文档化
- 存储层与现有orchestrator.db兼容
- 代码审查通过并合入主干
