---
id: TASK-FEAT-084-002
ssot_type: task
title: TemplateRegistry与InstanceManager运行时实现
status: frozen
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
frozen_at: '2026-03-12T19:44:04.742644'
---

# Objective

实现模板发现加载、实例生命周期管理和版本解析冻结机制

# Description

实现运行时管理层组件：
1. TemplateRegistry: 模板发现、加载、版本解析；支持从templates/目录和内置模板加载
2. InstanceManager: 运行时实例生命周期管理；创建、查询、状态更新；集成concurrency_scope
3. VersionResolver: 模板版本解析与冻结；实例创建时锁定模板版本引用；支持语义化版本比较
4. 与orchestrator/execution集成: 复用现有workflow_instances表结构，添加template_version字段

## Acceptance Mapping
- FEAT-084 / AC-005-004: 模板升级不影响实例 - VersionResolver实现版本冻结，InstanceManager深拷贝模板快照

## Dependencies
- TASK-FEAT-084-001

## Definition Of Done
- TemplateRegistry类实现并通过单元测试
- InstanceManager类实现并通过单元测试
- VersionResolver类实现并通过单元测试
- 与lee run命令集成验证通过
- 并发控制与ADR-009规范一致
- 代码审查通过并合入主干
