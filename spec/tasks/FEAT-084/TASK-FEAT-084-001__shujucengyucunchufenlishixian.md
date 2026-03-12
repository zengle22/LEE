---
id: TASK-FEAT-084-001
ssot_type: task
title: 数据层与存储分离实现
status: active
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
---

# Objective

建立 Template 与 Instance 的物理存储分离机制，实现 TemplateStore、InstanceStore 和 VersionResolver 核心组件

# Description

实现数据层基础设施：
- TemplateStore 基于 YAML 文件系统管理模板元数据（支持 name/version/description/author/updated_at 字段）
- InstanceStore 基于 SQLite 管理运行时实例状态（支持 id/template_id/template_version/status/created_at/started_at/completed_at/concurrency_scope/data 字段）
- VersionResolver 实现语义化版本解析与冻结机制（支持 exact/caret/tilde/wildcard/latest 模式）
- PathPolicy 统一路径策略管理（templates/ 目录、.workflow/templates/、$HOME/.lee/templates/ 优先级规则）

## Acceptance Mapping
- FEAT-084 / AC-005-001: Template 与 Instance 存储分离 - Template 使用 YAML 文件系统，Instance 使用 SQLite+artifacts 目录
- FEAT-084 / AC-005-004: 模板升级不影响实例 - Instance 表存储 template_version 字段支持版本隔离，VersionResolver 实现版本冻结

## Definition Of Done
- TemplateStore 类实现：YAML 文件发现、加载、元数据解析，通过单元测试
- InstanceStore 类实现：SQLite CRUD、查询、索引优化，通过单元测试
- VersionResolver 类实现：semver 解析、版本冻结逻辑，通过单元测试
- PathPolicy 实现：路径策略管理、多目录优先级协调
- workflow_instances 表结构定义文档化，与现有 orchestrator.db v3.0 兼容
- 代码审查通过并合入主干
- TASK 文件已冻结
