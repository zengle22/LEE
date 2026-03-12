---
id: TASK-FEAT-084-005
ssot_type: task
title: 应用层与CLI交互实现
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

实现TemplateRegistry、InstanceManager运行时管理，以及CLI命令与输出格式化

# Description

构建应用层：TemplateRegistry实现模板发现/加载/缓存，InstanceManager实现生命周期管理/状态机/concurrency_scope集成，WorkflowCLI实现template list和instance list命令，OutputFormatter支持table/json/yaml多格式输出与状态颜色编码

## Acceptance Mapping
- FEAT-084 / AC-005-002: lee workflow template list返回模板列表，包含name/version/description/updated/author
- FEAT-084 / AC-005-003: lee workflow instance list返回实例列表，包含id/template/status/started/duration/age，支持状态过滤和watch模式

## Dependencies
- {'task_id': 'TASK-FEAT-084-001', 'relationship': 'hard'}

## Definition Of Done
- TemplateRegistry实现：discover/load/reload接口，内存索引
- InstanceManager实现：生命周期管理、状态机、并发控制
- WorkflowCLI实现：template list命令，支持--format/--department
- WorkflowCLI实现：instance list命令，支持--format/--status/--watch/--template
- OutputFormatter实现：table/json/yaml格式，状态颜色编码，退出码规范
- E2E测试通过：创建实例→查询→版本冻结验证流程
- TASK文件已冻结
