---
id: TASK-FEAT-084-004
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

实现Template与Instance存储分离，包括YAML模板存储、SQLite实例存储、版本解析器

# Description

构建数据层基础设施：TemplateStore基于YAML文件系统管理模板元数据，InstanceStore基于SQLite管理运行时实例状态，VersionResolver实现语义化版本解析与冻结机制，PathPolicy统一路径策略管理

## Acceptance Mapping
- FEAT-084 / AC-005-001: Template使用YAML文件系统，Instance使用SQLite+artifacts目录，存储分离完成
- FEAT-084 / AC-005-004: VersionResolver实现版本冻结，支持exact/caret/tilde/wildcard/latest模式

## Definition Of Done
- TemplateStore实现：YAML文件发现、加载、元数据解析
- InstanceStore实现：SQLite CRUD、查询、索引优化
- VersionResolver实现：semver解析、版本冻结逻辑
- PathPolicy实现：路径策略管理、目录协调
- 单元测试覆盖率≥90%
- TASK文件已冻结
